[CmdletBinding(DefaultParameterSetName = 'Run')]
param(
    [string]$EnvFile = '.env',
    [Parameter(ParameterSetName = 'Check', Mandatory = $true)]
    [switch]$Check,
    [Parameter(ParameterSetName = 'Validate', Mandatory = $true)]
    [switch]$ValidateOnly,
    [Parameter(ParameterSetName = 'Run')]
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

function Read-HustlyDevelopmentEnvironment([string[]]$Lines) {
    # A data file, never PowerShell code: KEY=literal single-line value.
    # Whole-line # comments are ignored; #/$/backticks/quotes inside a value
    # are literal. No interpolation, quote removal, escapes or inline comments.
    $htValues = @{}
    $htAllowedNames = @(
        'DJANGO_ENVIRONMENT', 'DJANGO_SECRET_KEY', 'DJANGO_DEBUG',
        'DJANGO_ALLOWED_HOSTS', 'DJANGO_CSRF_TRUSTED_ORIGINS', 'DRF_NUM_PROXIES',
        'DJANGO_SECURE_SSL_REDIRECT', 'DJANGO_SESSION_COOKIE_SECURE',
        'DJANGO_CSRF_COOKIE_SECURE', 'DJANGO_SECURE_HSTS_SECONDS',
        'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'DJANGO_SECURE_HSTS_PRELOAD',
        'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST',
        'POSTGRES_PORT', 'POSTGRES_BIND_ADDRESS', 'DJANGO_MAILER_BACKEND',
        'DJANGO_SMTP_HOST', 'DJANGO_SMTP_PORT', 'DJANGO_SMTP_USERNAME',
        'DJANGO_SMTP_PASSWORD', 'DJANGO_SMTP_USE_TLS', 'DJANGO_SMTP_USE_SSL',
        'DJANGO_SMTP_TIMEOUT', 'DJANGO_DEFAULT_FROM_EMAIL', 'DJANGO_SERVER_EMAIL'
    )
    $htLineNumber = 0
    foreach ($htLine in $Lines) {
        $htLineNumber++
        if ([string]::IsNullOrWhiteSpace($htLine) -or $htLine.TrimStart().StartsWith('#')) { continue }
        if ($htLine.Contains([char]0) -or $htLine -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            throw "Invalid environment syntax at line $htLineNumber. Use KEY=literal-value; values are never evaluated."
        }
        $htName = $Matches[1]
        $htValue = $Matches[2]
        if ($htName -cnotin $htAllowedNames) { throw "Unsupported environment variable at line ${htLineNumber}: $htName" }
        if ($htValues.ContainsKey($htName)) { throw "Duplicate environment variable at line ${htLineNumber}: $htName" }
        $htValues[$htName] = $htValue
    }
    return $htValues
}

function Assert-HustlyDevelopmentEnvironment([hashtable]$Values) {
    $htRequired = @('DJANGO_ENVIRONMENT', 'DJANGO_SECRET_KEY', 'DJANGO_DEBUG',
        'DJANGO_ALLOWED_HOSTS', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
        'POSTGRES_HOST', 'POSTGRES_PORT')
    $htMissing = @($htRequired | Where-Object { -not $Values.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($Values[$_]) })
    if ($htMissing.Count -gt 0) { throw "Missing required environment variables: $($htMissing -join ', '). Configure the existing local values privately; no credentials are generated." }
    if ($Values.DJANGO_ENVIRONMENT.Trim() -cne 'development') { throw 'This launcher requires DJANGO_ENVIRONMENT=development; production is refused.' }
    if ($Values.DJANGO_DEBUG.Trim().ToLowerInvariant() -notin @('1', '0', 'true', 'false', 'yes', 'no', 'on', 'off')) { throw 'Invalid boolean: DJANGO_DEBUG' }
    $htHosts = @($Values.DJANGO_ALLOWED_HOSTS.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ('127.0.0.1' -notin $htHosts -or @($htHosts | Where-Object { $_ -notin @('127.0.0.1', 'localhost', '[::1]') }).Count -gt 0) {
        throw 'DJANGO_ALLOWED_HOSTS must include 127.0.0.1 and contain only local loopback hosts for this development launcher.'
    }
    if ($Values.POSTGRES_DB.Trim() -cne 'hustlytasker_db' -or $Values.POSTGRES_USER.Trim() -cne 'hustlytasker_user') {
        throw 'POSTGRES_DB/POSTGRES_USER do not identify the existing HustlyTasker development database; launch refused.'
    }
    if ($Values.POSTGRES_HOST.Trim() -notin @('127.0.0.1', 'localhost', '::1') -or $Values.POSTGRES_PORT.Trim() -ne '5432') {
        throw 'POSTGRES_HOST/POSTGRES_PORT must select the existing loopback development PostgreSQL endpoint.'
    }
}

function New-HustlyDevelopmentProcessInfo([string]$Repository, [hashtable]$Values, [string]$Mode, [int]$ListenPort = 8000) {
    if ($Mode -notin @('check', 'runserver') -or $ListenPort -lt 1024 -or $ListenPort -gt 65535) { throw 'Unsupported development launch mode or port.' }
    $htInfo = New-Object System.Diagnostics.ProcessStartInfo
    $htInfo.FileName = Join-Path $Repository 'backend/venv/Scripts/python.exe'
    $htInfo.WorkingDirectory = Join-Path $Repository 'backend'
    $htInfo.UseShellExecute = $false
    $htInfo.Arguments = if ($Mode -eq 'check') { 'manage.py check' } else { "manage.py runserver 127.0.0.1:$ListenPort --noreload" }
    # The selected file is authoritative. Stale deployment/Python/libpq settings
    # in the terminal cannot change settings module, import path or DB endpoint.
    foreach ($htName in @($htInfo.EnvironmentVariables.Keys)) {
        if ($htName -match '^(DJANGO_|POSTGRES_|DRF_|PG|PYTHON)' -or $htName -eq 'DATABASE_URL') {
            $htInfo.EnvironmentVariables.Remove($htName)
        }
    }
    foreach ($htName in $Values.Keys) { $htInfo.EnvironmentVariables[$htName] = $Values[$htName] }
    $htInfo.EnvironmentVariables['PYTHONUNBUFFERED'] = '1'
    return $htInfo
}

# Pure parser/launch-plan functions are imported by the guard test script.
# Dot-sourcing never loads private files or starts Python.
if ($MyInvocation.InvocationName -eq '.') { return }

$htProcess = $null
$htStarted = $false
try {
    $htRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $htEnvironmentPath = if ([IO.Path]::IsPathRooted($EnvFile)) { [IO.Path]::GetFullPath($EnvFile) } else { [IO.Path]::GetFullPath((Join-Path $htRepository $EnvFile)) }
    if (-not $htEnvironmentPath.StartsWith("$htRepository$([IO.Path]::DirectorySeparatorChar)", [StringComparison]::OrdinalIgnoreCase)) { throw 'The local environment file must be inside this repository and Git-ignored.' }
    if (-not (Test-Path -LiteralPath $htEnvironmentPath -PathType Leaf)) {
        throw 'Local environment file is missing. Copy .env.example to .env once and configure DJANGO_SECRET_KEY and the EXISTING POSTGRES_PASSWORD privately; never regenerate database credentials.'
    }
    $htItem = Get-Item -LiteralPath $htEnvironmentPath
    if ($htItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked environment files are refused; use a regular Git-ignored local file.' }
    & git -C $htRepository check-ignore --quiet -- $htEnvironmentPath
    if ($LASTEXITCODE -ne 0) { throw 'The local environment file must be Git-ignored before it can be loaded.' }
    $htValues = Read-HustlyDevelopmentEnvironment -Lines ([IO.File]::ReadAllLines($htEnvironmentPath))
    Assert-HustlyDevelopmentEnvironment -Values $htValues
    $htPython = Join-Path $htRepository 'backend/venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $htPython -PathType Leaf)) { throw 'Existing backend/venv/Scripts/python.exe was not found. This launcher does not create or replace the Owner virtualenv.' }
    if ($ValidateOnly) { Write-Output 'Local development configuration validated (values hidden). Python/Django and database connectivity were not checked.'; exit 0 }
    $htMode = if ($Check) { 'check' } else { 'runserver' }
    $htProcess = New-Object System.Diagnostics.Process
    $htProcess.StartInfo = New-HustlyDevelopmentProcessInfo -Repository $htRepository -Values $htValues -Mode $htMode -ListenPort $Port
    Write-Output $(if ($Check) { 'Running Django system checks with the existing virtualenv; environment values hidden.' } else { "Starting Django development at http://127.0.0.1:$Port (no automatic migrations, fixtures or reload). Press Ctrl+C to stop." })
    if (-not $htProcess.Start()) { throw 'Cannot start the existing virtualenv Python process.' }
    $htStarted = $true
    # Retaining the handle gives a reliable native child exit code on Windows.
    $htHandle = $htProcess.Handle
    $htProcess.WaitForExit()
    exit ([int]$htProcess.ExitCode)
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $htProcess) {
        if ($htStarted -and -not $htProcess.HasExited) { $htProcess.Kill(); $htProcess.WaitForExit() }
        $htProcess.Dispose()
    }
}

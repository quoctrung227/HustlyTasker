[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'start-backend-dev.ps1')
$htTestsPassed = 0

function Assert-True([bool]$Condition, [string]$Label) {
    if (-not $Condition) { throw "FAILED: $Label" }
}
function Expect-Failure([scriptblock]$Action, [string]$MessagePattern, [string]$Label) {
    try { & $Action } catch {
        Assert-True ($_.Exception.Message -match $MessagePattern) $Label
        return
    }
    throw "FAILED: $Label (no error)"
}
function New-TestValues {
    return @{
        DJANGO_ENVIRONMENT='development'; DJANGO_SECRET_KEY='synthetic-only-not-a-real-key';
        DJANGO_DEBUG='true'; DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,[::1]';
        POSTGRES_DB='hustlytasker_db'; POSTGRES_USER='hustlytasker_user';
        POSTGRES_PASSWORD='synthetic-only-not-a-real-password'; POSTGRES_HOST='127.0.0.1'; POSTGRES_PORT='5432'
    }
}
function Run-Test([string]$Label, [scriptblock]$Action) {
    & $Action
    $script:htTestsPassed++
    Write-Output "PASS: $Label"
}

Run-Test 'literal values, comments, blank optional values and first equals' {
    $htValues = Read-HustlyDevelopmentEnvironment @(' # comment', '', 'POSTGRES_PASSWORD=literal#value=with$dollar`and-quotes"', 'DJANGO_SMTP_PASSWORD=')
    Assert-True ($htValues.POSTGRES_PASSWORD -ceq 'literal#value=with$dollar`and-quotes"') 'literal password unchanged'
    Assert-True ($htValues.DJANGO_SMTP_PASSWORD -ceq '') 'optional blank unchanged'
}
Run-Test 'command text is data and never executed' {
    $htValues = Read-HustlyDevelopmentEnvironment @('POSTGRES_PASSWORD=$(throw ''must not execute'')')
    Assert-True ($htValues.POSTGRES_PASSWORD -ceq '$(throw ''must not execute'')') 'no evaluation'
}
Run-Test 'malformed lines do not echo their contents' {
    $htPrivateMarker = 'synthetic-content-not-for-error'
    try { Read-HustlyDevelopmentEnvironment @("INVALID $htPrivateMarker") } catch {
        Assert-True ($_.Exception.Message -match 'line 1' -and -not $_.Exception.Message.Contains($htPrivateMarker)) 'safe syntax error'
        return
    }
    throw 'Malformed line was accepted.'
}
Run-Test 'NUL is rejected without reflecting the line' {
    Expect-Failure { Read-HustlyDevelopmentEnvironment @("POSTGRES_PASSWORD=bad$([char]0)value") } 'line 1' 'NUL guard'
}
Run-Test 'duplicate environment keys are refused' {
    Expect-Failure { Read-HustlyDevelopmentEnvironment @('DJANGO_DEBUG=true', 'DJANGO_DEBUG=false') } 'Duplicate.*DJANGO_DEBUG' 'duplicate guard'
}
Run-Test 'arbitrary executable or import environment keys are refused' {
    foreach ($htName in @('PATH', 'PYTHONPATH', 'DJANGO_SETTINGS_MODULE', 'PGSERVICE', 'DATABASE_URL')) {
        Expect-Failure { Read-HustlyDevelopmentEnvironment @("$htName=synthetic-value") } 'Unsupported' 'allowlist guard'
    }
}
Run-Test 'required names are reported together without values' {
    $htValues = New-TestValues
    $htValues.Remove('DJANGO_SECRET_KEY'); $htValues.Remove('POSTGRES_PASSWORD'); $htValues.POSTGRES_USER=' '
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'Missing.*DJANGO_SECRET_KEY.*POSTGRES_USER.*POSTGRES_PASSWORD' 'required names'
}
Run-Test 'nine required fields suffice without copying optional settings defaults' {
    Assert-HustlyDevelopmentEnvironment (New-TestValues)
}
Run-Test 'production is refused' {
    $htValues = New-TestValues; $htValues.DJANGO_ENVIRONMENT='production'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'production is refused' 'development only'
}
Run-Test 'invalid boolean and wildcard hosts are refused' {
    $htValues = New-TestValues; $htValues.DJANGO_DEBUG='invalid'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'DJANGO_DEBUG' 'boolean guard'
    $htValues.DJANGO_DEBUG='false'; $htValues.DJANGO_ALLOWED_HOSTS='127.0.0.1,*'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'DJANGO_ALLOWED_HOSTS' 'hosts guard'
}
Run-Test 'different database identity and remote endpoint are refused' {
    $htValues = New-TestValues; $htValues.POSTGRES_DB='other-database'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'POSTGRES_DB/POSTGRES_USER' 'database identity'
    $htValues.POSTGRES_DB='hustlytasker_db'; $htValues.POSTGRES_HOST='database.example.test'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'POSTGRES_HOST/POSTGRES_PORT' 'remote endpoint'
    $htValues.POSTGRES_HOST='127.0.0.1'; $htValues.POSTGRES_PORT='5433'
    Expect-Failure { Assert-HustlyDevelopmentEnvironment $htValues } 'POSTGRES_HOST/POSTGRES_PORT' 'different endpoint'
}
Run-Test 'child process uses existing venv, loopback, check or runserver only' {
    $htRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $htInfo = New-HustlyDevelopmentProcessInfo $htRoot (New-TestValues) 'check'
    Assert-True ($htInfo.FileName -eq (Join-Path $htRoot 'backend/venv/Scripts/python.exe')) 'existing venv'
    Assert-True ($htInfo.Arguments -eq 'manage.py check' -and -not $htInfo.UseShellExecute) 'check arguments'
    $htInfo = New-HustlyDevelopmentProcessInfo $htRoot (New-TestValues) 'runserver' 8123
    Assert-True ($htInfo.Arguments -eq 'manage.py runserver 127.0.0.1:8123 --noreload') 'loopback server'
    Expect-Failure { New-HustlyDevelopmentProcessInfo $htRoot (New-TestValues) 'migrate' } 'Unsupported' 'migration command refused'
}
Run-Test 'child environment is isolated and security settings are preserved' {
    $htNames = @('DJANGO_SETTINGS_MODULE', 'DJANGO_SECRET_KEY', 'PGSERVICE', 'PYTHONPATH')
    $htOriginal = @{}
    foreach ($htName in $htNames) { $htOriginal[$htName] = [Environment]::GetEnvironmentVariable($htName, 'Process') }
    try {
        foreach ($htName in $htNames) { [Environment]::SetEnvironmentVariable($htName, 'synthetic-stale-inherited-value', 'Process') }
        $htValues = New-TestValues; $htValues.DJANGO_SESSION_COOKIE_SECURE='true'
        $htInfo = New-HustlyDevelopmentProcessInfo (Get-Location).Path $htValues 'check'
        foreach ($htName in @('DJANGO_SETTINGS_MODULE', 'PGSERVICE', 'PYTHONPATH')) { Assert-True (-not $htInfo.EnvironmentVariables.ContainsKey($htName)) 'stale override removed' }
        Assert-True ($htInfo.EnvironmentVariables['DJANGO_SECRET_KEY'] -ceq $htValues.DJANGO_SECRET_KEY) 'selected stable key'
        Assert-True ($htInfo.EnvironmentVariables['DJANGO_SESSION_COOKIE_SECURE'] -ceq 'true') 'security policy retained'
        foreach ($htName in $htNames) { Assert-True ([Environment]::GetEnvironmentVariable($htName, 'Process') -ceq 'synthetic-stale-inherited-value') 'parent unchanged' }
    } finally {
        foreach ($htName in $htNames) { [Environment]::SetEnvironmentVariable($htName, $htOriginal[$htName], 'Process') }
    }
}

Write-Output "BACKEND_DEV_GUARD_TESTS_PASSED=$htTestsPassed"
exit 0

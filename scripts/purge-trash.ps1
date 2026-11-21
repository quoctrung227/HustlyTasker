[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$htRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $PSScriptRoot 'start-backend-dev.ps1')
$htEnvironment = Join-Path $htRepository '.env'
if (-not (Test-Path -LiteralPath $htEnvironment -PathType Leaf) -or
    ((Get-Item -LiteralPath $htEnvironment).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'A regular existing Git-ignored local environment file is required.'
}
& git -C $htRepository check-ignore --quiet -- $htEnvironment
if ($LASTEXITCODE -ne 0) { throw 'Private local environment must be Git-ignored.' }
$htValues = Read-HustlyDevelopmentEnvironment -Lines ([IO.File]::ReadAllLines($htEnvironment))
$htProcess = $null
try {
    Assert-HustlyDevelopmentEnvironment -Values $htValues
    $htPurgeEnabled = $htValues.ContainsKey('DJANGO_TRASH_PURGE_ENABLED') -and $htValues.DJANGO_TRASH_PURGE_ENABLED.Trim().ToLowerInvariant() -cin @('true','1','yes','on')
    if ($Execute -and -not $htPurgeEnabled) {
        throw 'Purge execution is disabled. Separate Owner approval and explicit local configuration are required.'
    }
    $htInfo = New-HustlyDevelopmentProcessInfo -Repository $htRepository -Values $htValues -Mode check
    $htInfo.Arguments = 'manage.py purge_trash' + $(if ($Execute) { ' --execute' } else { '' })
    $htInfo.CreateNoWindow = $true
    $htInfo.EnvironmentVariables['PGCONNECT_TIMEOUT'] = '10'
    $htInfo.EnvironmentVariables['PGOPTIONS'] = '-c lock_timeout=5000 -c statement_timeout=60000'
    $htProcess = [Diagnostics.Process]::new()
    $htProcess.StartInfo = $htInfo
    if (-not $htProcess.Start()) { throw 'Existing backend virtualenv could not start.' }
    $htHandle = $htProcess.Handle
    $htProcess.WaitForExit()
    exit ([int]$htProcess.ExitCode)
} finally {
    $htValues.Clear()
    if ($null -ne $htProcess) { $htProcess.Dispose() }
}

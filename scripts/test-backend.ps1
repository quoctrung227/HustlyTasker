[CmdletBinding(DefaultParameterSetName = 'Run')]
param(
    [Parameter(ParameterSetName = 'Run', Position = 0)]
    [string[]]$TestLabel = @(),
    [Parameter(Mandatory = $true, ParameterSetName = 'Cleanup')]
    [ValidatePattern('^[a-f0-9]{32}$')]
    [string]$CleanupRunId
)

$ErrorActionPreference = 'Stop'
$htRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd([IO.Path]::DirectorySeparatorChar)
$htComposeFile = Join-Path $htRepository 'docker/compose.test.yml'
$htRunId = if ($CleanupRunId) { $CleanupRunId } else { [Guid]::NewGuid().ToString('N') }
$htProject = "ht-test-$htRunId"
$htCompose = @('compose', '--project-name', $htProject, '--file', $htComposeFile)

function Invoke-CheckedDocker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'A test Docker command failed. No development resource was selected.' }
}

function Remove-OwnedTestResources {
    # Inspect every candidate before deleting any. Names alone never establish ownership.
    $containerIds = @(& docker ps -aq --filter "label=com.docker.compose.project=$htProject" --filter "label=org.hustlytasker.test-run=$htRunId")
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect test containers; cleanup refused.' }
    $networkIds = @(& docker network ls -q --filter "label=com.docker.compose.project=$htProject" --filter "label=org.hustlytasker.test-run=$htRunId")
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect test networks; cleanup refused.' }
    foreach ($id in $containerIds) {
        $raw = & docker inspect $id
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect test container; cleanup refused.' }
        $item = @($raw | ConvertFrom-Json)[0]
        $labels = $item.Config.Labels
        if ($labels.'org.hustlytasker.test-run' -ne $htRunId -or
            $labels.'org.hustlytasker.test-repository' -ne $htRepository -or
            $labels.'com.docker.compose.project' -ne $htProject) {
            throw 'Container ownership does not match this repository/run; cleanup refused.'
        }
        $service = $labels.'com.docker.compose.service'
        if ($service -eq 'postgres') {
            $validName = $item.Name -in @("/$htProject-postgres-1", "/${htProject}_postgres_1")
            $validResource = $validName -and $item.Config.Image -eq 'postgres:16' -and
                @($item.Mounts | Where-Object { $_.Type -eq 'volume' }).Count -eq 0
        } elseif ($service -eq 'backend-tests') {
            $sourceMounts = @($item.Mounts | Where-Object { $_.Destination -eq '/workspace' })
            $validResource = $item.Name -eq "/$htProject-backend-tests" -and
                $item.Config.Image -eq 'hustlytasker-backend-tests:local' -and
                $sourceMounts.Count -eq 1 -and $sourceMounts[0].Type -eq 'bind' -and
                $sourceMounts[0].Source -eq $htRepository -and -not $sourceMounts[0].RW
        } else { $validResource = $false }
        if (-not $validResource) { throw 'Unexpected test container identity/mount; cleanup refused.' }
    }
    foreach ($id in $networkIds) {
        $raw = & docker network inspect $id
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect test network; cleanup refused.' }
        $item = @($raw | ConvertFrom-Json)[0]
        if ($item.Labels.'org.hustlytasker.test-run' -ne $htRunId -or
            $item.Labels.'org.hustlytasker.test-repository' -ne $htRepository -or
            $item.Labels.'com.docker.compose.project' -ne $htProject -or
            $item.Name -ne "${htProject}_default") {
            throw 'Network ownership does not match this repository/run; cleanup refused.'
        }
    }
    foreach ($id in $containerIds) { Invoke-CheckedDocker @('rm', '--force', $id) }
    foreach ($id in $networkIds) { Invoke-CheckedDocker @('network', 'rm', $id) }
}

foreach ($label in $TestLabel) {
    if ($label -notmatch '^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$') {
        throw 'Test labels must be dotted Python names; arbitrary Django options are not accepted.'
    }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop/Engine with Compose v2 is required.' }

# Compose must not read the Owner's .env or inherit deployment credentials.
$htEnvironmentNames = @('HT_TEST_RESOURCE_ID', 'HT_TEST_REPOSITORY', 'COMPOSE_DISABLE_ENV_FILE')
$htOriginalEnvironment = @{}
foreach ($name in $htEnvironmentNames) { $htOriginalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$htExitCode = 1
try {
    $env:HT_TEST_RESOURCE_ID = $htRunId
    $env:HT_TEST_REPOSITORY = $htRepository
    $env:COMPOSE_DISABLE_ENV_FILE = '1'
    Write-Host "HustlyTasker isolated test run: $htRunId"
    if ($CleanupRunId) {
        Remove-OwnedTestResources
        $htExitCode = 0
    } else {
        Invoke-CheckedDocker ($htCompose + @('build', 'backend-tests'))
        Invoke-CheckedDocker ($htCompose + @('up', '--detach', '--wait', 'postgres'))
        & docker @htCompose run --name "$htProject-backend-tests" --no-deps backend-tests python /workspace/scripts/test_backend.py @TestLabel
        $htExitCode = $LASTEXITCODE
    }
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
} finally {
    if (-not $CleanupRunId) {
        try { Remove-OwnedTestResources } catch {
            Write-Error -Message $_.Exception.Message -ErrorAction Continue
            Write-Host "After checking the Docker daemon, retry: .\scripts\test-backend.ps1 -CleanupRunId $htRunId"
            $htExitCode = 1
        }
    }
    foreach ($name in $htEnvironmentNames) { [Environment]::SetEnvironmentVariable($name, $htOriginalEnvironment[$name], 'Process') }
}
exit $htExitCode

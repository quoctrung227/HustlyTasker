[CmdletBinding()]
param(
    [ValidateRange(1024,65535)]
    [int]$BackendPort = 8001,
    [ValidateSet('foundation','work-management','collaboration','acceptance','account-security')]
    [string]$Suite = 'foundation'
)

$ErrorActionPreference = 'Stop'
$htRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd([IO.Path]::DirectorySeparatorChar)
$htRun = [Guid]::NewGuid().ToString('N')
$htPrefix = "ht-fe-$htRun"
$htNetwork = "$htPrefix-network"
$htHttpNetwork = "$htPrefix-http"
$htPg = "$htPrefix-postgres"
$htServer = "$htPrefix-backend"
$htLabelRun = "org.hustlytasker.fe-run=$htRun"
$htLabelRepo = "org.hustlytasker.fe-repository=$htRepository"
$htNames = @('HT_TEST_RUN_ID','HT_TEST_MODE','HT_TEST_DB_HOST','HT_TEST_DB_PORT',
    'HT_FRONTEND_TEST_EMAIL','HT_FRONTEND_TEST_OWNER_EMAIL','HT_FRONTEND_TEST_PASSWORD',
    'HT_FRONTEND_TEST_BACKEND_CONTAINER','HT_FRONTEND_TEST_RUN_ID','HT_FRONTEND_SCREENSHOT_DIR',
    'DJANGO_API_TARGET','PLAYWRIGHT_CHANNEL')
$htSaved = @{}
foreach ($htName in $htNames) { $htSaved[$htName] = [Environment]::GetEnvironmentVariable($htName,'Process') }
$htExit = 1
$htCreatedNetwork = $false
$htCreatedHttpNetwork = $false
$htCreatedPg = $false
$htCreatedServer = $false
$htServerReady = $false
$htSpec = switch ($Suite) {
    'account-security' {'e2e/account-security.spec.ts'}
    'acceptance' {'e2e/mvp-acceptance.spec.ts'}
    'collaboration' {'e2e/collaboration.spec.ts'}
    'work-management' {'e2e/work-management.spec.ts'}
    default {'e2e/real-api.spec.ts'}
}
$htArtifactTask = switch ($Suite) {
    'account-security' {'HT-FE-P3-04'}
    'acceptance' {'HT-FE-P3-04'}
    'collaboration' {'HT-FE-P3-03'}
    'work-management' {'HT-FE-P3-02'}
    default {'HT-FE-P3-01'}
}

function Invoke-CheckedDocker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Isolated frontend Docker operation failed.' }
}

function Assert-OwnedNetwork([string]$Name,[bool]$Internal) {
    if (($Name -ne $htNetwork -or -not $Internal) -and
        ($Name -ne $htHttpNetwork -or $Internal)) {throw 'Unexpected integration network selection.'}
    $raw = & docker network inspect $Name
    if ($LASTEXITCODE -ne 0) {throw 'Cannot verify integration network ownership.'}
    $network = @($raw | ConvertFrom-Json)[0]
    if ($network.Name -ne $Name -or [bool]$network.Internal -ne $Internal -or
        $network.Driver -ne 'bridge' -or
        $network.Labels.'org.hustlytasker.fe-run' -ne $htRun -or
        $network.Labels.'org.hustlytasker.fe-repository' -ne $htRepository) {
        throw 'Integration network identity/internal flag mismatch.'
    }
}

function Assert-OwnedContainer([string]$Name,[string]$Image,[string]$Purpose) {
    $raw = & docker inspect $Name
    if ($LASTEXITCODE -ne 0) {throw 'Cannot verify integration container ownership.'}
    $item = @($raw | ConvertFrom-Json)[0]
    $attached = @($item.NetworkSettings.Networks.PSObject.Properties | ForEach-Object {$_.Name})
    $partial = $item.State.Status -in @('created','exited')
    if ($Purpose -eq 'postgres') {
        $expectedNetwork = $item.HostConfig.NetworkMode -eq $htNetwork -and (
            ($attached.Count -eq 1 -and $attached -contains $htNetwork) -or
            ($partial -and $attached.Count -eq 0))
    } elseif ($Purpose -eq 'backend') {
        $bothNetworks = $attached.Count -eq 2 -and $attached -contains $htNetwork -and $attached -contains $htHttpNetwork
        # Creation precedes connecting PostgreSQL's private network. If that
        # connection/start fails, only these exact incomplete states are owned.
        $partialNetworks = $partial -and ($attached.Count -eq 0 -or
            ($attached.Count -eq 1 -and $attached -contains $htHttpNetwork))
        $expectedNetwork = $item.HostConfig.NetworkMode -eq $htHttpNetwork -and ($bothNetworks -or $partialNetworks)
    } else {throw 'Unknown integration container purpose.'}
    if ($item.Name -ne "/$Name" -or $item.Config.Image -ne $Image -or
        $item.Config.Labels.'org.hustlytasker.fe-run' -ne $htRun -or
        $item.Config.Labels.'org.hustlytasker.fe-repository' -ne $htRepository -or
        $item.Config.Labels.'org.hustlytasker.fe-purpose' -ne $Purpose -or
        -not $expectedNetwork -or
        @($item.Mounts | Where-Object {$_.Type -eq 'volume'}).Count -ne 0) {
        throw 'Integration ownership/network/volume gate refused operation.'
    }
    if ($Purpose -eq 'postgres') {
        if (@($item.HostConfig.Tmpfs.PSObject.Properties.Name) -notcontains '/var/lib/postgresql/data' -or
            @($item.HostConfig.PortBindings.PSObject.Properties).Count -ne 0) {
            throw 'Integration PostgreSQL must be unpublished and tmpfs-only.'
        }
    } else {
        $source = @($item.Mounts | Where-Object {$_.Destination -eq '/workspace'})
        if ($source.Count -ne 1 -or $source[0].Type -ne 'bind' -or $source[0].RW -or
            $source[0].Source -ne $htRepository) {throw 'Integration source mount is not read-only.'}
        $bindings = @($item.HostConfig.PortBindings.'8000/tcp')
        if (@($item.HostConfig.PortBindings.PSObject.Properties).Count -ne 1 -or
            $bindings.Count -ne 1 -or $bindings[0].HostIp -ne '127.0.0.1' -or
            $bindings[0].HostPort -ne [string]$BackendPort) {throw 'Integration HTTP binding is not the approved loopback port.'}
    }
}

function Assert-PublishedBackendPort {
    $raw = & docker inspect $htServer
    if ($LASTEXITCODE -ne 0) {throw 'Cannot inspect integration HTTP port publication.'}
    $item = @($raw | ConvertFrom-Json)[0]
    $bindings = @($item.NetworkSettings.Ports.'8000/tcp')
    if (-not $item.State.Running -or $bindings.Count -ne 1 -or
        $bindings[0].HostIp -ne '127.0.0.1' -or
        $bindings[0].HostPort -ne [string]$BackendPort) {
        throw 'Integration backend has no active loopback HTTP mapping; refusing a futile readiness wait.'
    }
}

function Remove-OwnedResources {
    $cleanupProblem = $null
    # A failed Docker start may still leave a created container. Discover only
    # exact run/repository-labelled resources before applying the same gates.
    $candidates = @(& docker ps -a --filter "label=$htLabelRun" --filter "label=$htLabelRepo" --format '{{.Names}}')
    if ($LASTEXITCODE -ne 0) {throw 'Cannot discover owned integration containers.'}
    foreach ($candidate in $candidates) {
        if ($candidate -eq $htServer) {$htCreatedServer = $true}
        elseif ($candidate -eq $htPg) {$htCreatedPg = $true}
        else {throw 'Unexpected run-labelled container; cleanup refused.'}
    }
    $networkCandidates = @(& docker network ls --filter "label=$htLabelRun" --filter "label=$htLabelRepo" --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0) {throw 'Cannot discover owned integration networks.'}
    foreach ($candidate in $networkCandidates) {
        if ($candidate -eq $htNetwork) {$htCreatedNetwork = $true}
        elseif ($candidate -eq $htHttpNetwork) {$htCreatedHttpNetwork = $true}
        else {throw 'Unexpected run-labelled network; cleanup refused.'}
    }
    if ($htCreatedServer) {Assert-OwnedContainer $htServer 'hustlytasker-backend-tests:local' 'backend'}
    if ($htCreatedPg) {Assert-OwnedContainer $htPg 'postgres:16' 'postgres'}
    if ($htCreatedNetwork) {Assert-OwnedNetwork $htNetwork $true}
    if ($htCreatedHttpNetwork) {Assert-OwnedNetwork $htHttpNetwork $false}
    if ($htCreatedServer) {
        Invoke-CheckedDocker @('stop','--time','15',$htServer)
        if ($htServerReady) {
            $serverCode = & docker inspect $htServer --format '{{.State.ExitCode}}'
            if ($LASTEXITCODE -ne 0) {throw 'Cannot inspect isolated backend exit code.'}
            # Drain native streams separately: expected CSRF warnings on stderr
            # must not become PowerShell NativeCommandError or leak fixture data.
            $logProcess = New-Object System.Diagnostics.Process
            $logProcess.StartInfo.FileName = 'docker'
            $logProcess.StartInfo.Arguments = "logs $htServer"
            $logProcess.StartInfo.UseShellExecute = $false
            $logProcess.StartInfo.CreateNoWindow = $true
            $logProcess.StartInfo.RedirectStandardOutput = $true
            $logProcess.StartInfo.RedirectStandardError = $true
            if (-not $logProcess.Start()) {throw 'Cannot inspect isolated backend cleanup evidence.'}
            $logHandle = $logProcess.Handle
            $logOutput = $logProcess.StandardOutput.ReadToEndAsync()
            $logError = $logProcess.StandardError.ReadToEndAsync()
            $logProcess.WaitForExit()
            $serverLog = $logOutput.GetAwaiter().GetResult()
            $null = $logError.GetAwaiter().GetResult()
            if ($logProcess.ExitCode -ne 0) {throw 'Cannot inspect isolated backend cleanup evidence.'}
            $logProcess.Dispose()
            if ($serverCode -ne '0' -or $serverLog -notmatch 'Owned integration database removed\.') {
                $cleanupProblem = 'Backend exit/owned database cleanup evidence did not pass.'
            } else {
                Write-Output 'ISOLATED_BACKEND_EXIT_CODE=0; OWNED_DATABASE_REMOVAL_CONFIRMED'
            }
        }
        Invoke-CheckedDocker @('rm',$htServer)
    }
    if ($htCreatedPg) {
        Invoke-CheckedDocker @('stop','--time','10',$htPg)
        Invoke-CheckedDocker @('rm',$htPg)
    }
    if ($htCreatedNetwork) {Invoke-CheckedDocker @('network','rm',$htNetwork)}
    if ($htCreatedHttpNetwork) {Invoke-CheckedDocker @('network','rm',$htHttpNetwork)}
    Write-Output 'OWNED_FRONTEND_INTEGRATION_RESOURCES_REMOVED'
    if ($cleanupProblem) {throw $cleanupProblem}
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Docker and Node/npm are required; no installation is attempted.'
    }
    if ($BackendPort -in @(5432,5173)) {throw 'Integration backend port conflicts with protected/default services.'}
    & docker image inspect hustlytasker-backend-tests:local --format '{{.Id}}'
    if ($LASTEXITCODE -ne 0) {throw 'Build the existing backend test image first; no deployment configuration is used.'}
    $env:HT_TEST_RUN_ID = $htRun
    $env:HT_TEST_MODE = 'docker'
    $env:HT_TEST_DB_HOST = 'postgres'
    $env:HT_TEST_DB_PORT = '5432'
    $env:HT_FRONTEND_TEST_EMAIL = "member.$htRun@example.test"
    $env:HT_FRONTEND_TEST_OWNER_EMAIL = "owner.$htRun@example.test"
    $env:HT_FRONTEND_TEST_PASSWORD = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N') + 'Az!9'
    $env:HT_FRONTEND_TEST_BACKEND_CONTAINER = $htServer
    $env:HT_FRONTEND_TEST_RUN_ID = $htRun
    $env:HT_FRONTEND_SCREENSHOT_DIR = Join-Path $htRepository ".local_backups/$htArtifactTask/screenshots/$htRun"
    $null = New-Item -ItemType Directory -Path $env:HT_FRONTEND_SCREENSHOT_DIR
    if (-not $env:PLAYWRIGHT_CHANNEL) {
        if (Test-Path -LiteralPath 'C:\Program Files\Google\Chrome\Application\chrome.exe') {$env:PLAYWRIGHT_CHANNEL='chrome'}
        elseif (Test-Path -LiteralPath 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe') {$env:PLAYWRIGHT_CHANNEL='msedge'}
    }
    $env:DJANGO_API_TARGET = "http://127.0.0.1:$BackendPort"

    Write-Output "HustlyTasker isolated frontend integration run: $htRun; suite=$Suite"
    Invoke-CheckedDocker @('network','create','--internal','--label',$htLabelRun,'--label',$htLabelRepo,$htNetwork)
    $htCreatedNetwork = $true
    Assert-OwnedNetwork $htNetwork $true
    # Docker Desktop does not publish ports for an internal-only backend.
    # Only the backend joins this separate HTTP bridge; PostgreSQL remains
    # unpublished on its internal, per-run network and tmpfs data directory.
    Invoke-CheckedDocker @('network','create','--driver','bridge','--label',$htLabelRun,'--label',$htLabelRepo,$htHttpNetwork)
    $htCreatedHttpNetwork = $true
    Assert-OwnedNetwork $htHttpNetwork $false
    Invoke-CheckedDocker @('run','--detach','--name',$htPg,'--network',$htNetwork,'--network-alias','postgres',
        '--tmpfs','/var/lib/postgresql/data','--env','POSTGRES_USER=ht_test_runner',
        '--env','POSTGRES_DB=hustlytasker_test_control','--env','POSTGRES_HOST_AUTH_METHOD=trust',
        '--label',$htLabelRun,'--label',$htLabelRepo,'--label','org.hustlytasker.fe-purpose=postgres','postgres:16')
    $htCreatedPg = $true
    Assert-OwnedContainer $htPg 'postgres:16' 'postgres'
    $htReady = $false
    for ($htAttempt=0; $htAttempt -lt 60; $htAttempt++) {
        & docker exec $htPg pg_isready -q -U ht_test_runner -d hustlytasker_test_control
        if ($LASTEXITCODE -eq 0) {$htReady=$true; break}
        Start-Sleep -Seconds 1
    }
    if (-not $htReady) {throw 'Isolated PostgreSQL readiness timeout.'}
    Invoke-CheckedDocker @('create','--name',$htServer,'--network',$htHttpNetwork,
        '--publish',"127.0.0.1:${BackendPort}:8000",'--workdir','/workspace/backend',
        '--mount',"type=bind,source=$htRepository,target=/workspace,readonly",
        '--env','HT_TEST_RUN_ID','--env','HT_TEST_MODE','--env','HT_TEST_DB_HOST','--env','HT_TEST_DB_PORT',
        '--env','HT_FRONTEND_TEST_EMAIL','--env','HT_FRONTEND_TEST_OWNER_EMAIL','--env','HT_FRONTEND_TEST_PASSWORD',
        '--env','PYTHONPATH=/workspace/backend:/workspace/scripts',
        '--label',$htLabelRun,'--label',$htLabelRepo,'--label','org.hustlytasker.fe-purpose=backend',
        'hustlytasker-backend-tests:local','python','/workspace/scripts/frontend_integration.py')
    $htCreatedServer = $true
    Assert-OwnedContainer $htServer 'hustlytasker-backend-tests:local' 'backend'
    Invoke-CheckedDocker @('network','connect',$htNetwork,$htServer)
    Assert-OwnedContainer $htServer 'hustlytasker-backend-tests:local' 'backend'
    Invoke-CheckedDocker @('start',$htServer)
    Assert-OwnedContainer $htServer 'hustlytasker-backend-tests:local' 'backend'
    Assert-PublishedBackendPort
    $htReady = $false
    for ($htAttempt=0; $htAttempt -lt 90; $htAttempt++) {
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri "$env:DJANGO_API_TARGET/api/health/" -TimeoutSec 2
            if ($health.StatusCode -eq 200) {$htReady=$true; break}
        } catch { }
        $state = & docker inspect $htServer --format '{{.State.Running}}'
        if ($LASTEXITCODE -ne 0 -or $state -ne 'true') {throw 'Isolated Django exited before readiness; inspect safe server logs.'}
        Start-Sleep -Seconds 1
    }
    if (-not $htReady) {throw 'Isolated Django readiness timeout.'}
    $htServerReady = $true
    Push-Location (Join-Path $htRepository 'frontend')
    try {
        # Separate fresh runtimes preserve the real login throttle and keep
        # each suite's fixture mutations independent, without changing Django.
        & npm.cmd run test:integration -- $htSpec
        $htExit = $LASTEXITCODE
        if ($null -eq $htExit) {throw 'Frontend test process exit code unavailable.'}
        Write-Output "FRONTEND_PLAYWRIGHT_EXIT_CODE=$htExit"
    } finally {Pop-Location}
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    $htExit = 1
} finally {
    try {Remove-OwnedResources} catch {
        Write-Error -Message $_.Exception.Message -ErrorAction Continue
        Write-Output "Cleanup needs inspection of owned run $htRun; never select development resources."
        $htExit = 1
    }
    foreach ($htName in $htNames) {[Environment]::SetEnvironmentVariable($htName,$htSaved[$htName],'Process')}
}
exit $htExit

[CmdletBinding()]
param([string]$Destination = '.local_backups/HT-TRASH-V1/purge-schedule-disabled.xml')

# Export only. This script never registers/enables/runs a Windows scheduled task.
$ErrorActionPreference = 'Stop'
$htRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$htTarget = [IO.Path]::GetFullPath((Join-Path $htRepository $Destination))
if (-not $htTarget.StartsWith($htRepository + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Schedule export must stay inside the repository in a Git-ignored path.'
}
& git -C $htRepository check-ignore --quiet -- $htTarget
if ($LASTEXITCODE -ne 0) { throw 'Schedule export must be Git-ignored.' }
if (Test-Path -LiteralPath $htTarget) { throw 'Existing export will not be overwritten.' }
$htParent = Split-Path -Parent $htTarget
if (-not (Test-Path -LiteralPath $htParent -PathType Container)) { throw 'Create the ignored output directory first.' }
if ((Get-Item -LiteralPath $htParent).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked export directories are refused.' }
$htUser = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$htStart = [DateTime]::Today.AddDays(1).ToString('yyyy-MM-dd') + 'T03:00:00'
$htArguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'purge-trash.ps1') + '" -Execute'
$htXml = @"
<?xml version="1.0" encoding="UTF-8"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>HustlyTasker conditional Trash purge. Disabled until separate Owner approval.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>$htStart</StartBoundary><Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Principals><Principal id="Owner"><UserId>$htUser</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable><Enabled>false</Enabled><ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings>
  <Actions Context="Owner"><Exec><Command>powershell.exe</Command><Arguments>$([Security.SecurityElement]::Escape($htArguments))</Arguments><WorkingDirectory>$([Security.SecurityElement]::Escape($htRepository))</WorkingDirectory></Exec></Actions>
</Task>
"@
[IO.File]::WriteAllText($htTarget, $htXml, [Text.UTF8Encoding]::new($false))
Write-Output 'Disabled schedule XML exported. No task was registered, enabled or executed.'

# Регистрирует задачу планировщика Windows «TGID backup» для backup-city-dbs.ps1.
# Запускать от администратора:
#   powershell -ExecutionPolicy Bypass -File install-backup-task.ps1
# По умолчанию в 02:30: пн–сб — бэкап всех баз; вс — бэкап и пробное восстановление одной
# базы (RestoreCheck), базы чередуются по номеру недели.
# Задача работает от SYSTEM: пароль Windows не нужен, доступ к PostgreSQL — из .env API.
# Удалить: Unregister-ScheduledTask -TaskName 'TGID backup', 'TGID backup restore check' -Confirm:$false
param(
  [string]$ScriptPath = 'H:\deploy\tgid-server\itwin-api\scripts\ops\backup-city-dbs.ps1',
  [string]$At = '02:30',
  [string[]]$RestoreRotation = @('almatygid', 'astana', 'shatura', 'karagandagid', 'shymkentgid', 'tarazgid', 'aktobegid')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $ScriptPath)) { throw "Нет скрипта $ScriptPath — сначала обновите H:\deploy\tgid-server" }

$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$daily = New-ScheduledTaskAction -Execute $psExe `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday, Saturday -At $At
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 6) -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'TGID backup' -Action $daily -Trigger $trigger -Settings $settings `
  -Principal $principal -Description 'Бэкап баз ТГИД (backup-city-dbs.ps1)' -Force | Out-Null
Write-Host "Задача 'TGID backup': пн–сб в $At"

# Воскресенье: тот же бэкап плюс пробное восстановление, база по номеру недели
$week = [System.Globalization.CultureInfo]::InvariantCulture.Calendar.GetWeekOfYear(
  (Get-Date), [System.Globalization.CalendarWeekRule]::FirstFourDayWeek, [DayOfWeek]::Monday)
$checkCmd = "`$dbs = @('" + ($RestoreRotation -join "','") + "'); " +
  "`$w = [System.Globalization.CultureInfo]::InvariantCulture.Calendar.GetWeekOfYear((Get-Date), 'FirstFourDayWeek', 'Monday'); " +
  "& '$ScriptPath' -RestoreCheck `$dbs[`$w % `$dbs.Count]; exit `$LASTEXITCODE"
$check = New-ScheduledTaskAction -Execute $psExe -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$checkCmd`""
$weekly = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At
Register-ScheduledTask -TaskName 'TGID backup restore check' -Action $check -Trigger $weekly -Settings $settings `
  -Principal $principal -Description 'Бэкап и пробное восстановление одной базы ТГИД' -Force | Out-Null
Write-Host ("Задача 'TGID backup restore check': по воскресеньям в {0}, на этой неделе — {1}" -f $At, $RestoreRotation[$week % $RestoreRotation.Count])
Write-Host 'Журнал: H:\deploy\logs\backup-<год-месяц>.log; итог: H:\tgid-backups\scheduled\last-backup.json'

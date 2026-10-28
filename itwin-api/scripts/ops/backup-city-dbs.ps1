# Плановый бэкап баз ТГИД: базы городов и UsersDB -> pg_dump -Fc, проверка, ротация.
#
#   powershell -ExecutionPolicy Bypass -File backup-city-dbs.ps1
#   powershell -ExecutionPolicy Bypass -File backup-city-dbs.ps1 -RestoreCheck almatygid
#
# Что делает:
#   1. Для каждой базы из -Databases: pg_dump -Fc в <BackupRoot>\daily\<дата>\<база>.dump.
#      Базы, которых нет на сервере, пропускаются с предупреждением (это не ошибка).
#   2. Проверяет каждый файл: pg_restore --list читает оглавление (файл не обрезан).
#   3. По воскресеньям копирует дневной каталог в weekly\. Хранит KeepDaily дневных и
#      KeepWeekly недельных каталогов, более старые удаляет.
#   4. С -RestoreCheck <база>: восстанавливает её свежий дамп во временную базу
#      tgid_restore_check, сверяет число строк в nodes и linesobj с исходной и удаляет
#      временную базу. Занимает место на диске данных PostgreSQL на время проверки.
#   5. Пишет журнал в <LogDir>\backup-<год-месяц>.log и итог в <BackupRoot>\last-backup.json.
# Код выхода 0 — все найденные базы сохранены и проверены, 1 — была ошибка (видно в планировщике).
# Доступ к PostgreSQL — из .env API (DB_HOST/PORT/USER/PASSWORD, USERS_DB_*); пароль не печатается.
param(
  [string[]]$Databases = @(
    'almatygid', 'astana', 'shatura', 'tarazgid', 'aktobegid', 'shymkentgid', 'karagandagid',
    'ekibastuzgid', 'atbasargid', 'kokshetaugid', 'shahtinskgid'
  ),
  [string]$ApiDir = 'H:\deploy\tgid-server\itwin-api',
  [string]$BackupRoot = 'H:\tgid-backups\scheduled',
  [string]$LogDir = 'H:\deploy\logs',
  [string]$PgBin = 'C:\Program Files\PostgreSQL\16\bin',
  [int]$KeepDaily = 7,
  [int]$KeepWeekly = 4,
  [string]$RestoreCheck = ''
)
$ErrorActionPreference = 'Stop'
# powershell -File передаёт список одной строкой: 'a,b' -> 'a', 'b'
$Databases = @($Databases | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PGCLIENTENCODING = 'UTF8'

$pgDump = Join-Path $PgBin 'pg_dump.exe'
$pgRestore = Join-Path $PgBin 'pg_restore.exe'
$psql = Join-Path $PgBin 'psql.exe'
$checkDb = 'tgid_restore_check'
$started = Get-Date
$day = $started.ToString('yyyy-MM-dd')
New-Item -ItemType Directory -Force $LogDir | Out-Null
$logFile = Join-Path $LogDir ("backup-{0}.log" -f $started.ToString('yyyy-MM'))

function Log([string]$msg) {
  $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  Write-Host $line
  Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# --- доступ к БД из .env API ---
$dotenv = @{}
foreach ($line in Get-Content (Join-Path $ApiDir '.env') -Encoding UTF8) {
  $t = $line.Trim()
  if ($t -eq '' -or $t.StartsWith('#') -or -not $t.Contains('=')) { continue }
  $i = $t.IndexOf('=')
  $dotenv[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim().Trim('"').Trim("'")
}
function Get-EnvValue([string]$key, [string]$fallback) {
  if ($dotenv.ContainsKey($key) -and $dotenv[$key] -ne '') { return $dotenv[$key] }
  return $fallback
}
$net = @{
  Host = Get-EnvValue 'DB_HOST' '127.0.0.1'; Port = Get-EnvValue 'DB_PORT' '5432'
  User = Get-EnvValue 'DB_USER' 'postgres'; Password = Get-EnvValue 'DB_PASSWORD' ''
}
$usr = @{
  Host = Get-EnvValue 'USERS_DB_HOST' $net.Host; Port = Get-EnvValue 'USERS_DB_PORT' $net.Port
  User = Get-EnvValue 'USERS_DB_USER' $net.User; Password = Get-EnvValue 'USERS_DB_PASSWORD' $net.Password
}
$usersDb = Get-EnvValue 'USERS_DB_NAME' 'usersdb'

# Запуск утилиты PostgreSQL: пароль только в переменной окружения на время вызова
function Invoke-Pg($conn, [string]$exe, [string[]]$pgArgs) {
  $env:PGPASSWORD = $conn.Password
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'   # NOTICE в stderr не прерывает скрипт; судим по коду выхода
  try {
    $out = & $exe -h $conn.Host -p $conn.Port -U $conn.User @pgArgs 2>&1
    return @{ Code = $LASTEXITCODE; Out = ($out | Out-String) }
  } finally {
    $ErrorActionPreference = $prev
    $env:PGPASSWORD = $null
  }
}
function Get-Scalar($conn, [string]$db, [string]$sql) {
  $r = Invoke-Pg $conn $psql @('-X', '-At', '-d', $db, '-v', 'ON_ERROR_STOP=1', '-c', $sql)
  if ($r.Code -ne 0) { throw "psql ($db): $($r.Out.Trim())" }
  return $r.Out.Trim()
}

$targets = @()
foreach ($db in $Databases) { $targets += , @($net, $db) }
$targets += , @($usr, $usersDb)

$dailyDir = Join-Path $BackupRoot (Join-Path 'daily' $day)
New-Item -ItemType Directory -Force $dailyDir | Out-Null
Log "== Бэкап в $dailyDir"

$results = @()
$failed = $false
foreach ($pair in $targets) {
  $conn = $pair[0]; $db = $pair[1]; $tmp = $null
  $item = [ordered]@{ database = $db; status = 'ok'; size_mb = 0; seconds = 0; error = '' }
  $t0 = Get-Date
  try {
    $exists = Get-Scalar $conn 'postgres' "SELECT count(*) FROM pg_database WHERE datname = '$db'"
    if ($exists -ne '1') {
      $item.status = 'missing'
      Log "  $db — нет на сервере, пропуск"
      $results += $item
      continue
    }
    $file = Join-Path $dailyDir "$db.dump"
    $tmp = "$file.part"
    $r = Invoke-Pg $conn $pgDump @('-Fc', '-f', $tmp, $db)
    if ($r.Code -ne 0 -or -not (Test-Path $tmp) -or (Get-Item $tmp).Length -eq 0) {
      throw "pg_dump завершился с кодом $($r.Code): $($r.Out.Trim())"
    }
    $check = Invoke-Pg $conn $pgRestore @('--list', $tmp)
    if ($check.Code -ne 0) { throw "pg_restore --list не читает файл: $($check.Out.Trim())" }
    Move-Item -Force $tmp $file
    $item.size_mb = [math]::Round((Get-Item $file).Length / 1MB, 2)
    Log ("  {0} — OK, {1:N2} МБ" -f $db, $item.size_mb)
  } catch {
    $failed = $true
    $item.status = 'error'
    $item.error = $_.Exception.Message
    Log "  $db — ОШИБКА: $($item.error)"
    if ($tmp -and (Test-Path $tmp)) { Remove-Item -Force $tmp }
  } finally {
    $item.seconds = [math]::Round(((Get-Date) - $t0).TotalSeconds)
  }
  $results += $item
}

# --- пробное восстановление ---
$restore = $null
if ($RestoreCheck) {
  $restore = [ordered]@{ database = $RestoreCheck; status = 'ok'; error = ''; tables = @{} }
  $file = Join-Path $dailyDir "$RestoreCheck.dump"
  Log "== Пробное восстановление $RestoreCheck -> $checkDb"
  try {
    if (-not (Test-Path $file)) { throw "нет свежего дампа $file" }
    Get-Scalar $net 'postgres' "DROP DATABASE IF EXISTS $checkDb" | Out-Null
    Get-Scalar $net 'postgres' "CREATE DATABASE $checkDb" | Out-Null
    $r = Invoke-Pg $net $pgRestore @('--no-owner', '--no-privileges', '-d', $checkDb, $file)
    # pg_restore даёт код 1 и на предупреждениях (нет роли, расширение уже есть) — судим по данным
    if ($r.Code -ne 0) { Log "  pg_restore: код $($r.Code), сверяю данные" }
    foreach ($table in 'nodes', 'linesobj') {
      $src = Get-Scalar $net $RestoreCheck "SELECT count(*) FROM $table"
      $dst = Get-Scalar $net $checkDb "SELECT count(*) FROM $table"
      $restore.tables[$table] = @{ source = [long]$src; restored = [long]$dst }
      # исходная база могла измениться за время бэкапа: допускаем расхождение не больше 1 %
      if ([math]::Abs([long]$src - [long]$dst) -gt [math]::Max(1, [long]$src * 0.01)) {
        throw "${table}: в исходной $src строк, восстановлено $dst"
      }
      Log "  $table — исходно $src, восстановлено $dst"
    }
  } catch {
    $failed = $true
    $restore.status = 'error'
    $restore.error = $_.Exception.Message
    Log "  ОШИБКА восстановления: $($restore.error)"
  } finally {
    try { Get-Scalar $net 'postgres' "DROP DATABASE IF EXISTS $checkDb" | Out-Null }
    catch { Log "  не удалось удалить ${checkDb}: $($_.Exception.Message)"; $failed = $true }
  }
}

# --- недельная копия и ротация ---
try {
  if ($started.DayOfWeek -eq [DayOfWeek]::Sunday) {
    $weeklyDir = Join-Path $BackupRoot (Join-Path 'weekly' $day)
    New-Item -ItemType Directory -Force $weeklyDir | Out-Null
    Copy-Item -Force (Join-Path $dailyDir '*.dump') $weeklyDir
    Log "== Недельная копия: $weeklyDir"
  }
  foreach ($kind in @(@('daily', $KeepDaily), @('weekly', $KeepWeekly))) {
    $root = Join-Path $BackupRoot $kind[0]
    if (-not (Test-Path $root)) { continue }
    # имена каталогов — даты yyyy-MM-dd, сортировка по имени = по дате
    $old = Get-ChildItem -Directory $root | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' } |
      Sort-Object Name -Descending | Select-Object -Skip $kind[1]
    foreach ($d in $old) {
      Remove-Item -Recurse -Force $d.FullName
      Log "  удалён старый бэкап $($kind[0])\$($d.Name)"
    }
  }
} catch {
  $failed = $true
  Log "ОШИБКА ротации: $($_.Exception.Message)"
}

$summary = [ordered]@{
  started = $started.ToString('s')
  finished = (Get-Date).ToString('s')
  ok = -not $failed
  directory = $dailyDir
  databases = $results
  restore_check = $restore
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $BackupRoot 'last-backup.json') -Encoding UTF8
Log ("== Итог: {0}" -f $(if ($failed) { 'ЕСТЬ ОШИБКИ' } else { 'всё сохранено' }))
if ($failed) { exit 1 }
exit 0

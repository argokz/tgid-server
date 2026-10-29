# Один API на все города (фаза 1 модернизации): служба tgid-api-multi и общие воркеры Celery
# вместо API и воркера на каждый город. ЗАПУСКАТЬ ОТ АДМИНИСТРАТОРА после обновления кода API
# до ветки modernization/phase-0:
#   powershell -ExecutionPolicy Bypass -File H:\deploy\tgid-server\itwin-api\scripts\multicity\install-multicity.ps1
#
# Шаги (повторный запуск безопасен):
#   1. Предпроверки, ничего не меняя: код API, базы городов, лимит соединений PostgreSQL, порт, nginx.
#   2. Службы: tgid-api-multi (127.0.0.1:8060, город — по префиксу /city/<код>/) и tgid-worker-multi-N
#      (очереди tgid.<город> всех городов). Redis — та же БД, что у API Алматы (REDIS_DB из .env):
#      очереди у общего API свои, задачи городских воркеров (очередь celery) они не забирают.
#   3. Проверка: /health по всем базам и /fragments каждого города — так же, как у прежнего API города.
#   4. nginx: /tgid/<город>/map-api/ -> http://127.0.0.1:8060/city/<город>/ (бэкап, nginx -t, reload).
# Прежние службы tgid-api-* и tgid-worker-* не удаляются: откат — тот же скрипт с -Disable (nginx снова
# на порты городов). Проверка входа GeoServer (/auth/check) остаётся на API Алматы.
# Только часть городов: -Only almaty,astana (общий API всё равно обслуживает все города из таблицы).
param(
  [string[]]$Only = @(),
  [switch]$Disable,
  [int]$Port = 8060,
  [int]$ApiWorkers = 2,
  [int]$CeleryWorkers = 2
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$nssm = 'C:\nssm\win64\nssm.exe'
$api = 'H:\deploy\tgid-server\itwin-api'
$py = "$api\venv\Scripts\python.exe"
$celery = "$api\venv\Scripts\celery.exe"
$logs = 'H:\deploy\logs'
$nginxDir = 'C:\nginx'
$citiesConf = "$nginxDir\conf\tgid-cities.conf"
$martinSql = 'C:\tgid\martin\sql'
$apiService = 'tgid-api-multi'
# Пул на базу города в каждом процессе API: 12 городов x 2 процесса x 6 = до 144 соединений
$poolMin = 1
$poolMax = 6

# Код города (как в API cities.py), база, порт прежнего API города (nginx map-api)
$cities = @(
  @{ Code = 'almaty';     Db = 'almatygid';            OldPort = 8011 },
  @{ Code = 'astana';     Db = 'astanagid_2026_09_22'; OldPort = 8021 },
  @{ Code = 'shatura';    Db = 'shatura';              OldPort = 8031 },
  @{ Code = 'taraz';      Db = 'tarazgid';             OldPort = 8051 },
  @{ Code = 'aktobe';     Db = 'aktobegid';            OldPort = 8052 },
  @{ Code = 'shymkent';   Db = 'shymkentgid';          OldPort = 8053 },
  @{ Code = 'karaganda';  Db = 'karagandagid';         OldPort = 8054 },
  @{ Code = 'ekibastuz';  Db = 'ekibastuzgid';         OldPort = 8055 },
  @{ Code = 'atbasar';    Db = 'atbasargid';           OldPort = 8056 },
  @{ Code = 'kokshetau';  Db = 'kokshetaugid';         OldPort = 8057 },
  @{ Code = 'shakhtinsk'; Db = 'shahtinskgid';         OldPort = 8058 },
  @{ Code = 'semey';      Db = 'semeygid';             OldPort = 8059 }
)
$switch = if ($Only.Count) { @($cities | Where-Object { $Only -contains $_.Code }) } else { $cities }
if ($Only.Count -and $switch.Count -ne $Only.Count) { throw "Неизвестный город в -Only: $($Only -join ', ')" }
$workerNames = @(1..$CeleryWorkers | ForEach-Object { "tgid-worker-multi-$_" })

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Invoke-Native([string]$exe, [string[]]$arguments, [string]$dir) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  Push-Location $dir
  try {
    $out = (& $exe @arguments 2>&1 | Out-String)
    return @{ Code = $LASTEXITCODE; Out = $out.Trim() }
  } finally { Pop-Location; $ErrorActionPreference = $old }
}
function Test-Nginx([string]$conf) {
  $r = Invoke-Native "$nginxDir\nginx.exe" @('-t', '-p', "$nginxDir\", '-c', $conf) $nginxDir
  return @{ Ok = ($r.Out -match 'test is successful'); Out = $r.Out }
}
function Get-Text([string]$url, [int]$timeout = 60) {
  try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout).Content } catch { return $null }
}
function Wait-Health([string]$url, [int]$seconds = 180) {
  for ($i = 0; $i -lt $seconds / 3; $i++) {
    if ($null -ne (Get-Text $url 30)) { return $true }
    Start-Sleep -Seconds 3
  }
  return $false
}
function Install-TgidService($name, $exe, $arguments, [string[]]$envVars) {
  if (Get-Service $name -ErrorAction SilentlyContinue) { Stop-TgidService $name; [void](Invoke-Native $nssm @('remove', $name, 'confirm') $api) }
  $r = Invoke-Native $nssm @('install', $name, $exe, $arguments) $api
  if ($r.Code -ne 0) { throw "nssm install $name`: $($r.Out)" }
  foreach ($kv in @(
      @('AppDirectory', $api), @('AppStdout', "$logs\$name.out.log"), @('AppStderr', "$logs\$name.err.log"),
      @('AppRotateFiles', '1'), @('AppRotateOnline', '1'), @('AppRotateBytes', '10485760'),
      @('AppRestartDelay', '5000'), @('Start', 'SERVICE_AUTO_START'))) {
    [void](Invoke-Native $nssm @('set', $name, $kv[0], $kv[1]) $api)
  }
  # прямо в реестр (REG_MULTI_SZ): через аргументы nssm PowerShell 5.1 теряет кавычки
  Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$name\Parameters" -Name AppEnvironmentExtra -Value $envVars -Type MultiString
  Start-TgidService $name
}
# map-api городов в tgid-cities.conf: на общий API (enable) или на порт прежнего API города
function Set-MapApi([string]$text, $city, [bool]$enable) {
  $target = if ($enable) { "http://127.0.0.1:$Port/city/$($city.Code)/" } else { "http://127.0.0.1:$($city.OldPort)/" }
  $pattern = "(location \^~ /tgid/$($city.Code)/map-api/ \{[^}]*?proxy_pass )http://127\.0\.0\.1:\d+/(?:city/$($city.Code)/)?;"
  $rx = [regex]::new($pattern)
  if (-not $rx.IsMatch($text)) { throw "В $citiesConf нет location /tgid/$($city.Code)/map-api/ с proxy_pass" }
  return $rx.Replace($text, { param($m) $m.Groups[1].Value + $target + ';' }, 1)
}
function Reload-Nginx {
  # от имени SYSTEM: служба nginx работает под LocalSystem, у администратора на reload нет прав
  $logBefore = (Get-Item "$nginxDir\logs\error.log").Length
  $task = 'tgid-nginx-reload'
  $action = New-ScheduledTaskAction -Execute "$nginxDir\nginx.exe" -Argument '-p C:/nginx/ -s reload' -WorkingDirectory $nginxDir
  $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Force | Out-Null
  try {
    Start-ScheduledTask -TaskName $task
    for ($i = 0; $i -lt 20 -and (Get-ScheduledTask -TaskName $task).State -eq 'Running'; $i++) { Start-Sleep -Seconds 1 }
    Start-Sleep -Seconds 3
  } finally { Unregister-ScheduledTask -TaskName $task -Confirm:$false }
  $fs = [IO.File]::Open("$nginxDir\logs\error.log", 'Open', 'Read', 'ReadWrite')
  try { [void]$fs.Seek($logBefore, 'Begin'); $tail = (New-Object IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Close() }
  if ($tail -match 'Access is denied|\[emerg\]') { throw "nginx: reload не прошёл:`n$tail" }
  Write-Host 'nginx: reload выполнен' -ForegroundColor Green
}
function Write-Conf([string]$text, [string]$label) {
  $backup = "$citiesConf.bak-multicity-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
  Copy-Item $citiesConf $backup
  [IO.File]::WriteAllText($citiesConf, $text, (New-Object Text.UTF8Encoding($false)))
  $t = Test-Nginx 'conf/nginx.conf'
  if (-not $t.Ok) {
    Copy-Item $backup $citiesConf -Force
    throw "nginx -t не прошёл, tgid-cities.conf возвращён ($label):`n$($t.Out)"
  }
  Write-Host "tgid-cities.conf: $label (прежний — $backup)"
  try { Reload-Nginx } catch {
    Copy-Item $backup $citiesConf -Force
    throw "$($_.Exception.Message)`ntgid-cities.conf возвращён из $backup"
  }
}

. 'H:\deploy\tgid-service-common.ps1'

# --- Откат ---
if ($Disable) {
  Step "Откат: map-api городов ($(($switch | ForEach-Object Code) -join ', ')) — на прежние API городов"
  $text = [IO.File]::ReadAllText($citiesConf)
  foreach ($city in $switch) {
    if (-not (Get-Service "tgid-api$(if ($city.Code -ne 'almaty') { '-' + $city.Code })" -ErrorAction SilentlyContinue)) {
      Write-Host "  $($city.Code): службы прежнего API нет — оставляю на общем API" -ForegroundColor Yellow; continue
    }
    $text = Set-MapApi $text $city $false
  }
  Write-Conf $text 'map-api на прежних API городов'
  if ([IO.File]::ReadAllText($citiesConf) -notmatch "127\.0\.0\.1:$Port/city/") {
    foreach ($name in @($apiService) + $workerNames) {
      if (Get-Service $name -ErrorAction SilentlyContinue) { Stop-TgidService $name; Set-Service $name -StartupType Disabled; Write-Host "$name остановлена" }
    }
  }
  Write-Host "`nОткат выполнен." -ForegroundColor Green
  return
}

# --- 1. Предпроверки ---
Step '1. Предпроверки (ничего не меняется)'
$problems = @()
if (-not (Test-Path "$api\city_context.py")) { $problems += "В $api нет city_context.py — сначала обновите API до ветки modernization/phase-0" }
foreach ($f in $nssm, $py, $celery, "$api\.env", $citiesConf) { if (-not (Test-Path $f)) { $problems += "Нет файла $f" } }
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
  $own = Get-CimInstance Win32_Service -Filter "Name='$apiService'" -ErrorAction SilentlyContinue
  $ownPids = @($own.ProcessId) + @(Get-CimInstance Win32_Process | Where-Object { $own -and $_.ParentProcessId -eq $own.ProcessId } | ForEach-Object ProcessId)
  if (-not $own -or -not ($busy | Where-Object { $ownPids -contains $_.OwningProcess })) { $problems += "Порт $Port занят другим процессом" }
}
# Базы городов и лимит соединений PostgreSQL — подключением с настройками API (.env)
$probe = Join-Path $env:TEMP 'tgid-multicity-probe.py'
@'
import asyncio, json, os, sys
import asyncpg
from dotenv import load_dotenv
load_dotenv(os.path.join(sys.argv[1], ".env"))
async def main():
    c = await asyncpg.connect(host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT") or 5432), user=os.getenv("DB_USER"),
                              password=os.getenv("DB_PASSWORD"), database="postgres", timeout=30)
    try:
        dbs = [r[0] for r in await c.fetch("select datname from pg_database")]
        limit = int(await c.fetchval("show max_connections"))
        used = int(await c.fetchval("select count(*) from pg_stat_activity"))
    finally:
        await c.close()
    print(json.dumps({"dbs": dbs, "max": limit, "used": used}))
asyncio.run(main())
'@ | Set-Content -Path $probe -Encoding UTF8
$r = Invoke-Native $py @($probe, $api) $api
Remove-Item $probe -ErrorAction SilentlyContinue
if ($r.Code -ne 0) { $problems += "Подключение к PostgreSQL не удалось: $($r.Out)" ; $db = $null }
else { $db = ($r.Out -split "`n" | Select-Object -Last 1) | ConvertFrom-Json }
$served = @()
if ($db) {
  foreach ($city in $cities) {
    if ($db.dbs -contains $city.Db) { $served += $city } else { Write-Host "  $($city.Code): базы $($city.Db) нет — общий API её не обслуживает" -ForegroundColor Yellow }
  }
  foreach ($city in $switch) { if (-not ($served | Where-Object { $_.Code -eq $city.Code })) { $problems += "Нет базы $($city.Db) города $($city.Code)" } }
  $need = $ApiWorkers * $served.Count * $poolMax
  Write-Host "PostgreSQL: соединений $($db.used) из $($db.max); общему API нужно до $need (+ воркеры)"
  if ($db.used + $need -gt $db.max) {
    Write-Host '  Внимание: при пиковой нагрузке соединений может не хватить — прежние службы городов после проверки можно остановить' -ForegroundColor Yellow
  }
}
$confText = [IO.File]::ReadAllText($citiesConf)
foreach ($city in $switch) { try { [void](Set-MapApi $confText $city $true) } catch { $problems += $_.Exception.Message } }
$t = Test-Nginx 'conf/nginx.conf'
if (-not $t.Ok) { $problems += "nginx -t не проходит уже сейчас:`n$($t.Out)" }
if ($problems) {
  Write-Host "`nНичего не изменено:" -ForegroundColor Red
  $problems | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  exit 1
}
Write-Host 'Предпроверки пройдены' -ForegroundColor Green

# --- 2. Службы ---
Step "2. Службы $apiService (:$Port) и $($workerNames -join ', ')"
$cityDbs = ($served | ForEach-Object { "$($_.Code)=$($_.Db)" }) -join ','
# Остальные переменные — из $api\.env (load_dotenv не перекрывает заданные здесь)
# API_PUBLIC_PREFIX — путь публикации за nginx: ссылки OGC API ведут на /tgid/<город>/map-api/…
$envVars = @('PYTHONUNBUFFERED=1', "TGID_CITY_DBS=$cityDbs", "DB_POOL_MIN_SIZE=$poolMin", "DB_POOL_MAX_SIZE=$poolMax",
  'API_PUBLIC_PREFIX=/tgid/{city}/map-api')
if (Test-Path $martinSql) { $envVars += "MARTIN_SQL_DIR=$martinSql" }
Install-TgidService $apiService $py "-m uvicorn main:app --host 127.0.0.1 --port $Port --workers $ApiWorkers" $envVars
$queues = ($served | ForEach-Object { "tgid.$($_.Code)" }) -join ','
$i = 0
foreach ($name in $workerNames) {
  $i++
  Install-TgidService $name $celery "-A worker.celery_app worker -P solo --loglevel=INFO -Q $queues --hostname tgid-multi-$i@%h" $envVars
}

# --- 3. Проверка ---
Step '3. Проверка общего API'
if (-not (Wait-Health "http://127.0.0.1:$Port/health")) { throw "$apiService не ответил на /health — см. $logs\$apiService.err.log (nginx не менялся)" }
$health = (Get-Text "http://127.0.0.1:$Port/health") | ConvertFrom-Json
foreach ($p in $health.database.cities.PSObject.Properties) {
  $color = if ($p.Value.ok) { 'Green' } else { 'Red' }
  Write-Host ("  {0}: база {1}" -f $p.Name, $(if ($p.Value.ok) { 'доступна' } else { "НЕДОСТУПНА — $($p.Value.error)" })) -ForegroundColor $color
}
$mismatch = @()
foreach ($city in $switch) {
  $new = Get-Text "http://127.0.0.1:$Port/city/$($city.Code)/fragments"
  $old = Get-Text "http://127.0.0.1:$($city.OldPort)/fragments"
  if ($null -eq $new) { $mismatch += "$($city.Code): общий API не отдал /fragments" }
  elseif ($null -ne $old -and $old -ne $new) { $mismatch += "$($city.Code): /fragments отличается от прежнего API" }
  else { Write-Host "  $($city.Code): фрагменты совпадают с прежним API" -ForegroundColor Green }
}
if ($mismatch) {
  $mismatch | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  throw "Общий API отвечает не так, как прежние — nginx не менялся. Службы $apiService можно остановить или пришлите журнал."
}

# --- 4. nginx ---
Step "4. nginx: map-api городов ($(($switch | ForEach-Object Code) -join ', ')) -> общий API"
$text = [IO.File]::ReadAllText($citiesConf)
foreach ($city in $switch) { $text = Set-MapApi $text $city $true }
if ($text -eq [IO.File]::ReadAllText($citiesConf)) { Write-Host 'tgid-cities.conf уже на общем API' }
else { Write-Conf $text 'map-api на общем API' }

Start-Sleep -Seconds 3
foreach ($city in $switch) {
  $u = "https://itwin.kz/tgid/$($city.Code)/map-api/health"
  $body = Get-Text $u 30
  if ($null -ne $body -and $body -notmatch '"cities"') { Write-Host "$u -> HTTP 200" -ForegroundColor Green }
  else { Write-Host "$u -> нет ответа города" -ForegroundColor Red }
}
Get-Service (@($apiService) + $workerNames) | Format-Table Name, Status, StartType
Write-Host "`nГотово: API городов идут через $apiService. Прежние службы tgid-api-*/tgid-worker-* работают — после" -ForegroundColor Green
Write-Host 'проверки их можно остановить. Откат: тот же скрипт с -Disable.' -ForegroundColor Green

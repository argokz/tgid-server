# Тайлы сети из PostGIS через martin вместо GeoServer — все города (фаза 1 модернизации).
# ЗАПУСКАТЬ ОТ АДМИНИСТРАТОРА после обновления кода API и веба (git pull, сборка веба):
#   powershell -ExecutionPolicy Bypass -File H:\deploy\tgid-server\itwin-api\scripts\martin\install-martin.ps1
#
# Шаги (повторный запуск безопасен):
#   1. martin.exe — в C:\tgid\martin (из -MartinZip, если exe ещё нет).
#   2. Функции тайлов tgid_mvt_<слой> в базе каждого города — из SQL-представлений GeoServer его рабочей
#      области (build_martin_functions.py --apply). Атрибуты и параметры — как у GeoServer.
#   3. Конфиг C:\tgid\martin\config.yaml (пароль базы — доступ только администраторам и SYSTEM).
#   4. Служба tgid-martin (NSSM), 127.0.0.1:3005, проверка /health.
#   5. nginx: /geoserver/tiles/ -> martin с той же проверкой входа, что у GeoServer (cookie tgid_gs);
#      в карту $tgid_gs_scope — источник тайла, чтобы «можно» для Алматы не открыло Астану. Бэкап, nginx -t.
#   6. Веб городов: MARTIN_TILES_URL / MARTIN_SOURCE_PREFIX / MARTIN_WORKSPACE, перезапуск служб веба.
#   7. API городов: MARTIN_SQL_FILE — API сам вернёт функции после переконвертации базы (city_schema);
#      подхватится при следующем перезапуске API (сейчас функции уже созданы шагом 2).
# Откат на GeoServer: -Disable (убирает MARTIN_* у служб веба и перезапускает их; martin и nginx не трогает).
param(
  [string]$MartinZip = '',
  [string[]]$Only = @(),
  [switch]$Disable,
  [switch]$SkipNginx
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$nssm = 'C:\nssm\win64\nssm.exe'
$api = 'H:\deploy\tgid-server\itwin-api'
$py = "$api\venv\Scripts\python.exe"
$martinDir = 'C:\tgid\martin'
$martinExe = "$martinDir\martin.exe"
$config = "$martinDir\config.yaml"
$listen = '127.0.0.1:3005'
$logs = 'H:\deploy\logs'
$gsWorkspaces = 'C:\ProgramData\GeoServer\workspaces'
$nginxDir = 'C:\nginx'
$publicTiles = 'https://itwin.kz/geoserver/tiles'

# Код города (префикс источников, как в API cities.py), база, рабочая область GeoServer, служба веба
$cities = @(
  @{ Code = 'almaty';     Db = 'almatygid';            Ws = 'AlmatyGIS';     Web = 'tgid-web';            Api = 'tgid-api' },
  @{ Code = 'astana';     Db = 'astanagid_2026_09_22'; Ws = 'AstanaGIS';     Web = 'tgid-web-astana';     Api = 'tgid-api-astana' },
  @{ Code = 'shatura';    Db = 'shatura';              Ws = 'ShaturaGIS';    Web = 'tgid-web-shatura';    Api = 'tgid-api-shatura' },
  @{ Code = 'taraz';      Db = 'tarazgid';             Ws = 'TarazGIS';      Web = 'tgid-web-taraz';      Api = 'tgid-api-taraz' },
  @{ Code = 'aktobe';     Db = 'aktobegid';            Ws = 'AktobeGIS';     Web = 'tgid-web-aktobe';     Api = 'tgid-api-aktobe' },
  @{ Code = 'shymkent';   Db = 'shymkentgid';          Ws = 'ShymkentGIS';   Web = 'tgid-web-shymkent';   Api = 'tgid-api-shymkent' },
  @{ Code = 'karaganda';  Db = 'karagandagid';         Ws = 'KaragandaGIS';  Web = 'tgid-web-karaganda';  Api = 'tgid-api-karaganda' },
  @{ Code = 'ekibastuz';  Db = 'ekibastuzgid';         Ws = 'EkibastuzGIS';  Web = 'tgid-web-ekibastuz';  Api = 'tgid-api-ekibastuz' },
  @{ Code = 'atbasar';    Db = 'atbasargid';           Ws = 'AtbasarGIS';    Web = 'tgid-web-atbasar';    Api = 'tgid-api-atbasar' },
  @{ Code = 'kokshetau';  Db = 'kokshetaugid';         Ws = 'KokshetauGIS';  Web = 'tgid-web-kokshetau';  Api = 'tgid-api-kokshetau' },
  @{ Code = 'shakhtinsk'; Db = 'shahtinskgid';         Ws = 'ShakhtinskGIS'; Web = 'tgid-web-shakhtinsk'; Api = 'tgid-api-shakhtinsk' },
  @{ Code = 'semey';      Db = 'semeygid';             Ws = 'SemeyGIS';      Web = 'tgid-web-semey';      Api = 'tgid-api-semey' }
)
if ($Only.Count) { $cities = @($cities | Where-Object { $Only -contains $_.Code }) }

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }

function Get-ServiceEnv($name) {
  $raw = & $nssm get $name AppEnvironmentExtra 2>$null
  if ($LASTEXITCODE -ne 0) { return $null }
  return @($raw | Where-Object { $_ -and $_.Trim() })
}

function Set-WebMartinEnv($city, [bool]$enable) {
  $svc = Get-Service $city.Web -ErrorAction SilentlyContinue
  if (-not $svc) { Write-Host "  $($city.Web): службы нет — пропуск" -ForegroundColor Yellow; return }
  $envList = Get-ServiceEnv $city.Web
  if ($null -eq $envList) { Write-Host "  $($city.Web): переменные NSSM не прочитаны — пропуск" -ForegroundColor Yellow; return }
  $kept = @($envList | Where-Object { $_ -notmatch '^MARTIN_(TILES_URL|SOURCE_PREFIX|WORKSPACE|LAYERS)=' })
  if ($enable) {
    $kept += "MARTIN_TILES_URL=$publicTiles"
    $kept += "MARTIN_SOURCE_PREFIX=$($city.Code)_"
    $kept += "MARTIN_WORKSPACE=$($city.Ws)"
  }
  & $nssm set $city.Web AppEnvironmentExtra @kept | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "nssm set $($city.Web) AppEnvironmentExtra" }
  Restart-Service $city.Web
  Write-Host ("  {0}: {1}, перезапущен" -f $city.Web, $(if ($enable) { 'тайлы сети из martin' } else { 'тайлы сети из GeoServer' }))
}

function Set-ApiMartinSql($city) {
  if (-not (Get-Service $city.Api -ErrorAction SilentlyContinue)) { Write-Host "  $($city.Api): службы нет — пропуск" -ForegroundColor Yellow; return }
  $envList = Get-ServiceEnv $city.Api
  if ($null -eq $envList) { Write-Host "  $($city.Api): переменные NSSM не прочитаны — пропуск" -ForegroundColor Yellow; return }
  $kept = @($envList | Where-Object { $_ -notmatch '^MARTIN_SQL_FILE=' }) + "MARTIN_SQL_FILE=$martinDir\sql\$($city.Code).sql"
  & $nssm set $city.Api AppEnvironmentExtra @kept | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "nssm set $($city.Api) AppEnvironmentExtra" }
  Write-Host "  $($city.Api): MARTIN_SQL_FILE задан (вступит в силу при следующем перезапуске API)"
}

if ($Disable) {
  Step 'Откат: веб городов берёт тайлы сети из GeoServer'
  foreach ($c in $cities) { Set-WebMartinEnv $c $false }
  exit 0
}

Step '1. Предпроверки'
$problems = @()
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { $problems += 'нужны права администратора' }
foreach ($p in @($nssm, $py, "$api\.env", "$api\scripts\martin\build_martin_functions.py")) { if (-not (Test-Path $p)) { $problems += "нет $p" } }
New-Item -ItemType Directory -Force $martinDir, "$martinDir\sql", $logs | Out-Null
if (-not (Test-Path $martinExe)) {
  if (-not $MartinZip) { $problems += "нет $martinExe — скачайте martin-x86_64-pc-windows-msvc.zip (стабильный выпуск, github.com/maplibre/martin/releases) и укажите -MartinZip" }
  elseif (-not (Test-Path $MartinZip)) { $problems += "нет $MartinZip" }
  else {
    Expand-Archive -Path $MartinZip -DestinationPath $martinDir -Force
    if (-not (Test-Path $martinExe)) { $problems += "в $MartinZip нет martin.exe" }
  }
}
if ($problems.Count) { $problems | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }; exit 1 }
Write-Host "  $(& $martinExe --version)"

Step '2. Функции тайлов в базах городов (из SQL-представлений GeoServer)'
$ready = @()
foreach ($c in $cities) {
  $wsDir = Join-Path $gsWorkspaces "$($c.Ws)\$($c.Ws)"
  if (-not (Test-Path $wsDir)) { Write-Host "  $($c.Code): нет рабочей области $wsDir — город пропущен" -ForegroundColor Yellow; continue }
  & $py "$api\scripts\martin\build_martin_functions.py" --workspace-dir $wsDir --db-name $c.Db --no-copy --apply --out "$martinDir\sql\$($c.Code).sql"
  if ($LASTEXITCODE -ne 0) { Write-Host "  $($c.Code): функции не созданы — город пропущен" -ForegroundColor Yellow; continue }
  $ready += $c
}
if (-not $ready.Count) { Write-Host 'Ни одного города — выход' -ForegroundColor Red; exit 1 }

Step '3. Конфиг martin'
$cityArgs = @(); foreach ($c in $ready) { $cityArgs += '--city'; $cityArgs += "$($c.Code)=$($c.Db)" }
& $py "$api\scripts\martin\build_martin_config.py" @cityArgs --listen $listen --env-file "$api\.env" --out $config
if ($LASTEXITCODE -ne 0) { throw 'build_martin_config.py' }
# в файле пароль базы: наследование прав снять, доступ — администраторам и SYSTEM
& icacls $config /inheritance:r /grant:r '*S-1-5-32-544:F' '*S-1-5-18:F' | Out-Null

Step '4. Служба tgid-martin'
$svcName = 'tgid-martin'
if (Get-Service $svcName -ErrorAction SilentlyContinue) { & $nssm stop $svcName | Out-Null }
else { & $nssm install $svcName $martinExe | Out-Null }
& $nssm set $svcName Application $martinExe | Out-Null
# город без функций (база переконвертирована и ещё не доведена API) — предупреждение, а не остановка всех городов
& $nssm set $svcName AppParameters "--config `"$config`" --on-invalid warn" | Out-Null
& $nssm set $svcName AppDirectory $martinDir | Out-Null
& $nssm set $svcName DisplayName 'TGID martin (тайлы сети из PostGIS)' | Out-Null
& $nssm set $svcName Start SERVICE_AUTO_START | Out-Null
& $nssm set $svcName AppStdout "$logs\$svcName.out.log" | Out-Null
& $nssm set $svcName AppStderr "$logs\$svcName.err.log" | Out-Null
& $nssm set $svcName AppRotateFiles 1 | Out-Null
& $nssm set $svcName AppRotateBytes 10485760 | Out-Null
& $nssm start $svcName | Out-Null
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
  Start-Sleep -Seconds 1
  try { $ok = (Invoke-WebRequest -UseBasicParsing "http://$listen/health" -TimeoutSec 3).StatusCode -eq 200 } catch { }
}
if (-not $ok) { Write-Host "martin не ответил — см. $logs\$svcName.err.log" -ForegroundColor Red; exit 1 }
$catalog = Invoke-RestMethod "http://$listen/catalog"
Write-Host "  martin работает, источников: $(@($catalog.tiles.PSObject.Properties).Count)"

if (-not $SkipNginx) {
  Step '5. nginx: /geoserver/tiles/ -> martin под проверкой входа'
  $conf = "$nginxDir\conf"
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $snippet = @"
# TGID: тайлы сети из martin (itwin-api scripts/martin) — под /geoserver/, чтобы действовала cookie сессии
# GeoServer tgid_gs (Path=/geoserver) и та же проверка входа и города (API /auth/check).
location ^~ /geoserver/tiles/ {
    auth_request /_tgid_gs_auth;
    proxy_pass http://$listen/;
    proxy_set_header Host `$host;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_read_timeout 60s;
    # адрес тайла меняется с версией данных (rev в viewparams) — браузеру можно держать его 5 минут
    add_header Cache-Control "private, max-age=300" always;
}
"@
  $files = @("$conf\nginx.conf", "$conf\tgid-auth-http.conf")
  foreach ($f in $files) { Copy-Item $f "$f.bak-martin-$stamp" -Force }
  [IO.File]::WriteAllText("$conf\tgid-martin.conf", $snippet, (New-Object Text.UTF8Encoding($false)))
  $main = [IO.File]::ReadAllText("$conf\nginx.conf")
  if ($main -notmatch 'include\s+(?:C:/nginx/conf/)?tgid-martin\.conf;') {
    $m = [regex]::Match($main, '(?m)^([ \t]*)include\s+(?:C:/nginx/conf/)?tgid-geoserver-auth\.conf;[ \t]*(?=\r?$)')
    if (-not $m.Success) { throw 'В nginx.conf нет include tgid-geoserver-auth.conf; — защита GeoServer не установлена' }
    $main = $main.Insert($m.Index + $m.Length, "`r`n$($m.Groups[1].Value)include C:/nginx/conf/tgid-martin.conf;")
    [IO.File]::WriteAllText("$conf\nginx.conf", $main, (New-Object Text.UTF8Encoding($false)))
  }
  $http = [IO.File]::ReadAllText("$conf\tgid-auth-http.conf")
  if ($http -notmatch 'geoserver/tiles/') {
    $m = [regex]::Match($http, '(?m)^([ \t]*)~\^/geoserver/\(\?<tgid_gs_ws>')
    if (-not $m.Success) { throw 'В tgid-auth-http.conf нет строки рабочей области в map $tgid_gs_scope' }
    $line = "$($m.Groups[1].Value)~^/geoserver/tiles/(?<tgid_gs_src>[^/?]+)                                       tiles:`$tgid_gs_src;`r`n"
    $http = $http.Insert($m.Index, $line)
    [IO.File]::WriteAllText("$conf\tgid-auth-http.conf", $http, (New-Object Text.UTF8Encoding($false)))
  }
  Push-Location $nginxDir
  $test = & .\nginx.exe -t 2>&1 | Out-String
  if ($test -notmatch 'test is successful') {
    foreach ($f in $files) { Copy-Item "$f.bak-martin-$stamp" $f -Force }
    Pop-Location
    Write-Host $test -ForegroundColor Red
    throw 'nginx -t не прошёл — файлы возвращены из бэкапа'
  }
  & .\nginx.exe -s reload
  Pop-Location
  Write-Host "  nginx перезагружен (бэкапы *.bak-martin-$stamp)"
}

Step '6. Веб городов: тайлы сети из martin'
foreach ($c in $ready) { Set-WebMartinEnv $c $true }

Step '7. API городов: функции тайлов возвращаются после переконвертации (MARTIN_SQL_FILE)'
foreach ($c in $ready) { Set-ApiMartinSql $c }

Write-Host "`nГотово. Проверка: войти в веб, открыть карту сети; в инструментах разработчика тайлы — $publicTiles/<город>_heatpipesections/..." -ForegroundColor Green
Write-Host "Откат на GeoServer: powershell -ExecutionPolicy Bypass -File $PSCommandPath -Disable"

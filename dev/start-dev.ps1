# Скрипт запуска окружения разработки TGID App (FastAPI + Celery + Nuxt 3)
param(
    [switch]$NoFrontend,
    [switch]$NoBackend,
    [switch]$NoCelery
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  TGID Web SaaS Development Environment Launcher          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Проверка Redis (нужен для Celery)
Write-Host "[1/4] Проверка доступности Redis (127.0.0.1:6379)..." -ForegroundColor Yellow
$redisCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $redisCheck) {
    Write-Host "  [ВНИМАНИЕ] Redis не отвечает на 127.0.0.1:6379." -ForegroundColor Red
    Write-Host "  Для работы гидравлических расчетов (Celery) запустите Redis:" -ForegroundColor DarkYellow
    Write-Host "  > docker run -d -p 6379:6379 --name tgid-redis redis:alpine" -ForegroundColor DarkYellow
} else {
    Write-Host "  [OK] Redis активен." -ForegroundColor Green
}

# 2. Запуск FastAPI Backend
if (-not $NoBackend) {
    Write-Host "[2/4] Запуск FastAPI (port 8011)..." -ForegroundColor Yellow
    $apiDir = "H:\projects\tgid-app\itwin-api\itwin-api"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$apiDir'; Write-Host 'Starting FastAPI on port 8011...' -ForegroundColor Cyan; python -m uvicorn main:app --host 0.0.0.0 --port 8011 --reload"
}

# 3. Запуск Celery Worker (с пулом solo для Windows)
if (-not $NoCelery) {
    Write-Host "[3/4] Запуск Celery Worker (Pool: solo)..." -ForegroundColor Yellow
    $apiDir = "H:\projects\tgid-app\itwin-api\itwin-api"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$apiDir'; Write-Host 'Starting Celery Worker for hydraulic calculation...' -ForegroundColor Magenta; celery -A worker.celery_app worker -l info -P solo"
}

# 4. Запуск Frontend Nuxt 3
if (-not $NoFrontend) {
    Write-Host "[4/4] Запуск Web-клиента Nuxt 3..." -ForegroundColor Yellow
    $webDir = "H:\projects\tgid-app\web-itwin"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$webDir'; Write-Host 'Starting Nuxt 3 Dev Server...' -ForegroundColor Green; npm run dev"
}

Write-Host "----------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Все сервисы запущены в отдельных окнах терминала." -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000 (или указанный порт Nuxt)" -ForegroundColor White
Write-Host "Swagger API Docs: http://localhost:8011/docs" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

# Script para levantar el servidor FastAPI en la red local
# Ejecutar como: .\start-server-local.ps1

Write-Host "🚀 Iniciando servidor FastAPI en red local..." -ForegroundColor Green
Write-Host ""

# Verificar que uv esté instalado
try {
    $uvVersion = uv --version 2>$null
    Write-Host "✅ uv encontrado: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: uv no está instalado o no está en el PATH" -ForegroundColor Red
    Write-Host "Por favor, instala uv siguiendo las instrucciones en INSTRUCCIONES_LOCAL.md" -ForegroundColor Yellow
    exit 1
}

# Obtener la IP local
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

if (-not $localIP) {
    Write-Host "⚠️  No se pudo detectar la IP local. Usando localhost..." -ForegroundColor Yellow
    $localIP = "localhost"
}

Write-Host "📍 IP Local: $localIP" -ForegroundColor Cyan
Write-Host "🌐 El servidor estará disponible en: http://${localIP}:8000" -ForegroundColor Cyan
Write-Host "📚 Documentación Swagger: http://${localIP}:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Verificar firewall
Write-Host "🔍 Verificando configuración del firewall..." -ForegroundColor Yellow
$firewallRule = Get-NetFirewallRule -DisplayName "FastAPI AnemiaIA" -ErrorAction SilentlyContinue

if (-not $firewallRule) {
    Write-Host "⚠️  Regla de firewall no encontrada." -ForegroundColor Yellow
    Write-Host "   Para permitir acceso desde otros dispositivos, ejecuta esto como Administrador:" -ForegroundColor Yellow
    Write-Host '   New-NetFirewallRule -DisplayName "FastAPI AnemiaIA" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow' -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "✅ Regla de firewall encontrada y activa" -ForegroundColor Green
    Write-Host ""
}

# Verificar archivo .env
if (-not (Test-Path .env)) {
    Write-Host "⚠️  Advertencia: No se encontró el archivo .env" -ForegroundColor Yellow
    Write-Host "   Copia .env.example a .env y configura tus credenciales:" -ForegroundColor Yellow
    Write-Host '   Copy-Item .env.example .env' -ForegroundColor White
    Write-Host ""
}

Write-Host "🎬 Iniciando servidor..." -ForegroundColor Green
Write-Host "   Presiona Ctrl+C para detener el servidor" -ForegroundColor Gray
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Iniciar el servidor
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

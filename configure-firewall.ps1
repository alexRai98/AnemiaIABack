# Script para configurar el firewall de Windows
# ⚠️ DEBE EJECUTARSE COMO ADMINISTRADOR ⚠️
# Click derecho → "Ejecutar con PowerShell como Administrador"

Write-Host "🔐 Configurando Firewall de Windows..." -ForegroundColor Cyan
Write-Host ""

# Verificar si se está ejecutando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Error: Este script debe ejecutarse como Administrador" -ForegroundColor Red
    Write-Host ""
    Write-Host "Cómo ejecutar como Administrador:" -ForegroundColor Yellow
    Write-Host "1. Click derecho en el archivo configure-firewall.ps1" -ForegroundColor White
    Write-Host "2. Selecciona 'Ejecutar con PowerShell como Administrador'" -ForegroundColor White
    Write-Host ""
    Write-Host "O desde PowerShell como Administrador:" -ForegroundColor Yellow
    Write-Host "   .\configure-firewall.ps1" -ForegroundColor White
    Write-Host ""
    Pause
    exit 1
}

# Verificar si la regla ya existe
$existingRule = Get-NetFirewallRule -DisplayName "FastAPI AnemiaIA" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "ℹ️  La regla de firewall ya existe." -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "¿Deseas eliminarla y recrearla? (S/N)"
    
    if ($response -eq "S" -or $response -eq "s") {
        Write-Host "🗑️  Eliminando regla existente..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName "FastAPI AnemiaIA"
        Write-Host "✅ Regla eliminada" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Manteniendo regla existente. Saliendo..." -ForegroundColor Cyan
        Pause
        exit 0
    }
}

Write-Host ""
Write-Host "➕ Creando regla de firewall..." -ForegroundColor Cyan

try {
    New-NetFirewallRule `
        -DisplayName "FastAPI AnemiaIA" `
        -Description "Permite acceso al servidor FastAPI AnemiaIA en el puerto 8000 para red local" `
        -Direction Inbound `
        -LocalPort 8000 `
        -Protocol TCP `
        -Action Allow `
        -Profile Private `
        -Enabled True
    
    Write-Host ""
    Write-Host "✅ ¡Regla de firewall creada exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalles de la configuración:" -ForegroundColor Cyan
    Write-Host "  • Nombre: FastAPI AnemiaIA" -ForegroundColor White
    Write-Host "  • Puerto: 8000" -ForegroundColor White
    Write-Host "  • Protocolo: TCP" -ForegroundColor White
    Write-Host "  • Dirección: Entrante (Inbound)" -ForegroundColor White
    Write-Host "  • Perfil: Privado (Red doméstica)" -ForegroundColor White
    Write-Host "  • Estado: Habilitado" -ForegroundColor White
    Write-Host ""
    Write-Host "🎉 Ahora otros dispositivos en tu red local pueden acceder al servidor" -ForegroundColor Green
    Write-Host ""
    
    # Mostrar la IP local
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress
    
    if ($localIP) {
        Write-Host "📍 Tu IP local: $localIP" -ForegroundColor Cyan
        Write-Host "🌐 URL del API: http://${localIP}:8000" -ForegroundColor Cyan
        Write-Host "📚 Documentación: http://${localIP}:8000/docs" -ForegroundColor Cyan
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error al crear la regla de firewall:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Próximo paso:" -ForegroundColor Yellow
Write-Host "   Ejecuta: .\start-server-local.ps1" -ForegroundColor White
Write-Host ""
Pause

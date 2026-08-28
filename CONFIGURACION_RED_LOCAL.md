# 🌐 Configuración para Acceso en Red Local

Esta guía te ayudará a exponer tu servicio FastAPI en tu red local para poder debuguearlo desde tu app móvil u otros dispositivos.

## 📍 Tu Configuración de Red

**IP Local de este PC:** `192.168.15.8`  
**Puerto del servidor:** `8000`  
**URL del API en red local:** `http://192.168.15.8:8000`

---

## 🚀 Paso 1: Levantar el Servidor en la Red Local

Ejecuta el siguiente comando para iniciar el servidor y hacerlo accesible en tu red:

```powershell
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### ¿Qué hace `--host 0.0.0.0`?
- `--host 0.0.0.0` hace que el servidor escuche en **todas las interfaces de red**, no solo en localhost
- Esto permite que otros dispositivos en tu red local puedan conectarse
- El parámetro `--reload` reinicia automáticamente el servidor cuando detecta cambios en el código (útil para debugging)

---

## 🔧 Paso 2: Configurar el Firewall de Windows

Para que otros dispositivos puedan acceder al servidor, necesitas permitir el puerto 8000 en el firewall:

### Opción A: Comando Rápido (Ejecutar como Administrador)

```powershell
New-NetFirewallRule -DisplayName "FastAPI AnemiaIA" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Opción B: Configuración Manual

1. Abre **Windows Defender Firewall con seguridad avanzada**
2. Ve a **Reglas de entrada** → **Nueva regla...**
3. Tipo de regla: **Puerto**
4. Protocolo: **TCP**, Puerto local específico: **8000**
5. Acción: **Permitir la conexión**
6. Perfil: Marca **Privado** (red doméstica)
7. Nombre: `FastAPI AnemiaIA Local`

---

## 📱 Paso 3: Conectar desde tu App

Una vez que el servidor esté corriendo, configura tu app para usar:

```
Base URL: http://192.168.15.8:8000
```

### Endpoints Disponibles:

- **Health Check**: `GET http://192.168.15.8:8000/health`
- **Documentación Interactiva**: `http://192.168.15.8:8000/docs`
- **API Endpoints**: Consulta la documentación en `/docs` para ver todos los endpoints disponibles

---

## 🔐 Paso 4: Configurar API Key

Tu app necesitará incluir la API Key en los headers de las peticiones:

```
X-API-Key: <tu-api-key-del-archivo-.env>
```

Asegúrate de que el archivo `.env` tenga configurado el `API_KEY`.

---

## ✅ Verificar la Conexión

### Desde tu PC (localhost):
```powershell
curl http://localhost:8000/health
```

### Desde otro dispositivo en la red:
```powershell
curl http://192.168.15.8:8000/health
```

O simplemente abre en el navegador de tu celular:
```
http://192.168.15.8:8000/docs
```

Deberías ver la documentación de Swagger UI.

---

## 🛡️ CORS (Cross-Origin Resource Sharing)

✅ **Ya configurado**: He agregado middleware CORS al archivo `api.py` para permitir que tu app móvil pueda hacer peticiones al servidor desde cualquier origen en tu red local.

La configuración actual permite:
- ✅ Todos los orígenes (`allow_origins=["*"]`)
- ✅ Todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
- ✅ Todos los headers
- ✅ Credenciales

### ⚠️ Nota de Seguridad
Esta configuración es adecuada para desarrollo local. **En producción**, deberías especificar solo los orígenes permitidos:

```python
allow_origins=[
    "https://tu-app.com",
    "https://www.tu-app.com",
]
```

---

## 🐛 Tips de Debugging

### 1. Ver logs en tiempo real
El servidor mostrará todos los logs en la terminal donde lo levantaste. Útil para ver:
- Peticiones entrantes
- Errores
- Datos procesados

### 2. Hot Reload
Con el flag `--reload`, el servidor se reinicia automáticamente cuando guardas cambios en el código.

### 3. Probar endpoints desde Swagger
Visita `http://192.168.15.8:8000/docs` desde cualquier dispositivo y prueba los endpoints directamente desde el navegador.

### 4. Ver la IP del cliente que hace peticiones
Verifica en los logs qué dispositivo está conectándose. Si ves peticiones desde IPs tipo `192.168.15.x`, significa que los dispositivos de tu red pueden conectarse correctamente.

---

## 🔍 Troubleshooting

### No puedo conectarme desde mi celular

1. **Verifica que ambos dispositivos estén en la misma red WiFi**
   ```powershell
   ipconfig
   ```
   Busca tu IP en la sección de tu adaptador WiFi/Ethernet activo

2. **Verifica que el servidor esté corriendo**
   ```powershell
   netstat -an | Select-String "8000"
   ```
   Deberías ver `0.0.0.0:8000` o `[::]:8000` en LISTENING

3. **Prueba hacer ping desde tu celular a tu PC**
   - Instala una app como "Network Analyzer" en tu celular
   - Haz ping a `192.168.15.8`
   - Si no responde, puede ser un problema de firewall

4. **Verifica el firewall**
   ```powershell
   Get-NetFirewallRule -DisplayName "FastAPI AnemiaIA" | Select-Object DisplayName, Enabled, Direction, Action
   ```

### El servidor se cae o da error

- Verifica que el archivo `.env` esté correctamente configurado
- Revisa que la base de datos PostgreSQL esté corriendo (si la necesitas)
- Revisa los logs en la terminal para ver el error específico

### Cambió mi IP local

Las IPs locales pueden cambiar si tu router usa DHCP dinámico. Para fijar tu IP:

1. Ve a la configuración de tu router (usualmente `192.168.1.1` o `192.168.0.1`)
2. Busca "DHCP Reservation" o "Reserva de IP"
3. Reserva la IP `192.168.15.8` para la MAC address de tu PC

O desde Windows:
```powershell
# Ver tu MAC address actual
Get-NetAdapter | Select-Object Name, MacAddress
```

---

## 🚪 Detener el Servidor

Presiona `Ctrl+C` en la terminal donde está corriendo el servidor.

---

## 📝 Comando Completo de Referencia

```powershell
# Desde el directorio del proyecto
cd c:\Users\Cliente\Documents\Apps\AnemiaIABack\AnemiaIABack

# Levantar el servidor en la red local
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌟 Resumen para tu App

Configura estos valores en tu app:

| Variable | Valor |
|----------|-------|
| Base URL | `http://192.168.15.8:8000` |
| API Key Header | `X-API-Key` |
| API Key Value | (el valor de `API_KEY` en tu `.env`) |

---

¡Listo! Ahora tu API estará accesible desde cualquier dispositivo conectado a tu red WiFi doméstica. 🎉

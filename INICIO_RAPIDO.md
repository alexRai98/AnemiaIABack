# ⚡ Inicio Rápido

## 🎯 Para Desarrollo Local en Este PC

```powershell
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Accede en: http://localhost:8000/docs

---

## 🌐 Para Acceso desde tu App Móvil en la Red Local

### Primera vez (configurar firewall):

1. **Abrir PowerShell como Administrador**
2. **Ejecutar**:
   ```powershell
   cd C:\Users\Cliente\Documents\Apps\AnemiaIABack\AnemiaIABack
   .\configure-firewall.ps1
   ```

### Cada vez que quieras iniciar el servidor:

```powershell
.\start-server-local.ps1
```

### Configuración en tu App:

```
Base URL: http://192.168.15.8:8000
Header: X-API-Key: <tu-api-key>
```

---

## 📚 Documentación Completa

- **Instalación de dependencias**: [INSTRUCCIONES_LOCAL.md](./INSTRUCCIONES_LOCAL.md)
- **Configuración de red local**: [CONFIGURACION_RED_LOCAL.md](./CONFIGURACION_RED_LOCAL.md)
- **Documentación del proyecto**: [README.md](./README.md)

---

## 🔑 Recordatorio

Antes de iniciar el servidor, asegúrate de:
1. ✅ Tener el archivo `.env` configurado con tus credenciales
2. ✅ Tener PostgreSQL corriendo (si lo usas localmente)
3. ✅ Tener configurado el bucket S3/Supabase

---

## 🆘 Problemas Comunes

### "uv no se reconoce como comando"
```powershell
# Actualiza el PATH de la sesión actual
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
```

### "No puedo conectarme desde mi celular"
1. Verifica que ambos estén en la misma red WiFi
2. Ejecuta `.\configure-firewall.ps1` como Administrador
3. Verifica que el servidor esté usando `--host 0.0.0.0`

### "Error de API Key"
Verifica que tu app envíe el header:
```
X-API-Key: <el-valor-de-API_KEY-en-tu-.env>
```

---

## 🛑 Detener el Servidor

Presiona `Ctrl+C` en la terminal donde está corriendo.

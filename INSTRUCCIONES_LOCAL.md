# Instrucciones para Levantar el Servidor Localmente

## 🌐 Acceso en Red Local

**¿Quieres que tu app móvil se conecte al servidor?** Lee la guía completa: **[CONFIGURACION_RED_LOCAL.md](./CONFIGURACION_RED_LOCAL.md)**

### Inicio Rápido en Red Local:

1. **Configura el firewall** (ejecutar como Administrador):
   ```powershell
   .\configure-firewall.ps1
   ```

2. **Inicia el servidor**:
   ```powershell
   .\start-server-local.ps1
   ```

3. **Conecta tu app a**: `http://192.168.15.8:8000`

---

## ✅ Dependencias Instaladas

Todas las dependencias ya están instaladas correctamente usando `uv`. El entorno virtual está en `.venv/`.

### Paquetes Instalados:
- FastAPI 0.141.1
- Uvicorn 0.52.4
- SQLAlchemy 2.0.52
- psycopg 3.3.4
- boto3 1.43.82
- opencv-python-headless 4.14.0.94
- numpy 2.5.2
- Y todas las demás dependencias del proyecto

## 🚀 Cómo Levantar el Servidor

### Opción 1: Usando `uv run` (Recomendado)

```powershell
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Opción 2: Activando el entorno virtual primero

```powershell
# Activar el entorno virtual
.\.venv\Scripts\Activate.ps1

# Levantar el servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📝 Configuración Requerida

Antes de levantar el servidor, asegúrate de que el archivo `.env` esté configurado correctamente con:

- `API_KEY`: Clave API para autenticación
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Configuración de PostgreSQL
- `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`: Configuración de S3/Supabase Storage

Puedes copiar `.env.example` a `.env` si aún no lo has hecho:

```powershell
Copy-Item .env.example .env
```

Luego edita `.env` con tus credenciales reales.

## 🔍 Verificar la Instalación

Para verificar que todo está correctamente instalado:

```powershell
# Ver la versión de uv
uv --version

# Listar paquetes instalados
uv pip list

# Ver información de Python
uv run python --version
```

## 🌐 Acceder al Servidor

Una vez levantado, el servidor estará disponible en:
- API: http://localhost:8000
- Documentación interactiva (Swagger): http://localhost:8000/docs
- Documentación alternativa (ReDoc): http://localhost:8000/redoc

## 🛑 Detener el Servidor

Presiona `Ctrl+C` en la terminal donde está corriendo el servidor.

## 🔧 Comandos Útiles

```powershell
# Actualizar dependencias
uv sync

# Agregar una nueva dependencia
uv add nombre-paquete

# Ejecutar tests (si están configurados)
uv run pytest

# Entrar al shell de Python con el entorno activado
uv run python
```

## ⚠️ Notas Importantes

- Este proyecto usa Python 3.12
- `uv` maneja automáticamente el entorno virtual y las dependencias
- Si tienes problemas con la política de ejecución de scripts en PowerShell, ejecuta:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

# 📋 Resumen de Archivos del Proyecto

## 🔧 Archivos de Configuración Principales

- **`.env`** - Variables de entorno (credenciales BD, S3, API Key)
- **`.env.example`** - Plantilla de variables de entorno
- **`pyproject.toml`** - Configuración del proyecto Python y dependencias
- **`uv.lock`** - Lock file de dependencias
- **`main.py`** - Punto de entrada de la aplicación

## 📚 Documentación

- **`README.md`** - Documentación principal del proyecto
- **`INSTRUCCIONES_LOCAL.md`** - Cómo instalar dependencias y levantar el servidor
- **`CONFIGURACION_RED_LOCAL.md`** - Cómo exponer el servicio en red local
- **`INICIO_RAPIDO.md`** - Comandos rápidos de referencia

## 🚀 Scripts de Utilidad

- **`start-server-local.ps1`** - Script para iniciar el servidor en red local
- **`configure-firewall.ps1`** - Script para configurar el firewall de Windows

## 🐳 Docker & Deploy

- **`Dockerfile`** - Configuración de Docker
- **`cloudbuild.yaml`** - Configuración de Cloud Build
- **`.dockerignore`** - Archivos ignorados por Docker

## 📁 Directorios Principales

- **`src/`** - Código fuente de la aplicación
- **`tests/`** - Tests del proyecto
- **`local_bucket/`** - Bucket local para desarrollo (contiene solo .gitkeep)
- **`.venv/`** - Entorno virtual de Python
- **`.git/`** - Repositorio Git

## 🗑️ Archivos de Testing Eliminados

- ❌ test-api.ps1
- ❌ test-capture-simple.ps1
- ❌ test_capture.py
- ❌ test_with_debug_image.py
- ❌ create_test_image.py
- ❌ test-eye-image.jpg
- ❌ a-test-01.png
- ❌ debug_*.jpg
- ❌ RESULTADO_PRUEBA.md
- ❌ RESULTADO_FINAL_EXITOSO.md
- ❌ ESTADO_SERVIDOR.txt
- ❌ COMO_PROBAR_CON_IMAGEN.md
- ❌ Imágenes de prueba en local_bucket/

## ✅ Estado Actual

El proyecto está limpio y listo para producción con:
- ✅ Código fuente optimizado
- ✅ Documentación completa
- ✅ Scripts de utilidad funcionales
- ✅ Configuración de red local
- ✅ Sin archivos de testing temporales

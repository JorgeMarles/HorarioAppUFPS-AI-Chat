# Gemini Chat Backend (FastAPI)

Backend ligero para gestionar sesiones de chat con el modelo Gemini usando la librería oficial `google-generativeai`.

## Tecnologías
- Python 3.11+
- FastAPI
- Uvicorn
- google-generativeai (SDK oficial de Gemini)
- Pydantic
- python-dotenv

## Endpoints
| Método | Path | Descripción |
|--------|------|-------------|
| POST | /chat/session | Crea una nueva sesión y retorna `session_id` |
| GET | /chat/sessions | Lista las sesiones activas |
| POST | /chat/message | Envía un mensaje y retorna respuesta completa |
| POST | /chat/stream | Devuelve respuesta en streaming vía Server-Sent Events (SSE) |
| GET | /health | Chequeo básico de salud |

## Instalación

```powershell
# En Windows PowerShell (desde la carpeta ai-assistant)
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuración
Crea un archivo `.env` en la raíz (`ai-assistant/.env`):
```env
GEMINI_API_KEY=tu_api_key_real
MODEL_NAME=gemini-1.5-flash
```
(O puedes copiar desde `.env.example`).

## Ejecutar el servidor

```powershell
uvicorn app.main:app --reload --port 8000
```

## Flujo de uso
1. Crear sesión:
   ```bash
   curl -X POST http://localhost:8000/chat/session
   ```
   Respuesta:
   ```json
   { "session_id": "<uuid>" }
   ```
2. Enviar mensaje:
   ```bash
   curl -X POST http://localhost:8000/chat/message \
     -H "Content-Type: application/json" \
     -d '{"session_id":"<uuid>","message":"Hola Gemini"}'
   ```
3. Streaming (SSE) desde terminal usando curl:
   ```bash
   curl -N -X POST http://localhost:8000/chat/stream \
     -H "Content-Type: application/json" \
     -d '{"session_id":"<uuid>","message":"Explica FastAPI"}'
   ```
   Verás eventos `data:` sucesivos.

## Notas
- Historial se mantiene en memoria. Para producción, usar Redis o base de datos.
- Si cambias el modelo, ajusta `MODEL_NAME` en `.env`.
- El streaming agrega el mensaje completo al historial una vez finalizado.

## Extensiones futuras sugeridas
- Persistencia de sesiones (Redis / Postgres)
- Autenticación JWT para controlar acceso
- Límite de tokens por sesión y conteo de uso
- Borrado de sesiones inactivas mediante tarea periódica

## Licencia
Uso interno del proyecto.

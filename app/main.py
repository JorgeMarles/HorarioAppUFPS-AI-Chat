from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .service.chat_service import chat_service
from .models import (
    CreateSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    ListSessionsResponse,
)
import warnings
from app.config import get_settings
import json


warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*pydantic.*")

app = FastAPI(title="Gemini Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_jwt_token(request: Request) -> str:
    """Dependency para extraer y verificar JWT token"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="Token de autorización requerido")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido. Use: Bearer <token>")
    
    return auth_header[7:]

@app.post("/chat/session", response_model=CreateSessionResponse)
def create_session(payload: CreateSessionResponse, token: str = Depends(get_jwt_token)):
    try:
        sid = chat_service.create_session(payload.session_id)
        return CreateSessionResponse(session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions", response_model=ListSessionsResponse)
def list_sessions():
    return ListSessionsResponse(sessions=chat_service.list_sessions())

@app.post("/chat/message", response_model=SendMessageResponse)
def send_message(payload: SendMessageRequest, token: str = Depends(get_jwt_token)):
    if not get_settings().chat_active:
        raise HTTPException(status_code=503, detail='Actualmente el chatbot no está activo, por favor inténtalo después')

    try:
        
        reply = chat_service.send_message(payload.session_id, payload.message)
        return SendMessageResponse(session_id=payload.session_id, reply=reply)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
def stream_message(payload: SendMessageRequest, token: str = Depends(get_jwt_token)):
    """Endpoint para streaming con SSE"""
    try:
        # Verificar que la sesión existe o crearla

        if not get_settings().chat_active:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Actualmente el chatbot no está activo, por favor inténtalo después'})}\n\n"

        sessions = chat_service.list_sessions()
        if payload.session_id not in sessions:
            chat_service.create_session(payload.session_id)

        def event_generator():
            try:
                for chunk in chat_service.send_message_stream(payload.session_id, payload.message, token):
                    yield chunk
            except Exception as e:
                yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

        return StreamingResponse(
            event_generator(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
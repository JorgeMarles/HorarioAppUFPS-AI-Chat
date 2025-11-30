from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from .chat_service import chat_service
from .models import (
    CreateSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    ListSessionsResponse,
)

app = FastAPI(title="Gemini Chat API", version="1.0.0")

@app.post("/chat/session", response_model=CreateSessionResponse)
def create_session():
    try:
        sid = chat_service.create_session()
        return CreateSessionResponse(session_id=sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions", response_model=ListSessionsResponse)
def list_sessions():
    return ListSessionsResponse(sessions=chat_service.list_sessions())

@app.post("/chat/message", response_model=SendMessageResponse)
def send_message(payload: SendMessageRequest):
    if payload.session_id not in chat_service.list_sessions():
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    try:
        reply = chat_service.send_message(payload.session_id, payload.message)
        return SendMessageResponse(session_id=payload.session_id, reply=reply)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
def stream_message(payload: SendMessageRequest):
    if payload.session_id not in chat_service.list_sessions():
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    def event_generator():
        try:
            for chunk in chat_service.stream_message(payload.session_id, payload.message):
                # SSE format: data: <content>\n\n
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health")
def health():
    return {"status": "ok"}

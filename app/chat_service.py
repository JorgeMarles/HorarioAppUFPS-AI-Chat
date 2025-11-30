import google.generativeai as genai
import uuid
from typing import Dict, List, Any
from .config import get_settings

# Simple in-memory session store
_sessions: Dict[str, Dict[str, Any]] = {}

class ChatService:
    def __init__(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.model_name

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            "history": []  # list of {role: user|model, content: str}
        }
        return session_id

    def list_sessions(self) -> List[str]:
        return list(_sessions.keys())

    def _build_history(self, session_id: str) -> List[Dict[str, str]]:
        session = _sessions.get(session_id)
        if not session:
            raise KeyError("Sesión no encontrada")
        return session["history"]

    def send_message(self, session_id: str, message: str) -> str:
        history = self._build_history(session_id)
        # Build chat object each time with existing history
        chat = genai.GenerativeModel(self.model_name).start_chat(history=history)
        response = chat.send_message(message)
        # Gemini returns candidates; we pick the first text part
        text = response.text or ""
        # Append user and model messages to history
        history.append({"role": "user", "content": message})
        history.append({"role": "model", "content": text})
        return text

    def stream_message(self, session_id: str, message: str):
        history = self._build_history(session_id)
        chat = genai.GenerativeModel(self.model_name).start_chat(history=history)
        stream = chat.send_message(message, stream=True)
        accumulated = []
        for chunk in stream:
            part_text = getattr(chunk, 'text', '') or ''
            if part_text:
                accumulated.append(part_text)
                yield part_text
        # Update history after streaming completes
        full_text = ''.join(accumulated)
        history.append({"role": "user", "content": message})
        history.append({"role": "model", "content": full_text})

chat_service = ChatService()

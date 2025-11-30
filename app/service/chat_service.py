import google.genai as genai
from typing import List
from app.config import get_settings
from google.genai import types
from .redis_service import redis_service
import os

def get_prompt():
    # Obtener la ruta del directorio donde está este archivo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))  # Sube 2 niveles: service -> app -> ai-assistant
    prompt_path = os.path.join(root_dir, 'prompt.txt')
    
    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()

class ChatService:
    def __init__(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        self.model_name = settings.model_name
        self.client = genai.Client(api_key=settings.gemini_api_key)


    def create_session(self, session_id: int) -> int:        
        # Crear historial vacío en Redis
        redis_service.set_chat_history(session_id, [])
        redis_service.add_session(session_id)
        
        return session_id

    def list_sessions(self) -> List[int]:
        return [int(x) for x in redis_service.get_sessions()]

    def _get_chat_from_history(self, session_id: int):
        """Crear objeto chat desde el historial guardado"""
        history = redis_service.get_chat_history(session_id)
        if history is None:
            self.create_session(session_id)
            history = redis_service.get_chat_history(session_id)
        
        # Adaptar historial al formato de google.genai
        gemini_history = []
        for msg in history:
            gemini_history.append({
                "role": msg["role"],
                "parts": [msg["content"]]
            })

        # Crear el chat con system_instruction y el historial previo (sin tools)
        chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=get_prompt()
            ),
            history=gemini_history
        )

        return chat, history

    def _save_history(self, session_id: int, history: List):
        """Guardar historial actualizado"""
        redis_service.set_chat_history(session_id, history)

    def send_message(self, session_id: int, message: str) -> str:
        chat, history = self._get_chat_from_history(session_id)
        
        # Enviar mensaje
        response = chat.send_message(message)
        response_text = response.text or ""
        
        # Actualizar historial
        history.append({"role": "user", "content": message})
        history.append({"role": "model", "content": response_text})
        
        # Guardar historial actualizado
        self._save_history(session_id, history)
        
        return response_text

    def stream_message(self, session_id: int, message: str):
        chat, history = self._get_chat_from_history(session_id)
        
        # Stream del mensaje
        stream = chat.send_message(message, stream=True)
        
        chunk_count = 0
        accumulated_response = []
        
        for chunk in stream:
            part_text = getattr(chunk, 'text', '') or ''
            if part_text:
                chunk_count += 1
                accumulated_response.append(part_text)
                yield part_text
        
        # Guardar historial después del stream completo
        full_response = ''.join(accumulated_response)
        history.append({"role": "user", "content": message})
        history.append({"role": "model", "content": full_response})
        
        self._save_history(session_id, history)
        print(f"Stream completado. Total chunks: {chunk_count}")

    def delete_session(self, session_id: int):
        """Eliminar una sesión"""
        redis_service.delete_session(session_id)

chat_service = ChatService()
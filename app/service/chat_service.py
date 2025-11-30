from typing import List, Generator
from .redis_service import redis_service
from .chat import Chat
import json

class ChatService:
    def __init__(self):
        pass

    def create_session(self, session_id: int) -> int:
        # Crear historial vacío en Redis
        redis_service.set_chat_history(session_id, [])
        redis_service.add_session(session_id)

        return session_id

    def list_sessions(self) -> List[int]:
        return [int(x) for x in redis_service.get_sessions()]

    def _serialize_message_content(self, content):
        """Convert Gemini Content objects to simple text"""
        if hasattr(content, 'text'):
            return content.text
        elif hasattr(content, 'parts') and content.parts:
            # Extract text from parts
            text_parts = []
            for part in content.parts:
                if hasattr(part, 'text'):
                    text_parts.append(part.text)
            return ''.join(text_parts)
        elif isinstance(content, str):
            return content
        else:
            return str(content)

    def _get_chat_from_history(self, session_id: int):
        """Crear objeto chat desde el historial guardado"""
        history = redis_service.get_chat_history(session_id)
        if history is None:
            self.create_session(session_id)
            history = redis_service.get_chat_history(session_id)

        chat = Chat(history)

        return chat, history

    def _save_history(self, session_id: int, history: List):
        """Guardar historial actualizado"""
        redis_service.set_chat_history(session_id, history)

    def send_message(self, session_id: int, message: str) -> str:
        chat, history = self._get_chat_from_history(session_id)

        # Enviar mensaje
        response_text = chat.send_message(message)

        # Serialize content properly before storing
        user_content = self._serialize_message_content(message)
        model_content = self._serialize_message_content(response_text)

        # Actualizar historial
        history.append({"role": "user", "content": user_content})
        history.append({"role": "model", "content": model_content})

        # Guardar historial actualizado
        self._save_history(session_id, history)

        return response_text
    
    def send_message_stream(self, session_id: int, message: str, jwt: str) -> Generator[str, None, None]:
        """Envía mensaje con streaming de eventos"""
        chat, history = self._get_chat_from_history(session_id)
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Procesando mensaje...'})}\n\n"

        context = {
            "jwt": jwt,
            "schedule_id": session_id
        }

        try:
            # Enviar mensaje y obtener respuesta con streaming
            for event in chat.send_message_stream(message, context):
                yield f"data: {json.dumps(event)}\n\n"
            
            # Actualizar historial al final
            user_content = self._serialize_message_content(message)
            model_content = chat.get_last_response()
            
            history.append({"role": "user", "content": user_content})
            history.append({"role": "model", "content": model_content})
            
            self._save_history(session_id, history)
            
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Conversación guardada'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    def delete_session(self, session_id: int):
        """Eliminar una sesión"""
        redis_service.delete_session(session_id)


chat_service = ChatService()
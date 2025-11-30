import redis
import json
from typing import Optional, List, Dict
from app.config import get_settings

class RedisService:
    def __init__(self):
        settings = get_settings()
        self.client = redis.from_url(settings.redis_url, decode_responses=True)  # decode_responses=True
    
    def set_chat_history(self, session_id: int, history: List[Dict], expire_hours: int = 24):
        """Guardar historial del chat como JSON"""
        history_json = json.dumps(history)
        self.client.set(f"chat:{session_id}", history_json, ex=expire_hours * 3600)
    
    def get_chat_history(self, session_id: int) -> Optional[List[Dict]]:
        """Recuperar historial del chat"""
        history_json = self.client.get(f"chat:{session_id}")
        if not history_json:
            return None
        return json.loads(history_json)
    
    def add_session(self, session_id: int, expire_hours: int = 24):
        """Agregar sesión a la lista"""
        self.client.sadd("chat:sessions", session_id)
        # Crear meta para TTL
        self.client.set(f"session:meta:{session_id}", "active", ex=expire_hours * 3600)
    
    def get_sessions(self) -> list[str]:
        """Obtener todas las sesiones activas"""
        all_sessions = self.client.smembers("chat:sessions")
        active_sessions = []
        
        for session in all_sessions:
            # Verificar si la sesión sigue activa
            if self.client.exists(f"session:meta:{session}"):
                active_sessions.append(session)
            else:
                # Limpiar sesión expirada
                self.client.srem("chat:sessions", session)
        
        return active_sessions
    
    def delete_session(self, session_id: int):
        """Eliminar sesión"""
        self.client.delete(f"chat:{session_id}")
        self.client.delete(f"session:meta:{session_id}")
        self.client.srem("chat:sessions", session_id)
    
    def session_exists(self, session_id: int) -> bool:
        """Verificar si existe una sesión"""
        return (self.client.exists(f"chat:{session_id}") > 0 and 
                self.client.exists(f"session:meta:{session_id}") > 0)

redis_service = RedisService()
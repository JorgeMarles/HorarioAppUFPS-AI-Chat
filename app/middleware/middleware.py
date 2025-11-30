from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

class JWTPassthroughMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        # Rutas que no requieren JWT
        self.excluded_paths = excluded_paths or [
            "/health", 
            "/docs", 
            "/openapi.json",
            "/redoc",
            "/chat/sessions"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Verificar si la ruta está excluida
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extraer JWT del header Authorization
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token de autorización requerido")
        
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Formato de token inválido. Use: Bearer <token>")
        
        # Extraer solo el token sin "Bearer "
        jwt_token = auth_header[7:]
        
        # Agregar el token al estado de la request para usarlo después
        request.state.jwt_token = jwt_token
        request.state.auth_header = auth_header
        
        # Continuar con el request
        response = await call_next(request)
        return response
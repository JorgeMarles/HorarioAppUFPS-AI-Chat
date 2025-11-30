from pydantic import BaseModel, Field
from typing import List

class CreateSessionResponse(BaseModel):
    session_id: int = Field(..., description="ID único de la sesión")

class SendMessageRequest(BaseModel):
    session_id: int
    message: str

class SendMessageResponse(BaseModel):
    session_id: int
    reply: str

class ListSessionsResponse(BaseModel):
    sessions: List[int]

class ErrorResponse(BaseModel):
    detail: str

from pydantic import BaseModel, Field
from typing import List

class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., description="ID único de la sesión")

class SendMessageRequest(BaseModel):
    session_id: str
    message: str

class SendMessageResponse(BaseModel):
    session_id: str
    reply: str

class ListSessionsResponse(BaseModel):
    sessions: List[str]

class ErrorResponse(BaseModel):
    detail: str

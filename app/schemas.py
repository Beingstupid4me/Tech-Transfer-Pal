# app/schemas.py
from pydantic import BaseModel
from typing import List

class ChatHistoryItem(BaseModel):
    """Defines the structure for a single message in the history."""
    role: str  # Should be 'user' or 'model'
    parts: List[str]

class ChatRequest(BaseModel):
    """Defines the structure for an incoming chat request from the frontend."""
    message: str
    history: List[ChatHistoryItem] = []
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: List[dict] = Field(default_factory=list, max_length=20)


@router.post("")
def chat(body: ChatIn, user: dict = Depends(current_user)):
    # Step 6: connect Groq / Gemini here (free tiers). The frontend shows this message in the chat.
    raise HTTPException(status_code=503, detail="The AI chat is not connected yet.")

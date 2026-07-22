from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.chat.dto.chat_dto import CreateChatDTO
from .chat_service import create_chat, get_chats_by_session

router = APIRouter(
  prefix="/chat",
  tags=["chat"]
)

@router.post("/")
async def create_chat_endpoint(body: CreateChatDTO, db: Session = Depends(get_db)):
  result = create_chat(db, body)
  if result:
    return {
      "success": True, 
      "message": "Chat created successfully", 
      "data": {
        "id": result.id, 
        "session_id": result.session_id,
        "content": result.content,
        "weather_json": result.weather_json,
        "created_at": result.created_at
      }
    }
  return {"success": False, "message": "Failed to create chat", "data": None}

@router.get("/{session_id}")
async def get_chats_endpoint(session_id: int, db: Session = Depends(get_db)):
  chats = get_chats_by_session(db, session_id)
  return {
    "success": True,
    "message": "Chats retrieved successfully",
    "data": [
      {
        "id": chat.id,
        "session_id": chat.session_id,
        "sender": getattr(chat, "sender", None),
        "content": chat.content,
        "weather_json": getattr(chat, "weather_json", None),
        "created_at": chat.created_at
      }
      for chat in chats
    ]
  }

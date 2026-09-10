from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.chat.dto.chat_dto import CreateChatDTO
from src.auth.auth_middleware import get_current_user
from src.auth.auth_model import UserModel
from .chat_service import create_chat, get_chats_by_session

router = APIRouter(
  prefix="/chat",
  tags=["chat"],
  dependencies=[Depends(get_current_user)]
)

@router.post("")
@router.post("/")
async def create_chat_endpoint(
    body: CreateChatDTO, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  result = create_chat(db, body, current_user)
  if result:
    return {
      "status": True, 
      "data": {
        "id": result.id, 
        "session_id": result.session_id,
        "content": result.content,
        "weather_json": result.weather_json,
        "created_at": result.created_at
      }
    }
  return {"status": False, "data": None, "error": "Failed to create chat"}

@router.get("/{session_id}")
async def get_chats_endpoint(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  chats = get_chats_by_session(db, session_id)
  return {
    "status": True,
    "data": [
      {
        "id": chat.id,
        "session_id": chat.session_id,
        "role": getattr(chat, "sender", None),
        "content": chat.content,
        "weather_json": getattr(chat, "weather_json", None),
        "created_at": chat.created_at
      }
      for chat in chats
    ]
  }

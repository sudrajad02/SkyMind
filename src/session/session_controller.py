from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.session.dto.session_dto import CreateSessionDTO
from .session_service import create_session

router = APIRouter(
  prefix="/session",
  tags=["session"]
)

@router.post("/")
async def create_session_endpoint(body: CreateSessionDTO, db: Session = Depends(get_db)):
  result = create_session(db, body)
  if result:
    return {
      "success": True, 
      "message": "Session created successfully", 
      "data": {
        "id": result.id, 
        "title": result.title,
        "created_at": result.created_at, 
        "updated_at": result.updated_at
      }
    }
  return {"success": False, "message": "Failed to create session", "data": None}

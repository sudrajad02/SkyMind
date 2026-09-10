from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.session.dto.session_dto import CreateSessionDTO
from src.auth.auth_middleware import get_current_user
from src.auth.auth_model import UserModel
from .session_service import create_session

router = APIRouter(
  prefix="/session",
  tags=["session"],
  dependencies=[Depends(get_current_user)]
)

@router.post("")
@router.post("/")
async def create_session_endpoint(
    body: CreateSessionDTO, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  result = create_session(db, body)
  if result:
    return {
      "status": True, 
      "data": {
        "id": result.id, 
        "title": result.title,
        "created_at": result.created_at, 
        "updated_at": result.updated_at
      }
    }
  return {"status": False, "data": None, "error": "Failed to create session"}

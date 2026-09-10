from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.session.dto.session_dto import CreateSessionDTO
from src.auth.auth_middleware import get_current_user
from src.auth.auth_model import UserModel
from .session_service import (
  create_session, 
  get_sessions_by_user, 
  get_session_by_id, 
  delete_session
)

router = APIRouter(
  prefix="/session",
  tags=["session"],
  dependencies=[Depends(get_current_user)]
)

@router.get("/")
async def get_user_sessions_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  """
  Mengambil semua session obrolan milik user yang sedang login (berdasarkan token JWT).
  """
  sessions = get_sessions_by_user(db, current_user.id)
  return {
    "status": True,
    "data": [
      {
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at,
      }
      for s in sessions
    ]
  }

@router.post("/")
async def create_session_endpoint(
    body: CreateSessionDTO, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  """
  Membuat session baru secara manual dengan menautkan user_id dari JWT.
  """
  result = create_session(db, body, user_id=current_user.id)
  if result:
    return {
      "status": True, 
      "data": {
        "id": result.id, 
        "title": result.title,
        "user_id": result.user_id,
        "created_at": result.created_at, 
        "updated_at": result.updated_at
      }
    }
  return {"status": False, "data": None, "error": "Failed to create session"}

@router.get("/{session_id}")
async def get_session_detail_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  """
  Mengambil detail satu session milik user.
  """
  session = get_session_by_id(db, session_id, current_user.id)
  if not session:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Session tidak ditemukan"
    )
  return {
    "status": True,
    "data": {
      "id": session.id,
      "title": session.title,
      "user_id": session.user_id,
      "created_at": session.created_at,
      "updated_at": session.updated_at
    }
  }

@router.delete("/{session_id}")
async def delete_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
  """
  Menghapus session beserta seluruh pesan di dalamnya.
  """
  success = delete_session(db, session_id, current_user.id)
  if not success:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Session tidak ditemukan atau gagal dihapus"
    )
  return {
    "status": True,
    "data": {"message": "Session berhasil dihapus"}
  }

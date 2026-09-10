from sqlalchemy.orm import Session
from src.session.dto.session_dto import CreateSessionDTO
from .session_model import SessionModel
from src.chat.chat_model import ChatModel

def create_session(db: Session, payload: CreateSessionDTO, user_id: int | None = None):
  try:
    new_session = SessionModel(
      title=payload.title,
      user_id=user_id
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session
  except Exception as e:
    db.rollback()
    print(f"Error creating session: {e}")
    return None

def get_sessions_by_user(db: Session, user_id: int):
  """
  Mengambil daftar seluruh session milik pengguna tertentu berdasarkan user_id dari JWT.
  Diurutkan dari sesi terbaru (updated_at/created_at desc).
  """
  try:
    return db.query(SessionModel).filter(
      SessionModel.user_id == user_id
    ).order_by(SessionModel.updated_at.desc()).all()
  except Exception as e:
    print(f"Error fetching sessions for user {user_id}: {e}")
    return []

def get_session_by_id(db: Session, session_id: int, user_id: int):
  """
  Mengambil detail satu session tertentu yang terverifikasi milik pengguna tersebut.
  """
  try:
    return db.query(SessionModel).filter(
      SessionModel.id == session_id,
      SessionModel.user_id == user_id
    ).first()
  except Exception as e:
    print(f"Error fetching session {session_id}: {e}")
    return None

def delete_session(db: Session, session_id: int, user_id: int):
  """
  Menghapus session beserta seluruh pesan obrolan di dalamnya.
  """
  try:
    session = db.query(SessionModel).filter(
      SessionModel.id == session_id, 
      SessionModel.user_id == user_id
    ).first()
    if not session:
      return False
      
    # Hapus pesan terkait agar tidak melanggar foreign key constraint
    db.query(ChatModel).filter(ChatModel.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return True
  except Exception as e:
    db.rollback()
    print(f"Error deleting session {session_id}: {e}")
    return False

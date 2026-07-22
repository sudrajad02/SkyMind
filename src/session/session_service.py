from sqlalchemy.orm import Session
from src.session.dto.session_dto import CreateSessionDTO
from .session_model import SessionModel

def create_session(db: Session, payload: CreateSessionDTO):
  try:
    new_session = SessionModel(title=payload.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session
  except Exception as e:
    db.rollback()
    print(f"Error creating session: {e}")
    return None

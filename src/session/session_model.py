from sqlalchemy import Column, String, DateTime, Integer
from src.config.db import Base
import uuid
import datetime

class SessionModel(Base):
	__tablename__ = "chat_sessions"

	id = Column(Integer, primary_key=True, autoincrement=True)
	title = Column(String(255))
	user_id = Column(Integer, nullable=True)
	created_at = Column(DateTime, default=datetime.datetime.utcnow)
	updated_at = Column(DateTime, default=datetime.datetime.utcnow)

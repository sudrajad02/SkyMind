from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON
from src.config.db import Base
import datetime

class ChatModel(Base):
	__tablename__ = "chat_messages"

	id = Column(Integer, primary_key=True, autoincrement=True)
	session_id = Column(Integer, ForeignKey("chat_sessions.id"))
	content = Column(Text)
	weather_json = Column(JSON)
	sender = Column(String)
	created_at = Column(DateTime, default=datetime.datetime.utcnow)

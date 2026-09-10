from pydantic import BaseModel

class CreateChatDTO(BaseModel):
  session_id: int | None = None
  content: str
  weather_json: dict | None = None

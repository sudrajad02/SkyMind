from pydantic import BaseModel

class CreateChatDTO(BaseModel):
  session_id: int
  content: str
  weather_json: dict | None = None

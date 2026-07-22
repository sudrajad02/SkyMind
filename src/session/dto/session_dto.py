from pydantic import BaseModel

class CreateSessionDTO(BaseModel):
  title: str | None = None
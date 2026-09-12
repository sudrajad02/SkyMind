from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class RegisterDTO(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")

class LoginDTO(BaseModel):
    email: EmailStr
    password: str

class UserResponseDTO(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

class TokenResponseDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponseDTO

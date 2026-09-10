from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.config.db import get_db
from src.auth.dto.auth_dto import RegisterDTO, LoginDTO
from src.auth.auth_service import register_user, authenticate_user
from src.auth.auth_middleware import get_current_user
from src.auth.auth_model import UserModel

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_endpoint(body: RegisterDTO, db: Session = Depends(get_db)):
    user = register_user(db, body)
    return {
        "status": True,
        "data": {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
        },
    }

@router.post("/login", status_code=status.HTTP_200_OK)
async def login_endpoint(body: LoginDTO, db: Session = Depends(get_db)):
    auth_data = authenticate_user(db, body)
    user = auth_data["user"]
    return {
        "status": True,
        "data": {
            "access_token": auth_data["access_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
            }
        },
    }

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me_endpoint(current_user: UserModel = Depends(get_current_user)):
    return {
        "status": True,
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at,
        },
    }

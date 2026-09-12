from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.auth.auth_model import UserModel
from src.auth.dto.auth_dto import RegisterDTO, LoginDTO
from src.auth.auth_utils import hash_password, verify_password, create_access_token

def get_user_by_email(db: Session, email: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.id == user_id).first()

def register_user(db: Session, payload: RegisterDTO) -> UserModel:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )
    
    hashed_pwd = hash_password(payload.password)
    new_user = UserModel(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hashed_pwd
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mendaftarkan user: {str(e)}"
        )

def authenticate_user(db: Session, payload: LoginDTO) -> dict:
    user = get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User belum terdaftar"
        )
    
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password salah"
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {
        "access_token": access_token,
        "user": user
    }

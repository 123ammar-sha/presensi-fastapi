from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import engine
from app.models import User, UserPublic
from app.security import buat_token, user_saat_ini, verifikasi_password

router = APIRouter(tags=["Auth"])

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.employee_id == form.username)).first()
        if user is None or not verifikasi_password(form.password, user.password_hash):
            raise HTTPException(status_code=401, detail="ID atau password salah")
        token = buat_token(user.employee_id, user.role)

        return {"access_token":token, "token_type":"bearer"}


@router.get("/saya", response_model=UserPublic)
def profil_saya(user: User = Depends(user_saat_ini)):
    return user
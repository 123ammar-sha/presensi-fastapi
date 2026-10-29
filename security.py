from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from config import settings
from database import engine
from models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def hash_password(password: str)->str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verifikasi_password(password: str, hashed: str)-> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def buat_token(employee_id: str, role: str)-> str:
    kadaluarsa = datetime.now(timezone.utc) + timedelta(minutes=settings.token_menit)
    isi = {"sub": employee_id, "role": role, "exp": kadaluarsa}

    return jwt.encode(isi, settings.secret_key, algorithm=settings.algorithm)

def user_saat_ini(token: str = Depends(oauth2_scheme)):
    try:
        isi = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.employee_id == isi["sub"])
        ).first()

        if user is None:
            raise HTTPException(status_code=401, detail="User tidak ditemukan")

        return user


def hanya_admin(user: User = Depends(user_saat_ini)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Khusus Admin")
    return user

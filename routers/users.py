import json
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlmodel import Session, select

from database import engine
from models import User, UserCreate, UserPublic, UserUpdate, WajahStatus
from security import hanya_admin, hash_password, user_saat_ini
from services.face import encoding_dari_bytes, baca_foto

router = APIRouter(tags=["Users"])

@router.post("/users", response_model=UserPublic, dependencies=[Depends(hanya_admin)])
def tambah_user(data: UserCreate): #nanti ditambahi
    with Session(engine) as session:
        sudah_ada = session.exec( select(User).where(User.employee_id == data.employee_id)).first()
        if sudah_ada:
            raise HTTPException(status_code = 400, detail="employee_id sudah terdaftar")

        user = User.model_validate(data, update={"password_hash":hash_password(data.password)})

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

@router.get("/users", response_model=list[UserPublic], dependencies=[Depends(hanya_admin)])
def daftar_user():
    with Session(engine) as session:
        return session.exec(select(User)).all()

@router.get("/users/{user_id}", response_model=UserPublic, dependencies=[Depends(hanya_admin)])
def lihat_user(user_id:int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code = 404, detail="User tidak ditemukan!")

        return user

@router.put("/users/{user_id}", response_model=UserPublic,)
def ubah_user(user_id:int, data: UserUpdate, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")

        perubahan = data.model_dump(exclude_unset=True)
        user.sqlmodel_update(perubahan)

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

@router.delete("/users/{user_id}")
def delete_user(user_id:int, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        session.delete(user)
        session.commit()
        return {"pesan":"User dihapus"}


@router.post("/users/{user_id}/wajah", response_model= WajahStatus)
def daftar_wajah(user_id:int, foto: list[UploadFile] = File(...), admin: User = Depends(hanya_admin)):
    if not 1 <= len(foto) <= 3:
        raise HTTPException(status_code=400, detail="Kirim 1 sampai 3 foto")

    daftar = []
    for f in foto:
        isi = baca_foto(f)
        daftar.append(encoding_dari_bytes(isi))

    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        user.face_encodings = json.dumps(daftar)
        session.add(user)
        session.commit()

    return WajahStatus(jumlah_foto=len(daftar))
from models import *
from helpers import WIB, cek_radius, ambil_pengaturan, sekarang_wib, cari_lokasi_terdekat
from security import (
    buat_token, hanya_admin, hash_password, user_saat_ini, verifikasi_password,
)

from config import settings
from datetime import date, datetime, time, timedelta, timezone
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException
from sqlmodel import Field, SQLModel, Session,create_engine,  select


SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
TOKEN_MENIT = settings.token_menit

from database import engine
from database import buat_tabel

buat_tabel()

app = FastAPI()

@app.get("/")
def halaman_utama():
    return {"pesan":"API Presensi Start"}

@app.get("/ping")
def ping():
    return{"status":"ping"}


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.employee_id == form.username)).first()
        if user is None or not verifikasi_password(form.password, user.password_hash):
            raise HTTPException(status_code=401, detail="ID atau password salah")
        token = buat_token(user.employee_id, user.role)

        return {"access_token":token, "token_type":"bearer"}


@app.post("/users", response_model=UserPublic, dependencies=[Depends(hanya_admin)])
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

@app.get("/users", response_model=list[UserPublic],dependencies=[Depends(user_saat_ini)])
def daftar_user():
    with Session(engine) as session:
        return session.exec(select(User)).all()

@app.get("/users/{user_id}", response_model=UserPublic, dependencies=[Depends(user_saat_ini)])
def lihat_user(user_id:int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code = 404, detail="User tidak ditemukan!")

        return user

@app.put("/users/{user_id}", response_model=UserPublic,)
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

@app.delete("/users/{user_id}")
def delete_user(user_id:int, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        session.delete(user)
        session.commit()
        return {"pesan":"User dihapus"}

@app.get("/saya", response_model=UserPublic)
def profil_saya(user: User = Depends(user_saat_ini)):
    return user

@app.post("/lokasi", response_model=Location)
def tambah_lokasi(data: LocationCreate, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        lokasi = Location.model_validate(data)
        session.add(lokasi)
        session.commit()
        session.refresh(lokasi)
        return lokasi


@app.get("/lokasi", response_model=list[Location])
def daftar_lokasi(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        return session.exec(select(Location)).all()


@app.delete("/lokasi/{lokasi_id}")
def hapus_lokasi(lokasi_id: int, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        lokasi = session.get(Location, lokasi_id)
        if lokasi is None:
            raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
        session.delete(lokasi)
        session.commit()
        return {"pesan": "Lokasi dihapus"}


@app.get("/pengaturan", response_model=PengaturanInput)
def lihat_pengaturan(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        data = session.get(PengaturanKerja, 1)
        return data or PengaturanInput()


@app.put("/pengaturan", response_model=PengaturanInput)
def ubah_pengaturan(data: PengaturanInput, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        pengaturan = session.get(PengaturanKerja, 1)
        if pengaturan is None:
            pengaturan = PengaturanKerja(id=1, **data.model_dump())
        else:
            pengaturan.sqlmodel_update(data.model_dump())
        session.add(pengaturan)
        session.commit()
        return data

@app.post("/cek-lokasi")
def cek_lokasi(posisi: PosisiInput, user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        daftar = session.exec(select(Location)).all()

    if not daftar:
        raise HTTPException(status_code=404, detail="Belum ada lokasi kantor")

    lokasi, jarak = cari_lokasi_terdekat(posisi.latitude, posisi.longitude, daftar)
    return {
        "kantor_terdekat": lokasi.nama,
        "jarak_meter": round(jarak, 1),
        "radius_meter": lokasi.radius_meters,
        "di_dalam_radius": jarak <= lokasi.radius_meters,
    }

@app.post("/absen/masuk")
def check_in(posisi: PosisiInput, user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        sekarang = sekarang_wib()
        hari_ini = sekarang.date()

        sudah = session.exec(
            select(Absensi).where(
                Absensi.user_id == user.id, Absensi.tanggal == hari_ini
            )
        ).first()
        if sudah:
            raise HTTPException(status_code=400, detail="Sudah check-in hari ini")

        jarak = cek_radius(session, posisi)

        p = ambil_pengaturan(session)
        jam, menit = map(int, p.jam_masuk.split(":"))
        batas = datetime.combine(hari_ini, time(jam, menit), tzinfo=WIB) + timedelta(
            minutes=p.toleransi_menit
        )
        status = "tepat_waktu" if sekarang <= batas else "terlambat"

        absen = Absensi(
            user_id=user.id,
            tanggal=hari_ini,
            jam_masuk=sekarang,
            status=status,
            jarak_masuk=round(jarak, 1),
        )
        session.add(absen)
        session.commit()
        session.refresh(absen)
        return absen

@app.post("/absen/pulang")
def check_out(posisi: PosisiInput, user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        sekarang = sekarang_wib()

        absen = session.exec(
            select(Absensi).where(
                Absensi.user_id == user.id, Absensi.tanggal == sekarang.date()
            )
        ).first()
        if absen is None:
            raise HTTPException(status_code=400, detail="Belum check-in hari ini")
        if absen.jam_pulang is not None:
            raise HTTPException(status_code=400, detail="Sudah check-out hari ini")

        jarak = cek_radius(session, posisi)

        absen.jam_pulang = sekarang
        absen.jarak_pulang = round(jarak, 1)
        session.add(absen)
        session.commit()
        session.refresh(absen)
        return absen


@app.get("/absen/saya")
def riwayat_saya(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        return session.exec(
            select(Absensi)
            .where(Absensi.user_id == user.id)
            .order_by(Absensi.tanggal.desc())
        ).all()
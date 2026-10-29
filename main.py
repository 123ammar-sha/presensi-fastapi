import bcrypt
import jwt
import math

from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException
from sqlmodel import Field, SQLModel, Session,create_engine,  select

engin = create_engine("sqlite:///presensi.db")

def hash_password(password: str)->str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verifikasi_password(password: str, hashed: str)-> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def buat_token(employee_id: str, role: str)-> str:
    kadaluarsa = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MENIT)
    isi = {"sub": employee_id, "role": role, "exp": kadaluarsa}

    return jwt.encode(isi, SECRET_KEY, algorithm=ALGORITHM)



def hitung_jarak(lat1, lon1, lat2, lon2) -> float:
    R = 6371000  # jari-jari bumi dalam meter
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))



def cari_lokasi_terdekat(lat: float, lon: float, daftar: list):
    terdekat = None
    jarak_terdekat = None
    for lokasi in daftar:
        jarak = hitung_jarak(lat, lon, lokasi.latitude, lokasi.longitude)
        if jarak_terdekat is None or jarak < jarak_terdekat:
            terdekat = lokasi
            jarak_terdekat = jarak
    return terdekat, jarak_terdekat


class UserBase(SQLModel):    
    employee_id: str = Field(unique=True)
    nama: str
    jabatan:str | None = None
    role: str = "karyawan"

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password_hash: str

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserPublic(UserBase):
    id:int

class UserUpdate(SQLModel):
    nama: str | None=None
    jabatan: str | None=None
    role: str | None=None


class LocationBase(SQLModel):
    nama:str
    latitude:float = Field(ge=90, le=90)
    longitude:float = Field(ge=90, le=90)
    radius_meters: int = Field(default=50, ge=10, le=1000)

class Location(LocationBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

class LocationCreate(LocationBase):
    pass


class PengaturanInput(SQLModel):
    jam_masuk: str = "08:00"
    toleransi_menit: int = Field(default=15, ge=0, le=120) #maksud ge, le ??
    jam_pulang: str = "17:00"

class PengaturanKerja(PengaturanInput, table=True):
    id: int | None = Field(None, primary_key=True)



class PosisiInput(SQLModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)



SQLModel.metadata.create_all(engin)

SECRET_KEY = "ganti-dengan-teks-acak-yang-panjang"
ALGORITHM = "HS256"
TOKEN_MENIT = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

app = FastAPI()


def user_saat_ini(token: str = Depends(oauth2_scheme)):
    try:
        isi = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    with Session(engin) as session:
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


@app.get("/")
def halaman_utama():
    return {"pesan":"API Presensi Start"}

@app.get("/ping")
def ping():
    return{"status":"ping"}


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    with Session(engin) as session:
        user = session.exec(select(User).where(User.employee_id == form.username)).first()
        if user is None or not verifikasi_password(form.password, user.password_hash):
            raise HTTPException(status_code=401, detail="ID atau password salah")
        token = buat_token(user.employee_id, user.role)

        return {"access_token":token, "token_type":"bearer"}


@app.post("/users", response_model=UserPublic, dependencies=[Depends(hanya_admin)])
def tambah_user(data: UserCreate): #nanti ditambahi
    with Session(engin) as session:
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
    with Session(engin) as session:
        return session.exec(select(User)).all()

@app.get("/users/{user_id}", response_model=UserPublic, dependencies=[Depends(user_saat_ini)])
def lihat_user(user_id:int):
    with Session(engin) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code = 404, detail="User tidak ditemukan!")

        return user

@app.put("/users/{user_id}", response_model=UserPublic,)
def ubah_user(user_id:int, data: UserUpdate, admin: User = Depends(hanya_admin)):
    with Session(engin) as session:
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
    with Session(engin) as session:
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
    with Session(engin) as session:
        lokasi = Location.model_validate(data)
        session.add(lokasi)
        session.commit()
        session.refresh(lokasi)
        return lokasi


@app.get("/lokasi", response_model=list[Location])
def daftar_lokasi(user: User = Depends(user_saat_ini)):
    with Session(engin) as session:
        return session.exec(select(Location)).all()


@app.delete("/lokasi/{lokasi_id}")
def hapus_lokasi(lokasi_id: int, admin: User = Depends(hanya_admin)):
    with Session(engin) as session:
        lokasi = session.get(Location, lokasi_id)
        if lokasi is None:
            raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
        session.delete(lokasi)
        session.commit()
        return {"pesan": "Lokasi dihapus"}


@app.get("/pengaturan", response_model=PengaturanInput)
def lihat_pengaturan(user: User = Depends(user_saat_ini)):
    with Session(engin) as session:
        data = session.get(PengaturanKerja, 1)
        return data or PengaturanInput()


@app.put("/pengaturan", response_model=PengaturanInput)
def ubah_pengaturan(data: PengaturanInput, admin: User = Depends(hanya_admin)):
    with Session(engin) as session:
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
    with Session(engin) as session:
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
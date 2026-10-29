from datetime import date, datetime

from sqlmodel import Field, SQLModel

# USER 
class UserBase(SQLModel):    
    employee_id: str = Field(unique=True)
    nama: str
    jabatan:str | None = None
    role: str = "karyawan"

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password_hash: str
    face_encodings: str | None = None
    
class WajahStatus(SQLModel):
    jumlah_foto: int

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserPublic(UserBase):
    id:int

class UserUpdate(SQLModel):
    nama: str | None=None
    jabatan: str | None=None
    role: str | None=None


# LOCATION & SETTING
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


#  ABSENI
class PosisiInput(SQLModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Absensi(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tanggal: date
    jam_masuk: datetime | None = None
    jam_pulang: datetime | None = None
    status: str | None = None
    jarak_masuk: float | None = None
    jarak_pulang: float | None = None



import json
from datetime import date, datetime

from sqlalchemy import UniqueConstraint
from pydantic import field_validator
from sqlmodel import Field, SQLModel

# USER 
class UserBase(SQLModel):    
    employee_id: str = Field(unique=True)
    nama: str
    jabatan:str | None = None
    role: str = "karyawan"

    @field_validator("role")
    @classmethod
    def validasi_role(cls, value: str) -> str:
        if value not in {"admin", "karyawan"}:
            raise ValueError("role harus admin atau karyawan")
        return value

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password_hash: str
    face_encodings: str | None = None

    @property
    def wajah_terdaftar(self) -> bool:
        if not self.face_encodings:
            return False
        try:
            wajah = json.loads(self.face_encodings)
            return isinstance(wajah, list) and len(wajah) > 0
        except (json.JSONDecodeError, TypeError):
            return False
    
class WajahStatus(SQLModel):
    jumlah_foto: int

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserPublic(UserBase):
    id:int
    wajah_terdaftar: bool = False

class UserUpdate(SQLModel):
    nama: str | None=None
    jabatan: str | None=None
    role: str | None=None

    @field_validator("role")
    @classmethod
    def validasi_role(cls, value: str | None) -> str | None:
        if value is not None and value not in {"admin", "karyawan"}:
            raise ValueError("role harus admin atau karyawan")
        return value


# LOCATION & SETTING
class LocationBase(SQLModel):
    nama:str
    latitude:float = Field(ge=-90, le=90)
    longitude:float = Field(ge=-180, le=180)
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
    __table_args__ = (
        UniqueConstraint("user_id", "tanggal", name="uq_absensi_user_tanggal"),
    )
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tanggal: date
    jam_masuk: datetime | None = None
    jam_pulang: datetime | None = None
    status: str | None = None
    jarak_masuk: float | None = None
    jarak_pulang: float | None = None


# Log Absensi
class LogAbsen(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    waktu: datetime
    jenis: str                      # "masuk" atau "pulang"
    hasil: str                      # berhasil / ditolak_radius / ditolak_wajah / ditolak_lain
    jarak_meter: float | None = None
    jarak_wajah: float | None = None
    keterangan: str | None = None

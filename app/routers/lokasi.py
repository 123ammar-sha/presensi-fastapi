from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.helpers import cari_lokasi_terdekat
from app.models import (
    Location, LocationCreate, PengaturanInput, PengaturanKerja,
    PosisiInput, User,
)
from app.security import hanya_admin, user_saat_ini

router = APIRouter(tags=["Lokasi"])

@router.post("/lokasi", response_model=Location)
def tambah_lokasi(data: LocationCreate, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        lokasi = Location.model_validate(data)
        session.add(lokasi)
        session.commit()
        session.refresh(lokasi)
        return lokasi


@router.get("/lokasi", response_model=list[Location])
def daftar_lokasi(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        return session.exec(select(Location)).all()


@router.delete("/lokasi/{lokasi_id}")
def hapus_lokasi(lokasi_id: int, admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        lokasi = session.get(Location, lokasi_id)
        if lokasi is None:
            raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")
        session.delete(lokasi)
        session.commit()
        return {"pesan": "Lokasi dihapus"}


@router.get("/pengaturan", response_model=PengaturanInput)
def lihat_pengaturan(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        data = session.get(PengaturanKerja, 1)
        return data or PengaturanInput()


@router.put("/pengaturan", response_model=PengaturanInput)
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

@router.post("/cek-lokasi")
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
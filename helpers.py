import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from models import Location, PengaturanInput, PengaturanKerja, PosisiInput

WIB = timezone(timedelta(hours=7))

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


def sekarang_wib() -> datetime:
    return datetime.now(timezone.utc).astimezone(WIB)


def ambil_pengaturan(session: Session) -> PengaturanInput:
    data = session.get(PengaturanKerja, 1)
    return data or PengaturanInput()


def cek_radius(session: Session, posisi: PosisiInput):
    daftar = session.exec(select(Location)).all()
    lokasi, jarak = cari_lokasi_terdekat(posisi.latitude, posisi.longitude, daftar)
    if lokasi is None:
        raise HTTPException(status_code=404, detail="Belum ada lokasi kantor")
    if jarak > lokasi.radius_meters:
        raise HTTPException(
            status_code=400,
            detail=f"Di luar radius kantor ({round(jarak)} m dari {lokasi.nama})",
        )
    return jarak

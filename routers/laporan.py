from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from database import engine
from helpers import sekarang_wib
from models import Absensi, LogAbsen, User
from security import hanya_admin

router = APIRouter(tags=["Laporan"])


@router.get("/laporan/harian")
def laporan_harian(tanggal: date | None = None, admin: User = Depends(hanya_admin)):
    tgl = tanggal or sekarang_wib().date()
    with Session(engine) as session:
        karyawan = session.exec(select(User).where(User.role == "karyawan")).all()
        absen = session.exec(select(Absensi).where(Absensi.tanggal == tgl)).all()
        peta = {a.user_id: a for a in absen}

        data = []
        for k in karyawan:
            a = peta.get(k.id)
            data.append(
                {
                    "employee_id": k.employee_id,
                    "nama": k.nama,
                    "status": a.status if a else "belum_absen",
                    "jam_masuk": a.jam_masuk if a else None,
                    "jam_pulang": a.jam_pulang if a else None,
                }
            )
        return {
            "tanggal": tgl,
            "total_karyawan": len(karyawan),
            "hadir": len(absen),
            "data": data,
        }


@router.get("/laporan/log")
def laporan_log(hasil: str | None = None, limit: int = 100, admin: User = Depends(hanya_admin)):
    query = select(LogAbsen)
    if hasil:
        query = query.where(LogAbsen.hasil == hasil)
    query = query.order_by(LogAbsen.waktu.desc()).limit(limit)
    with Session(engine) as session:
        return session.exec(query).all()


@router.get("/laporan/ringkasan-log")
def ringkasan_log(admin: User = Depends(hanya_admin)):
    with Session(engine) as session:
        baris = session.exec(select(LogAbsen.hasil, func.count()).group_by(LogAbsen.hasil)).all()
        return {hasil: jumlah for hasil, jumlah in baris}
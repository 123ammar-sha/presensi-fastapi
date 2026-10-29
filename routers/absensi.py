from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import engine
from helpers import WIB, ambil_pengaturan, cek_radius, sekarang_wib
from models import Absensi, PosisiInput, User
from security import user_saat_ini

router = APIRouter(tags=["Absensi"])

@router.post("/absen/masuk")
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

@router.post("/absen/pulang")
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


@router.get("/absen/saya")
def riwayat_saya(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        return session.exec(
            select(Absensi)
            .where(Absensi.user_id == user.id)
            .order_by(Absensi.tanggal.desc())
        ).all()
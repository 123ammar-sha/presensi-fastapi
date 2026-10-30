from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import engine
from app.helpers import WIB, ambil_pengaturan, cek_radius, sekarang_wib
from app.models import Absensi, PosisiInput, User
from app.security import user_saat_ini
from app.services.face import baca_foto, encoding_dari_bytes, jarak_terkecil, wajah_cocok
from app.services.log import catat_log

router = APIRouter(tags=["Absensi"])


def verifikasi(session: Session, user: User, jenis: str, lat: float, lon: float, foto: UploadFile):
    """Validasi berurutan: radius dulu, baru wajah. Gagal = catat log lalu raise."""
    # 1. Radius
    try:
        jarak = cek_radius(session, PosisiInput(latitude=lat, longitude=lon))
    except HTTPException as e:
        catat_log(user.id, jenis, "ditolak_radius", keterangan=str(e.detail))
        raise

    # 2. Wajah sudah terdaftar?
    if not user.face_encodings:
        catat_log(user.id, jenis, "ditolak_lain", jarak, keterangan="Wajah belum terdaftar")
        raise HTTPException(status_code=400, detail="Wajah belum terdaftar, hubungi admin")

    # 3. Foto berisi wajah?
    try:
        encoding = encoding_dari_bytes(baca_foto(foto))
    except HTTPException as e:
        catat_log(user.id, jenis, "ditolak_wajah", jarak, keterangan=str(e.detail))
        raise

    # 4. Wajah cocok?
    jarak_wajah = round(jarak_terkecil(user.face_encodings, encoding), 3)
    if not wajah_cocok(jarak_wajah):
        catat_log(user.id, jenis, "ditolak_wajah", jarak, jarak_wajah, "Wajah tidak cocok")
        raise HTTPException(status_code=400, detail="Wajah tidak cocok")

    return jarak, jarak_wajah


@router.post("/absen/masuk")
def check_in(
    latitude: float = Form(ge=-90, le=90),
    longitude: float = Form(ge=-180, le=180),
    foto: UploadFile = File(...),
    user: User = Depends(user_saat_ini),
):
    with Session(engine) as session:
        sekarang = sekarang_wib()
        hari_ini = sekarang.date()

        sudah = session.exec(
            select(Absensi).where(Absensi.user_id == user.id, Absensi.tanggal == hari_ini)
        ).first()
        if sudah:
            raise HTTPException(status_code=400, detail="Sudah check-in hari ini")

        jarak, jarak_wajah = verifikasi(session, user, "masuk", latitude, longitude, foto)

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
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=400, detail="Sudah check-in hari ini")
        session.refresh(absen)

    catat_log(user.id, "masuk", "berhasil", round(jarak, 1), jarak_wajah, status)
    return absen


@router.post("/absen/pulang")
def check_out(
    latitude: float = Form(ge=-90, le=90),
    longitude: float = Form(ge=-180, le=180),
    foto: UploadFile = File(...),
    user: User = Depends(user_saat_ini),
):
    with Session(engine) as session:
        sekarang = sekarang_wib()

        absen = session.exec(
            select(Absensi).where(Absensi.user_id == user.id, Absensi.tanggal == sekarang.date())
        ).first()
        if absen is None:
            raise HTTPException(status_code=400, detail="Belum check-in hari ini")
        if absen.jam_pulang is not None:
            raise HTTPException(status_code=400, detail="Sudah check-out hari ini")

        jarak, jarak_wajah = verifikasi(session, user, "pulang", latitude, longitude, foto)

        absen.jam_pulang = sekarang
        absen.jarak_pulang = round(jarak, 1)
        session.add(absen)
        session.commit()
        session.refresh(absen)

    catat_log(user.id, "pulang", "berhasil", round(jarak, 1), jarak_wajah)
    return absen


@router.get("/absen/saya")
def riwayat_saya(user: User = Depends(user_saat_ini)):
    with Session(engine) as session:
        return session.exec(
            select(Absensi).where(Absensi.user_id == user.id).order_by(Absensi.tanggal.desc())
        ).all()
from database import engine
from helpers import sekarang_wib
from models import LogAbsen
from sqlmodel import Session


def catat_log(user_id, jenis, hasil, jarak_meter=None, jarak_wajah=None, keterangan=None):
    # Pakai session sendiri agar log tetap tersimpan walau request ditolak
    with Session(engine) as session:
        session.add(
            LogAbsen(
                user_id=user_id,
                waktu=sekarang_wib(),
                jenis=jenis,
                hasil=hasil,
                jarak_meter=jarak_meter,
                jarak_wajah=jarak_wajah,
                keterangan=keterangan,
            )
        )
        session.commit()
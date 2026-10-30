import io
import json
import face_recognition
import numpy as np

from fastapi import HTTPException
from PIL import Image

from app.config import settings

MAXS_SISI = 640
MAKS_BYTES = 5 * 1024 * 1024

def baca_foto(upload) -> bytes:
    data = upload.file.read(MAKS_BYTES + 1)
    if len(data) > MAKS_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Foto terlalu besar (maks 5 MB)",
        )
    if not data:
        raise HTTPException(status_code=400, detail="File foto kosong")
    return data

def encoding_dari_bytes(data:bytes) -> list[float]:
    """Ubah data foto menjadi satu encoding 128 angka list"""
    try:
        gambar = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="File bukan gambar yang valid")

    gambar.thumbnail((MAXS_SISI, MAXS_SISI))
    hasil = face_recognition.face_encodings(np.array(gambar))

    if len(hasil) == 0:
        raise HTTPException(status_code=400, detail="Wajah tak terdeteksi")
    if len(hasil) > 1:
        raise HTTPException(status_code=400, detail="Terdeteksi lebih dari satu wajah")
    return hasil[0].tolist()

def jarak_terkecil(encoding_json: str, encoding_baru: list[float]) -> float:
    """Jarak terkecil antara foto presensi dengan foto msater"""
    master = [np.array(e) for e in json.loads(encoding_json)]
    jarak = face_recognition.face_distance(master, np.array(encoding_baru))
    return float(min(jarak))

def wajah_cocok(jarak: float) -> bool:
    return jarak <= settings.face_threshold 
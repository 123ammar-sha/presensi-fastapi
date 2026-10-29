from fastapi import FastAPI

from models import *
from routers import absensi, auth, lokasi, users
from database import buat_tabel

buat_tabel()

app = FastAPI()

@app.get("/")
def halaman_utama():
    return {"pesan":"API Presensi Start"}

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(lokasi.router)
app.include_router(absensi.router)
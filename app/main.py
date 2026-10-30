from fastapi import FastAPI

from app.models import *
from app.routers import absensi, auth, lokasi, users, laporan
from app.database import buat_tabel

from fastapi.middleware.cors import CORSMiddleware

buat_tabel()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # alamat Vue (Vite) default
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def halaman_utama():
    return {"pesan":"API Presensi Start"}

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(lokasi.router)
app.include_router(absensi.router)
app.include_router(laporan.router)
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def halaman_utama():
    return {"pesan":"API Presensi Start"}

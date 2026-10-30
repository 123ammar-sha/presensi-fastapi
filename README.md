# Sistem Presensi Karyawan Berbasis Geofencing GPS dan Verifikasi Wajah

REST API presensi karyawan yang memvalidasi **lokasi (geofencing)** dan **wajah (face recognition)** sebelum absensi dicatat. Dibangun dengan FastAPI sebagai backend terpisah (_decoupled_) yang dikonsumsi oleh aplikasi mobile (Flutter) dan dashboard web admin (Vue.js).

**Status:** Backend MVP selesai. Frontend (Flutter dan Vue) dikerjakan terpisah.

> Panduan lengkap data form, JSON, multipart, header, role, respons, dan penanganan
> error untuk Flutter/Vue tersedia di [FRONTEND_README.md](FRONTEND_README.md).
>
> Aturan implementasi khusus aplikasi mobile tersedia di
> [FLUTTER_README.md](FLUTTER_README.md).

## Fitur

- Login JWT dengan dua role: `admin` dan `karyawan`
- CRUD karyawan (khusus admin), password disimpan sebagai hash bcrypt
- Manajemen lokasi kantor (banyak lokasi, radius per lokasi) dan jam kerja
- Geofencing: jarak posisi karyawan ke kantor dihitung dengan rumus Haversine
- Registrasi wajah (1-3 foto master per karyawan, disimpan sebagai encoding 128 dimensi, foto asli tidak disimpan)
- Check-in dan check-out dengan validasi berurutan: radius, lalu wajah
- Status kehadiran otomatis: `tepat_waktu` atau `terlambat`
- Log seluruh percobaan absen (berhasil dan ditolak) untuk audit dan pengukuran akurasi
- Laporan harian, log, dan ringkasan untuk admin

## Teknologi

| Lapisan     | Pilihan                                                           |
| ----------- | ----------------------------------------------------------------- |
| Framework   | FastAPI + Uvicorn                                                 |
| Database    | SQLite + SQLModel (dapat diganti PostgreSQL lewat `DATABASE_URL`) |
| Autentikasi | PyJWT + bcrypt                                                    |
| Wajah       | face_recognition (dlib), Pillow, NumPy                            |
| Konfigurasi | pydantic-settings (`.env`)                                        |
| Klien       | Flutter (mobile), Vue.js 3 (web admin)                            |

## Struktur Proyek

```
presensi-fastAPI/
├── seed.py            # membuat admin awal
├── main.py            # wrapper kompatibilitas untuk uvicorn main:app
├── app/
│   ├── main.py        # membuat app, memasang router, CORS
│   ├── config.py      # membaca .env
│   ├── database.py    # engine dan pembuat tabel
│   ├── models.py      # tabel dan skema input/output
│   ├── security.py    # hash password, JWT, user_saat_ini, hanya_admin
│   ├── helpers.py     # Haversine, cek_radius, waktu WIB
│   ├── routers/
│   │   ├── auth.py    # /login, /saya
│   │   ├── users.py   # CRUD user, registrasi wajah
│   │   ├── lokasi.py  # lokasi, pengaturan jam kerja, cek-lokasi
│   │   ├── absensi.py # check-in, check-out, riwayat
│   │   └── laporan.py # laporan admin
│   └── services/
│       ├── face.py    # encoding dan perbandingan wajah
│       └── log.py     # pencatatan log percobaan
```

## Instalasi

Prasyarat: Python 3.12, Ubuntu/Debian (untuk kompilasi dlib).

```bash
# 1. Library sistem untuk membangun dlib
sudo apt install build-essential cmake libopenblas-dev liblapack-dev

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Dependensi
pip install -r requirements.txt
```

Catatan: `setuptools` harus versi di bawah 81 (`pip install "setuptools<81"`), karena `face_recognition_models` membutuhkan `pkg_resources`.

## Konfigurasi

Salin `.env.example` menjadi `.env`, lalu isi:

```
SECRET_KEY=isi-dengan-teks-acak-panjang
ALGORITHM=HS256
TOKEN_MENIT=480
DATABASE_URL=sqlite:///presensi.db
FACE_THRESHOLD=0.5
```

`.env` tidak boleh di-commit.

## Menjalankan

```bash
python seed.py                      # membuat admin awal (ADM001), sekali saja
uvicorn app.main:app --reload       # pengembangan
uvicorn app.main:app --host 0.0.0.0 # agar dapat diakses dari HP di jaringan yang sama
```

Dokumentasi interaktif: `http://127.0.0.1:8000/docs`

## Daftar Endpoint

| Method    | Path                       | Akses         | Fungsi                                 |
| --------- | -------------------------- | ------------- | -------------------------------------- |
| POST      | `/login`                   | publik        | login (form-data), mengembalikan token |
| GET       | `/saya`                    | login         | profil pengguna saat ini               |
| POST      | `/users`                   | admin         | tambah karyawan                        |
| GET       | `/users`, `/users/{id}`    | login         | daftar dan detail                      |
| PUT       | `/users/{id}`              | admin         | ubah sebagian data                     |
| DELETE    | `/users/{id}`              | admin         | hapus                                  |
| POST      | `/users/{id}/wajah`        | admin         | daftarkan 1-3 foto wajah               |
| POST      | `/lokasi`                  | admin         | tambah lokasi kantor                   |
| GET       | `/lokasi`                  | login         | daftar lokasi                          |
| DELETE    | `/lokasi/{id}`             | admin         | hapus lokasi                           |
| GET / PUT | `/pengaturan`              | login / admin | jam kerja dan toleransi                |
| POST      | `/cek-lokasi`              | login         | uji jarak ke kantor terdekat           |
| POST      | `/absen/masuk`             | login         | check-in (lokasi + wajah)              |
| POST      | `/absen/pulang`            | login         | check-out (lokasi + wajah)             |
| GET       | `/absen/saya`              | login         | riwayat absen sendiri                  |
| GET       | `/laporan/harian?tanggal=` | admin         | kehadiran per hari                     |
| GET       | `/laporan/log?hasil=`      | admin         | log percobaan absen                    |
| GET       | `/laporan/ringkasan-log`   | admin         | jumlah per jenis hasil                 |

## Alur Check-in

```
Flutter: GPS + foto kamera depan
   │  POST /absen/masuk  (multipart: latitude, longitude, foto)
   ▼
1. Validasi token JWT (user_saat_ini)
2. Sudah check-in hari ini?            → 400
3. Radius: Haversine ke kantor terdekat → 400 + log ditolak_radius
4. Wajah sudah terdaftar?              → 400 + log ditolak_lain
5. Encoding foto, jarak ke foto master → 400 + log ditolak_wajah
6. Hitung status (tepat_waktu/terlambat) dari jam server
7. Simpan absensi + log berhasil       → 200
```

## Aturan Bisnis

- Waktu diambil dari **server** (UTC, dikonversi ke WIB), tidak pernah dari klien.
- Identitas pengabsen diambil dari **token**, bukan dari body request.
- Terlambat jika check-in melewati `jam_masuk + toleransi_menit`.
- Wajah cocok jika jarak terkecil ke salah satu foto master ≤ `FACE_THRESHOLD` (default 0.5).
- Satu karyawan satu check-in dan satu check-out per hari.

## Kontrak Waktu API

Semua waktu adalah WIB dalam format ISO 8601 **tanpa offset**, contohnya
`2026-10-30T08:05:12`. Klien menampilkan nilai tersebut apa adanya dan tidak
melakukan konversi timezone.

## Keamanan

- Password di-hash bcrypt dengan salt.
- JWT bertanda tangan `SECRET_KEY`, berlaku sesuai `TOKEN_MENIT`.
- Respons memakai skema `UserPublic`, sehingga hash dan encoding wajah tidak bocor.
- Pesan login sama untuk "ID salah" dan "password salah" (mencegah user enumeration).
- Hak akses minimum: hanya admin yang mengubah user, lokasi, dan pengaturan.

## Keterbatasan yang Diketahui

- **Tidak ada anti-spoofing:** foto cetak atau layar HP dapat lolos verifikasi wajah.
- **Fake GPS:** koordinat palsu tidak terdeteksi di server (mitigasi di klien: `Position.isMocked`).
- Pembatasan "tanpa galeri" hanya dapat ditegakkan di sisi klien.
- Perbandingan radius dilakukan terhadap kantor terdekat saja.
- Tabel baru dibuat otomatis, tetapi perubahan kolom pada tabel lama dilakukan manual (`ALTER TABLE`), belum memakai migrasi (Alembic).
- Akurasi wajah harus diukur lewat uji coba sendiri (lihat `/laporan/ringkasan-log`).

## Pengujian Akurasi

Gunakan tabel skenario (terang, redup, berkacamata/masker, orang berbeda) lalu hitung:

```
FRR = orang sah ditolak ÷ total uji orang sah × 100%
FAR = orang lain diterima ÷ total uji orang lain × 100%
```

Data jarak wajah tiap percobaan tersimpan pada log.

## Alur Git

- `main`: hanya kode yang sudah teruji.
- `dev`: kerja harian. Merge ke `main` setelah tes lulus.
- Format commit: `jenis(langkah-N): ringkasan` dengan jenis `feat`, `fix`, `refactor`, atau `docs`. Tiap langkah diberi tag `langkah-N`.

## Rencana Lanjutan

- Flutter: login, kamera depan live, GPS, kirim absen
- Vue.js: login admin, CRUD karyawan, pengaturan lokasi, tabel laporan (polling)
- Dockerisasi API
- Liveness detection dan deteksi fake GPS
- Migrasi database dengan Alembic

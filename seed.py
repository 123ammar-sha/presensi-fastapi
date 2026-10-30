from sqlmodel import Session, select

from database import buat_tabel, engine
from models import User
from security import hash_password

buat_tabel()
with Session(engine) as session:
    if session.exec(select(User).where(User.employee_id == "ADM001")).first():
        print("ADM001 sudah ada")
    else:
        session.add(User(employee_id="ADM001", nama="HRD Utama", role="admin",
                         password_hash=hash_password("rahasia123")))
        session.commit()
        print("ADM001 dibuat")
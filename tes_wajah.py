import face_recognition


def ambil_encoding(path):
    gambar = face_recognition.load_image_file(path)
    hasil = face_recognition.face_encodings(gambar)
    if len(hasil) == 0:
        return None  # tidak ada wajah
    return hasil[0]


e1 = ambil_encoding("wajah1.jpg")
e2 = ambil_encoding("images.jpg")

print("Panjang encoding:", len(e1))

jarak = face_recognition.face_distance([e1], e2)[0]
print("Jarak wajah1 vs wajah2:", round(float(jarak), 3))
print("Cocok?", jarak <= 0.5)
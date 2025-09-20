# SOC Event Processing Tool

Script Python ini digunakan untuk **mengelola event log, mendeteksi false positive, membuat laporan, dan men-generate template event** secara otomatis untuk kebutuhan SOC.

---

## ⚙️ Fitur Utama

1. **Proses file TXT** → buat laporan WA dan Event Report
2. **Proses file XML** → export ke Excel
3. **Buat template event baru**
4. **Cek false positive**

---

## 📂 Struktur Folder

```
input/                  # Folder berisi file TXT atau XML untuk diproses
outputs/                # Folder hasil output (WA, Event Report, Excel)
templates/              # Folder template event
main.py                 # Script utama
database/
    ├── events_magnitude_list.csv  # Database event
    └── False_Positive.txt         # Daftar false positive
README.md               # Dokumentasi
```

---

## ⚙️ Cara Menjalankan

1. Pastikan Python ≥ 3.8 sudah terinstal.
2. Jalankan script utama:

```bash
python main.py
```

3. Pilih mode sesuai kebutuhan:

| Mode | Deskripsi                 |
| ---- | ------------------------- |
| 1    | Proses TXT → WA Report    |
| 2    | Proses TXT → Event Report |
| 3    | Proses XML → Excel Export |
| 4    | Buat Template Event       |
| 5    | Cek False Positive        |
| 99   | Exit                      |

---

## 📝 Penjelasan Mode

### 1. Proses TXT → WA Report / Event Report

* Membaca file `.txt` di folder `input/`
* Membuat laporan WA berdasarkan template (`templates/wa.txt`)
* Membuat file detail per event berdasarkan template masing-masing event
* Menampilkan summary false positive

### 2. Proses XML → Excel Export

* Membaca file `.xml` di folder `input/`
* Mengexport ke Excel (`outputs/FollowUp & Closed Offenses List - [tanggal].xlsx`)
* Otomatis menghapus file XML setelah diproses

### 3. Buat Template Event

* Masukkan nama event, deskripsi, dan mitigasi
* Template baru tersimpan di `templates/` sebagai `[EventName].txt`

### 4. Cek False Positive

* Masukkan nama event untuk dicek
* Status yang ditampilkan:

  * ✅ Valid → ada di database, bukan FP
  * 🚫 False Positive → ada di database, termasuk FP
  * ❓ Unknown → tidak ada di database, disertai suggestion jika mirip

---

## 🔑 Perintah Khusus di Mode False Positive

* `exit` → keluar ke menu utama
* `listfp` → tampilkan daftar false positive
* `listdb` → tampilkan daftar event di database

---

## 📌 Catatan

* `events_magnitude_list.csv` harus berisi daftar event yang valid.
* `False_Positive.txt` berisi daftar event yang sudah diverifikasi **tidak berbahaya**.
* Script otomatis menampilkan suggestion jika nama event tidak ditemukan di database.
* File WA dan detail event tersimpan di `outputs/shiftX/` sesuai shift yang dipilih.

---

## 🔧 Shift

| Kode | Nama Shift    | Waktu         |
| ---- | ------------- | ------------- |
| 3    | Selamat Pagi  | 00.00 - 08.00 |
| 1    | Selamat Sore  | 08.00 - 16.00 |
| 2    | Selamat Malam | 16.00 - 00.00 |

---

## 📜 Lisensi

Bebas digunakan untuk SOC, Blue Team, atau Incident Handling internal.

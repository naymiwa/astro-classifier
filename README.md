# Astro Classifier

Website klasifikasi gambar benda ruang angkasa. User bisa upload:
- **Gambar** (JPG/PNG/WEBP) → ditebak di antara 6 kelas: constellation, cosmos_space, galaxies, nebula, planets, stars.
- **File FITS** (`.fits` / `.fit` / `.fits.gz`) → ditebak bintang vs galaksi, plus preview PNG.

Dibuat untuk observer teleskop: hasil observasi format FITS bisa langsung diupload dan web kasih jawaban benda apa + penjelasan singkat.

## Cara jalanin

### 1. Setup environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-backend.txt
```

### 2. Siapkan model
Repository sudah menyertakan model yang sudah dilatih:
- `best_model.keras` — model gambar 6 kelas (EfficientNetB0)
- `fits_star_galaxy_model.keras` — model FITS bintang vs galaksi (CNN 2 kelas)
- `class_names.txt`, `fits_class_names.txt` — urutan kelas (index model harus sama dgn urutan di sini)

### 3. Jalankan server
```powershell
.\.venv\Scripts\activate
uvicorn main:app --reload
```
Buka `http://127.0.0.1:8000` di browser. Endpoint Swagger UI ada di `http://127.0.0.1:8000/docs`.

## Struktur project

```
astro-project/
├─ main.py                      # Backend FastAPI: /predict, /predict_fits, /fits_preview, /health
├─ index.html                   # Frontend (1 file): upload gambar / FITS, preview, hasil + penjelasan
├─ fits_utils.py                # Preprocessing FITS (dipakai training & inference)
├─ best_model.keras             # Model gambar 6 kelas (EfficientNetB0)
├─ class_names.txt              # Urutan kelas model gambar
├─ fits_star_galaxy_model.keras # Model FITS 2 kelas (star/galaxy)
├─ fits_class_names.txt         # Urutan kelas model FITS
├─ train_image.py               # Skrip training model gambar 6 kelas (EfficientNet fine-tune)
├─ train_fits.py                # Skrip training model FITS (CNN biner)
├─ generate_dataset.py          # Generator dataset FITS sintetis (meniru kondisi teleskop)
├─ classification_dataset/      # 1000 file FITS hasil generate (star vs galaxy)
├─ classification_labels.csv    # Label dataset FITS (0=star, 1=galaxy)
├─ space images/                # Dataset gambar Kaggle (6 folder per kelas) — hasil extract archive.zip
├─ archive.zip                  # Dataset Kaggle "Astronomy Image Classification Dataset"
├─ requirements-backend.txt     # Dependensi Python
└─ best_model.backup.keras      # Backup model gambar lama
```

## Melatih ulang model

### Model gambar 6 kelas
Dataset harus sudah di-extract ke folder `space images/`:
```powershell
Expand-Archive archive.zip -DestinationPath .
python train_image.py                                   # default: 20 epoch head + 10 epoch fine-tune
python train_image.py --epochs 25 --fine-epochs 15      # atur sesuai kebutuhan
python train_image.py --no-finetune                     # head aja, cepat buat tes
```
Output: `best_model.keras` + `class_names.txt` + laporan evaluasi (accuracy, confusion matrix).

### Model FITS bintang vs galaksi
Dataset FITS bisa diregenerate dulu kalau perlu:
```powershell
python generate_dataset.py --count 1000        # buat dataset sintetis
python train_fits.py                           # latih CNN biner
```
Output: `fits_star_galaxy_model.keras` + `fits_class_names.txt`.

## Endpoint API

| Method | Path | Fungsi |
|---|---|---|
| GET | `/` | Halaman frontend (`index.html`) |
| GET | `/health` | Status + daftar kelas |
| POST | `/predict` | Klasifikasi gambar (JPG/PNG/WEBP) → top-3 + penjelasan |
| POST | `/predict_fits` | Klasifikasi FITS → star/galaxy + probabilitas + kualitas |
| POST | `/fits_preview` | Render FITS → PNG (preview sebelum analisis) |

Semua endpoint upload pakai `multipart/form-data`, field name `file`.

## Catatan & limitasi

- **Model FITS cuma 2 kelas (bintang vs galaksi).** Nebula, planet, konstelasi belum didukung di mode FITS. Untuk objek sebaik itu pakai mode Gambar (upload hasil render JPG).
- **Model FITS dilatih dari data sintetis** (`generate_dataset.py`) yang meniru kondisi teleskop: profil Gaussian/Moffat untuk bintang, Sersic2D + konvolusi PSF untuk galaksi, plus sky background, readout noise, cosmic rays, dan bad pixel. Hasil di luar sebaran itu belum tentu akurat.
- Backend memuat kedua model saat startup (±5-10 detik), jadi request pertama setelah jalan mungkin agak lambat.
- Upload maksimal 25 MB per file.
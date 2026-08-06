"""
Fase 2 - Backend FastAPI buat serve model classifier lewat endpoint /predict.

Cara pakai:
    uvicorn main:app --reload

Lalu buka http://127.0.0.1:8000/docs buat coba upload gambar langsung dari browser
(Swagger UI otomatis dibikinin sama FastAPI).

Syarat file yang harus ada sejajar sama main.py:
    best_model.keras            (model 6 kelas: gambar)
    class_names.txt
    fits_star_galaxy_model.keras (model 2 kelas: bintang vs galaksi dari FITS)
    fits_class_names.txt

Endpoint:
    GET  /            -> health check
    POST /predict     -> klasifikasi gambar (JPG/PNG/WEBP, 6 kelas)
    POST /predict_fits-> klasifikasi FITS (star/galaxy)
    POST /fits_preview-> render preview PNG dari FITS
"""
import io

import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from tensorflow import keras

import fits_utils

MODEL_PATH = "best_model.keras"
CLASS_NAMES_PATH = "class_names.txt"
IMG_SIZE = (224, 224)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

FITS_MODEL_PATH = "fits_star_galaxy_model.keras"
FITS_CLASS_NAMES_PATH = "fits_class_names.txt"
FITS_CLASS_NAMES = ["star", "galaxy"]
ALLOWED_FITS_SUFFIXES = (".fits", ".fit", ".fits.gz")

EXPLANATIONS = {
    "star": (
        "Bintang adalah bola gas panas (terutama hidrogen dan helium) yang "
        "memancarkan cahaya dari reaksi fusi nuklir di intinya. Di foto teleskop, "
        "bintang tampak sebagai sumber titik yang tajam, karena cahayanya "
        "terkonsentrasi hanya pada beberapa piksel."
    ),
    "galaxy": (
        "Galaksi adalah sistem masif berisi milyaran bintang, gas, debu, dan "
        "materi gelap yang terikat gravitasi. Pada foto teleskop, galaksi tampak "
        "lebih lebar dan menyebar (extended) dibanding bintang, dengan inti "
        "terang dan cahaya yang memudar ke tepi."
    ),
    "stars": (
        "Bintang adalah bola gas panas yang memancarkan cahaya dari reaksi fusi "
        "di intinya. Kelas ini mencakup gambar bintang individu atau gugusan "
        "bintang yang tampak sebagai titik-titik terang."
    ),
    "galaxies": (
        "Galaksi adalah kumpulan raksasa bintang, gas, debu, dan materi gelap "
        "yang terikat gravitasi. Contoh: Bima Sakti, Andromeda. Bentuknya "
        "beragam — spiral, elips, atau tak beraturan."
    ),
    "nebula": (
        "Nebula adalah awan raksasa gas dan debu antar bintang. Ada yang menjadi "
        "tempat lahir bintang baru (nebula emisi), sisa ledakan bintang "
        "(nebula supernova), atau sekadar awan debu yang menghalangi cahaya "
        "(nebula gelap)."
    ),
    "planets": (
        "Planet adalah benda langit yang mengorbit bintang, berbentuk hampir "
        "bulat karena gravitasinya sendiri, dan sudah membersihkan orbitnya. "
        "Contoh dalam tata surya: Mars, Jupiter, Saturnus."
    ),
    "constellation": (
        "Konstelasi adalah kumpulan bintang di langit yang dilihat membentuk "
        "pola tertentu dari bumi, misalnya Orion, Ursa Major, atau Cassiopeia. "
        "Bintang-bintangnya tidak benar-benar berdekatan di ruang angkasa."
    ),
    "cosmos_space": (
        "Gambar dari kategori ruang angkasa luas: pemandangan langit, deep field, "
        "atau foto astronomi yang menampilkan banyak objek. Biasanya diambil "
        "oleh teleskop luar angkasa atau astrofotografer."
    ),
}

FITS_SCOPE_NOTE = (
    "Model FITS ini dilatih membedakan 2 kelas saja: bintang vs galaksi. "
    "Hasil di luar itu (nebula, planet, dll) belum didukung model ini."
)

app = FastAPI(title="Astro Classifier API")

# CORS dibuka biar frontend (React/Next.js) di domain/port lain bisa akses API ini.
# Kalau udah deploy, ganti allow_origins=["*"] jadi domain frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asset frontend statis (mis. generator "Your Cosmic Card").
app.mount("/static", StaticFiles(directory="static"), name="static")

print("Loading model...")
model = keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH) as f:
    CLASS_NAMES = [line.strip() for line in f if line.strip()]

print("Model siap. Kelas:", CLASS_NAMES)

print("Loading FITS model...")
fits_model = keras.models.load_model(FITS_MODEL_PATH)

with open(FITS_CLASS_NAMES_PATH) as f:
    _fits_names = [line.strip() for line in f if line.strip()]

print("Model FITS siap. Kelas:", _fits_names)


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img, dtype=np.float32)
    arr = keras.applications.efficientnet.preprocess_input(arr)
    return np.expand_dims(arr, axis=0)  # jadi batch of 1


def is_fits_file(filename: str) -> bool:
    return (filename or "").strip().lower().endswith(ALLOWED_FITS_SUFFIXES)


@app.get("/")
def read_index():
    return FileResponse("index.html")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "classes": CLASS_NAMES,
        "fits_classes": FITS_CLASS_NAMES,
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Format '{file.content_type}' belum didukung. Pakai JPG, PNG, atau WEBP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File terlalu besar. Maksimal 25 MB.",
        )
    try:
        x = preprocess_image(image_bytes)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Gagal membaca gambar. Pastikan filenya gambar yang valid.",
        )

    preds = model.predict(x, verbose=0)[0]  # shape: (6,)
    top3_idx = np.argsort(preds)[::-1][:3]
    top3 = [
        {
            "label": CLASS_NAMES[i],
            "confidence": round(float(preds[i]), 4),
            "explanation": EXPLANATIONS.get(CLASS_NAMES[i], ""),
        }
        for i in top3_idx
    ]

    return {"prediction": top3[0], "top3": top3}


@app.post("/predict_fits")
async def predict_fits(file: UploadFile = File(...)):
    if not is_fits_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Format belum didukung. Upload file FITS (.fits / .fit / .fits.gz).",
        )

    fits_bytes = await file.read()
    if len(fits_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File terlalu besar. Maksimal 25 MB.",
        )
    try:
        x, quality = fits_utils.preprocess_fits(fits_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file FITS: {e}",
        )

    p_galaxy = float(fits_model.predict(x, verbose=0)[0][0])
    p_star = 1.0 - p_galaxy
    label = FITS_CLASS_NAMES[1] if p_galaxy >= 0.5 else FITS_CLASS_NAMES[0]

    # Peringatan reliabilitas: data yang banyak NaN / tersaturasi berada di
    # luar sebaran data latih, jadi prediksinya kemungkinan besar tidak akurat.
    warnings = []
    if quality["nan_fraction"] > 0.2:
        warnings.append(
            f"{quality['nan_fraction'] * 100:.1f}% piksel tidak valid (NaN). "
            "Data seperti ini di luar sebaran data latih — hasil klasifikasi "
            "kemungkinan besar tidak akurat."
        )
    if quality["saturated"]:
        warnings.append(
            "Terdeteksi saturasi: objek terang bisa tampak melebar (extended) "
            "sehingga bintang mudah tertukar sebagai galaksi."
        )

    return {
        "warnings": warnings,
        "prediction": {
            "label": label,
            "confidence": round(max(p_star, p_galaxy), 4),
            "explanation": EXPLANATIONS.get(label, ""),
        },
        "probabilities": {
            "star": round(p_star, 4),
            "galaxy": round(p_galaxy, 4),
        },
        "quality": quality,
        "note": FITS_SCOPE_NOTE,
    }


@app.post("/fits_preview")
async def fits_preview(
    file: UploadFile = File(...),
    size: int = Query(300, ge=64, le=1200),
):
    if not is_fits_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Format belum didukung. Upload file FITS (.fits / .fit / .fits.gz).",
        )

    fits_bytes = await file.read()
    if len(fits_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File terlalu besar. Maksimal 25 MB.",
        )
    try:
        png = fits_utils.render_preview(fits_bytes, size=size)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal merender preview: {e}")

    return Response(content=png, media_type="image/png")

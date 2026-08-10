"""
Phase 2 - FastAPI backend serving the classifier model through the /predict endpoint.

Usage:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs to try uploading an image straight from the
browser (Swagger UI is generated automatically by FastAPI).

Files that must sit alongside main.py:
    best_model.keras             (6-class model: images)
    class_names.txt
    fits_star_galaxy_model.keras (2-class model: star vs galaxy from FITS)
    fits_class_names.txt

Endpoints:
    GET  /            -> health check
    POST /predict     -> image classification (JPG/PNG/WEBP, 6 classes)
    POST /predict_fits-> FITS classification (star/galaxy)
    POST /fits_preview-> render a PNG preview from a FITS file
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
        "A star is a hot ball of gas (mostly hydrogen and helium) that emits "
        "light through nuclear fusion in its core. In telescope images, a star "
        "appears as a sharp point source, since its light is concentrated in "
        "just a few pixels."
    ),
    "galaxy": (
        "A galaxy is a massive system containing billions of stars, gas, dust, "
        "and dark matter bound together by gravity. In telescope images, a "
        "galaxy appears wider and more extended than a star, with a bright "
        "core and light that fades toward the edges."
    ),
    "stars": (
        "A star is a hot ball of gas that emits light through nuclear fusion "
        "in its core. This class covers images of individual stars or star "
        "clusters that appear as bright points of light."
    ),
    "galaxies": (
        "A galaxy is a giant collection of stars, gas, dust, and dark matter "
        "bound together by gravity. Examples: the Milky Way, Andromeda. "
        "Shapes vary widely — spiral, elliptical, or irregular."
    ),
    "nebula": (
        "A nebula is a vast interstellar cloud of gas and dust. Some are "
        "stellar nurseries where new stars are born (emission nebulae), "
        "others are the remnants of stellar explosions (supernova nebulae), "
        "or simply dust clouds blocking light (dark nebulae)."
    ),
    "planets": (
        "A planet is a celestial body that orbits a star, is nearly spherical "
        "due to its own gravity, and has cleared its orbital neighborhood. "
        "Examples in our solar system: Mars, Jupiter, Saturn."
    ),
    "constellation": (
        "A constellation is a group of stars in the sky that, seen from Earth, "
        "appears to form a recognizable pattern — for example Orion, Ursa "
        "Major, or Cassiopeia. The stars aren't actually close together in space."
    ),
    "cosmos_space": (
        "Images from the broad deep-space category: sweeping sky views, deep "
        "fields, or astronomical photos featuring many objects at once. "
        "Usually captured by space telescopes or astrophotographers."
    ),
}

FITS_SCOPE_NOTE = (
    "This FITS model is trained to distinguish only 2 classes: star vs "
    "galaxy. Results outside that (nebula, planet, etc.) are not supported "
    "by this model."
)

app = FastAPI(title="Astro Classifier API")

# CORS is left open so a frontend (React/Next.js) on another domain/port can call this API.
# Once deployed, replace allow_origins=["*"] with the frontend's actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static frontend assets (e.g. the "Your Cosmic Card" generator).
app.mount("/static", StaticFiles(directory="static"), name="static")

print("Loading model...")
model = keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH) as f:
    CLASS_NAMES = [line.strip() for line in f if line.strip()]

print("Model ready. Classes:", CLASS_NAMES)

print("Loading FITS model...")
fits_model = keras.models.load_model(FITS_MODEL_PATH)

with open(FITS_CLASS_NAMES_PATH) as f:
    _fits_names = [line.strip() for line in f if line.strip()]

print("FITS model ready. Classes:", _fits_names)


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img, dtype=np.float32)
    arr = keras.applications.efficientnet.preprocess_input(arr)
    return np.expand_dims(arr, axis=0)  # turn into a batch of 1


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
            detail=f"Format '{file.content_type}' is not supported. Use JPG, PNG, or WEBP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 25 MB.",
        )
    try:
        x = preprocess_image(image_bytes)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to read the image. Make sure the file is a valid image.",
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
            detail="Format not supported. Upload a FITS file (.fits / .fit / .fits.gz).",
        )

    fits_bytes = await file.read()
    if len(fits_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 25 MB.",
        )
    try:
        x, quality = fits_utils.preprocess_fits(fits_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read the FITS file: {e}",
        )

    p_galaxy = float(fits_model.predict(x, verbose=0)[0][0])
    p_star = 1.0 - p_galaxy
    label = FITS_CLASS_NAMES[1] if p_galaxy >= 0.5 else FITS_CLASS_NAMES[0]

    # Reliability warnings: data with a lot of NaN / saturation falls outside
    # the training distribution, so the prediction is likely inaccurate.
    warnings = []
    if quality["nan_fraction"] > 0.2:
        warnings.append(
            f"{quality['nan_fraction'] * 100:.1f}% of pixels are invalid (NaN). "
            "Data like this falls outside the training distribution — the "
            "classification result is likely inaccurate."
        )
    if quality["saturated"]:
        warnings.append(
            "Saturation detected: bright objects can appear extended, which "
            "can cause a star to be misclassified as a galaxy."
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
            detail="Format not supported. Upload a FITS file (.fits / .fit / .fits.gz).",
        )

    fits_bytes = await file.read()
    if len(fits_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 25 MB.",
        )
    try:
        png = fits_utils.render_preview(fits_bytes, size=size)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to render preview: {e}")

    return Response(content=png, media_type="image/png")

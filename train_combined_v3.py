"""
Train a fresh star/galaxy CNN from scratch using THREE data sources:

1. Real Kaggle data (JPG cutout files from archive.zip)
2. Synthetic realistic data (PSF-convolved, noisy, in-memory)
3. Workshop-style clean data (Gaussian2D / Sersic2D without noise, in-memory)

All data is balanced 50:50 (star:galaxy) and all data is kept in memory to
avoid disk I/O for thousands of FITS files.

Output: fits_star_galaxy_model.keras (overwrites the existing one)
"""
import csv
import io
import os
import zipfile

import numpy as np
import tensorflow as tf
from astropy.io import fits
from astropy.modeling.functional_models import Gaussian2D, Moffat2D, Sersic2D
from astropy.stats import sigma_clipped_stats
from PIL import Image
from scipy import ndimage
from tensorflow import keras

ARCHIVE_ZIP = "archive.zip"
MODEL_PATH = "fits_star_galaxy_model.keras"
CLASS_NAMES_PATH = "fits_class_names.txt"
IMG_SIZE = 64
STAMP_SIZE = 300
SEED = 42


# ─── Preprocessing (must match fits_utils for inference consistency) ──────────

def normalize_fits(data):
    arr = data.astype(np.float32)
    if arr.size == 0:
        return arr
    median, _, _ = sigma_clipped_stats(arr, sigma=3.0, maxiters=5)
    sky = float(median) if np.isfinite(median) else 0.0
    sub = arr - sky
    lo, hi = np.percentile(sub, (1.0, 99.5))
    if not np.isfinite(hi) or hi - lo < 1e-6:
        return np.zeros_like(arr)
    return np.clip((sub - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def to_model_input(data, size=IMG_SIZE):
    norm = normalize_fits(data)
    img = Image.fromarray((norm * 255.0).astype(np.uint8), mode="L")
    img = img.resize((size, size), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return np.stack([arr, arr, arr], axis=-1)


# ─── Kaggle real data (JPG stamps) ─────────────────────────────────────────────

def load_kaggle_data(archive_path, max_per_class=942):
    """Load JPG cutouts from archive.zip, balanced star/galaxy."""
    X, y = [], []
    stars, galaxies = [], []
    with zipfile.ZipFile(archive_path, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".jpg"):
                continue
            label = None
            if "star" in name.lower():
                label = 0
                target_list = stars
            elif "galaxy" in name.lower():
                label = 1
                target_list = galaxies
            else:
                continue
            if len(target_list) >= max_per_class:
                continue
            raw = zf.read(name)
            img = Image.open(io.BytesIO(raw)).convert("L")
            arr = np.asarray(img, dtype=np.float32)
            inp = to_model_input(arr)
            target_list.append(inp)
    min_n = min(len(stars), len(galaxies))
    rng = np.random.default_rng(SEED)
    rng.shuffle(stars)
    rng.shuffle(galaxies)
    X = stars[:min_n] + galaxies[:min_n]
    y = [0] * min_n + [1] * min_n
    print(f"  kaggle: {len(stars)} stars, {len(galaxies)} galaxies, using {min_n} each")
    return np.stack(X), np.asarray(y, dtype=np.int32)


# ─── Synthetic realistic stamps (like generate_dataset.py) ────────────────────

def make_psf_kernel(size, fwhm, rng, moffat_prob=0.35):
    c = (size - 1) / 2
    y, x = np.mgrid[0:size, 0:size]
    if rng.random() < moffat_prob:
        alpha = 2.5
        gamma = fwhm / (2 * np.sqrt(2 ** (1 / alpha) - 1))
        psf = (1 + ((x - c) ** 2 + (y - c) ** 2) / gamma**2) ** (-alpha)
    else:
        sigma = fwhm / 2.35482
        psf = np.exp(-((x - c) ** 2 + (y - c) ** 2) / (2 * sigma**2))
    return psf / psf.sum()


def generate_realistic_stamp(size, rng):
    y, x = np.mgrid[0:size, 0:size]
    cx = rng.uniform(60, size - 60)
    cy = rng.uniform(60, size - 60)
    fwhm = rng.uniform(2.0, 7.0)
    is_star = rng.random() < 0.5
    if is_star:
        amp = rng.uniform(300, 3000)
        if rng.random() < 0.35:
            alpha = 2.5
            gamma = fwhm / (2 * np.sqrt(2 ** (1 / alpha) - 1))
            obj = Moffat2D(amplitude=amp, x_0=cx, y_0=cy, gamma=gamma, alpha=alpha)(x, y)
        else:
            sigma = fwhm / 2.35482
            obj = Gaussian2D(amplitude=amp, x_mean=cx, y_mean=cy,
                             x_stddev=sigma, y_stddev=sigma)(x, y)
        label = 0
    else:
        amp = rng.uniform(50, 1500)
        r_eff = rng.uniform(5, 35)
        nn = rng.uniform(0.5, 4.5)
        ellip = rng.uniform(0.0, 0.7)
        theta = rng.uniform(0, np.pi)
        obj = Sersic2D(amplitude=amp, r_eff=r_eff, n=nn, x_0=cx, y_0=cy,
                       theta=theta, ellip=ellip)(x, y)
        psf = make_psf_kernel(15, fwhm, rng)
        obj = ndimage.convolve(obj, psf, mode="constant", cval=0.0)
        label = 1
    sky = rng.uniform(100, 400)
    img = obj + sky
    readout_noise = rng.uniform(2, 10)
    img = img + rng.normal(0.0, readout_noise, size=(size, size))
    gradient = rng.uniform(-0.15, 0.15) * sky
    img = img + gradient * (x / size - 0.5)
    for _ in range(rng.integers(0, 4)):
        for _ in range(int(rng.integers(1, 4))):
            rr, cc = int(rng.integers(0, size)), int(rng.integers(0, size))
            img[rr, cc] = rng.uniform(800, 5000)
    for _ in range(rng.integers(0, 40)):
        rr, cc = int(rng.integers(0, size)), int(rng.integers(0, size))
        img[rr, cc] = 0.0
    return np.asarray(img, dtype=np.float32), label


def generate_workshop_stamp(size, rng):
    y, x = np.mgrid[0:size, 0:size]
    margin = size * 0.27
    cx = rng.uniform(margin, size - margin)
    cy = rng.uniform(margin, size - margin)
    is_star = rng.random() < 0.5
    if is_star:
        amp = rng.uniform(1.0, 15.0)
        stddev = rng.uniform(2.0, 12.0)
        obj = Gaussian2D(amplitude=amp, x_mean=cx, y_mean=cy,
                         x_stddev=stddev, y_stddev=stddev)(x, y)
        label = 0
    else:
        amp = rng.uniform(0.1, 2.0)
        r_eff = rng.uniform(15.0, 70.0)
        nn = rng.uniform(1.0, 6.0)
        ellip = rng.uniform(0.0, 0.7)
        theta = rng.uniform(0, np.pi)
        obj = Sersic2D(amplitude=amp, r_eff=r_eff, n=nn, x_0=cx, y_0=cy,
                       theta=theta, ellip=ellip)(x, y)
        label = 1
    img = obj.astype(np.float64)
    if rng.random() >= 0.55:
        sky = rng.uniform(0.0, 0.3) * max(amp, 0.1)
        img = img + sky
        noise_sigma = rng.uniform(0.0, 0.06) * max(amp, 0.1)
        if noise_sigma > 0:
            img = img + rng.normal(0.0, noise_sigma, size=(size, size))
    return np.asarray(img, dtype=np.float32), label


def load_synthetic(n_samples, style="realistic", seed=SEED):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for _ in range(n_samples):
        if style == "workshop":
            img, label = generate_workshop_stamp(STAMP_SIZE, rng)
        else:
            img, label = generate_realistic_stamp(STAMP_SIZE, rng)
        X.append(to_model_input(img))
        y.append(label)
    return np.stack(X), np.asarray(y, dtype=np.int32)


# ─── Training ──────────────────────────────────────────────────────────────────

def build_model(input_shape=(64, 64, 3)):
    model = keras.Sequential([
        keras.Input(shape=input_shape),
        keras.layers.RandomFlip("horizontal"),
        keras.layers.RandomContrast(0.1),
        keras.layers.Conv2D(32, 3, activation="relu", padding="same"),
        keras.layers.BatchNormalization(),
        keras.layers.MaxPooling2D(),
        keras.layers.Conv2D(64, 3, activation="relu", padding="same"),
        keras.layers.BatchNormalization(),
        keras.layers.MaxPooling2D(),
        keras.layers.Conv2D(128, 3, activation="relu", padding="same"),
        keras.layers.BatchNormalization(),
        keras.layers.MaxPooling2D(),
        keras.layers.GlobalAveragePooling2D(),
        keras.layers.Dropout(0.4),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(3e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def stratified_split(y, val_frac=0.2, seed=0):
    rng = np.random.default_rng(seed)
    train_idx, val_idx = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        n_val = max(1, int(len(idx) * val_frac))
        val_idx.extend(idx[:n_val])
        train_idx.extend(idx[n_val:])
    return np.asarray(train_idx), np.asarray(val_idx)


def main():
    print("Loading real (Kaggle) data...")
    X_real, y_real = load_kaggle_data(ARCHIVE_ZIP)
    n_real = len(X_real)

    print("Generating realistic synthetic data (1000 stamps)...")
    X_syn, y_syn = load_synthetic(1000, style="realistic")
    n_syn = len(X_syn)

    print("Generating workshop-style synthetic data (1200 stamps)...")
    X_ws, y_ws = load_synthetic(1200, style="workshop", seed=SEED + 1)
    n_ws = len(X_ws)

    X = np.concatenate([X_real, X_syn, X_ws], axis=0)
    y = np.concatenate([y_real, y_syn, y_ws], axis=0)
    print(f"Combined: {len(X)} samples  y dist: {np.bincount(y)}")

    train_idx, val_idx = stratified_split(y, val_frac=0.2)
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"Train: {len(train_idx)}  Val: {len(val_idx)}")

    model = build_model()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=10, restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6
        ),
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=60,
        batch_size=32,
        callbacks=callbacks,
        verbose=1,
    )

    model.save(MODEL_PATH)
    with open(CLASS_NAMES_PATH, "w") as f:
        f.write("star\ngalaxy\n")

    probs = model.predict(X_val, verbose=0)[:, 0]
    preds = (probs >= 0.5).astype(int)
    acc = float((preds == y_val).mean())
    print(f"\nVal accuracy: {acc:.4f}")
    for cls, name in [(0, "star"), (1, "galaxy")]:
        mask = y_val == cls
        acc_cls = float((preds[mask] == y_val[mask]).mean())
        print(f"  {name:7s}: {acc_cls:.4f}  (n={mask.sum()})")

    print(f"\nModel saved: {MODEL_PATH}")

    print("\n--- Evaluating on example FITS files ---")
    example_files = [
        ("elliptical_galaxy.fits", 1),
        ("mock_star_image.fits", 0),
    ]
    for fname, expected in example_files:
        path = os.path.join(".", fname)
        if not os.path.exists(path):
            print(f"  {fname}: not found, skipping")
            continue
        with fits.open(path, memmap=False) as hdul:
            data = np.asarray(hdul[0].data, dtype=np.float32)
        inp = np.expand_dims(to_model_input(data), axis=0)
        prob = float(model.predict(inp, verbose=0)[0, 0])
        pred = "galaxy" if prob >= 0.5 else "star"
        expected_name = "galaxy" if expected == 1 else "star"
        correct = "OK" if pred == expected_name else "WRONG"
        print(f"  {fname}: pred={pred} (prob_galaxy={prob:.4f}) expected={expected_name} [{correct}]")


if __name__ == "__main__":
    main()
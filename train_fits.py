"""
Latih CNN biner bintang vs galaksi dari dataset FITS.

Cara pakai:
    python train_fits.py            # pakai classification_dataset/ + classification_labels.csv
    python train_fits.py --epochs 40 --batch 32

Output:
    fits_star_galaxy_model.keras
    fits_class_names.txt            # star, galaxy
"""
import argparse
import os

import numpy as np
import pandas as pd
import tensorflow as tf
from astropy.io import fits
from tensorflow import keras

import fits_utils

MODEL_PATH = "fits_star_galaxy_model.keras"
CLASS_NAMES_PATH = "fits_class_names.txt"
DATA_DIR = "classification_dataset"
LABELS_CSV = "classification_labels.csv"


def load_dataset(data_dir, labels_csv):
    df = pd.read_csv(labels_csv)
    X, y, names = [], [], []
    for _, row in df.iterrows():
        path = os.path.join(data_dir, row["filename"])
        with fits.open(path, memmap=False) as hdul:
            data = np.asarray(hdul[0].data, dtype=np.float32)
        inp = fits_utils.to_model_input(data)
        X.append(inp)
        y.append(int(row["label"]))
        names.append(row["filename"])
    return np.stack(X), np.asarray(y, dtype=np.int32), names


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


def build_model(input_shape=(64, 64, 3)):
    model = keras.Sequential(
        [
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
        ]
    )
    model.compile(
        optimizer=keras.optimizers.Adam(3e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--labels-csv", default=LABELS_CSV)
    args = parser.parse_args()

    print("Memuat dataset FITS...")
    X, y, names = load_dataset(args.data_dir, args.labels_csv)
    print(f"Total sampel: {X.shape[0]}, shape: {X.shape[1:]}")

    train_idx, val_idx = stratified_split(y, args.val_frac)
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"Train: {len(train_idx)}, Val: {len(val_idx)}")

    model = build_model(X.shape[1:])
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch,
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

    wrong = np.where(preds != y_val)[0]
    if len(wrong):
        rng = np.random.default_rng(1)
        sample = rng.choice(wrong, size=min(5, len(wrong)), replace=False)
        print("\nContoh salah klasifikasi (file, label asli, label prediksi):")
        for i in sample:
            print(f"  {names[val_idx[i]]}: asli={y_val[i]} pred={preds[i]}")
    else:
        print("\nTidak ada salah klasifikasi di validation set.")
    print(f"\nModel disimpan: {MODEL_PATH}")


if __name__ == "__main__":
    main()

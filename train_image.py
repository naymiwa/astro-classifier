"""
Fase 1 - Training classifier gambar 6 kelas benda langit dari dataset Kaggle
(Astronomy Image Classification Dataset).

Cara pakai:
    python train_image.py
    python train_image.py --epochs 20 --fine-epochs 10 --batch 16
    python train_image.py --data-dir "space images" --epochs 25

Dataset: folder per kelas berisi JPG. Nama folder otomatis dipakai jadi label,
urutan kelas diambil dari sort nama folder supaya konsisten dengan class_names.txt:
    constellation, cosmos_space, galaxies, nebula, planets, stars

Output:
    best_model.keras      (EfficientNetB0 fine-tuned, 6 kelas)
    class_names.txt       (urutan kelas = urutan output model, index i -> CLASS_NAMES[i])
"""
import argparse
import os
import re

import numpy as np
import tensorflow as tf
from tensorflow import keras

IMG_SIZE = (224, 224)
DATA_DIR = "space images"
MODEL_PATH = "best_model.keras"
CLASS_NAMES_PATH = "class_names.txt"
SEED = 42
SUFFIX_RE = re.compile(r"\s*-\s*Google Search\s*$", re.IGNORECASE)


def folder_to_class(folder_name: str) -> str:
    """Ubah nama folder dataset jadi nama kelas yang rapi."""
    name = SUFFIX_RE.sub("", folder_name).strip()
    return name.replace(" ", "_").lower()


def list_classes(data_dir: str):
    """Kumpulkan nama kelas dari subfolder (urutan alfabetis = urutan output model)."""
    folders = sorted(
        d
        for d in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, d))
    )
    classes = [folder_to_class(f) for f in folders]
    return folders, classes


def decode_image(path, label, augment):
    """Baca gambar -> resize 224x224 -> augment? -> EfficientNet preprocess_input.

    decode_image tanpa `channels` biar gambar indexed-color/palette PNG tetap lolos.
    Channel count dinormalisasi manual ke 3 (grayscale -> RGB, RGBA -> drop alpha).
    expand_animations=False supaya gambar animasi gak kasih dimensi frame ekstra.
    """
    raw = tf.io.read_file(path)
    img = tf.io.decode_image(raw, expand_animations=False)
    img = tf.cond(
        tf.equal(tf.shape(img)[-1], 1),
        lambda: tf.image.grayscale_to_rgb(img),
        lambda: img[..., :3],
    )
    img.set_shape([None, None, 3])
    img = tf.image.resize(img, IMG_SIZE)
    if augment:
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_flip_up_down(img)
        img = tf.image.random_brightness(img, max_delta=0.15)
        img = tf.image.random_contrast(img, lower=0.85, upper=1.15)
        img = tf.image.random_saturation(img, lower=0.9, upper=1.1)
    img = keras.applications.efficientnet.preprocess_input(img)
    return img, label


def make_datasets(data_dir, folders, batch_size, val_frac):
    """Bangun tf.data pipeline + split stratified per kelas."""
    filepaths, labels = [], []
    for label_idx, folder in enumerate(folders):
        full = os.path.join(data_dir, folder)
        for fn in os.listdir(full):
            if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                filepaths.append(os.path.join(full, fn))
                labels.append(label_idx)
    filepaths = np.array(filepaths)
    labels = np.array(labels, dtype=np.int32)
    print(f"Total gambar: {len(filepaths)}")

    rng = np.random.default_rng(SEED)
    train_idx, val_idx = [], []
    for cls in np.unique(labels):
        idx = np.where(labels == cls)[0]
        rng.shuffle(idx)
        n_val = max(1, int(len(idx) * val_frac))
        val_idx.extend(idx[:n_val])
        train_idx.extend(idx[n_val:])
    train_idx, val_idx = np.array(train_idx), np.array(val_idx)
    print(f"Train: {len(train_idx)}, Val: {len(val_idx)}")

    def load_train(path, label):
        return decode_image(path, label, augment=True)

    def load_val(path, label):
        return decode_image(path, label, augment=False)

    train_ds = (
        tf.data.Dataset.from_tensor_slices(
            (filepaths[train_idx], labels[train_idx])
        )
        .shuffle(min(2000, len(train_idx)), seed=SEED)
        .map(load_train, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )
    val_ds = (
        tf.data.Dataset.from_tensor_slices(
            (filepaths[val_idx], labels[val_idx])
        )
        .map(load_val, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )
    return train_ds, val_ds


def build_model(n_classes):
    """EfficientNetB0 (ImageNet) + head baru. Base awalnya dibekukan."""
    base = keras.applications.EfficientNetB0(
        include_top=False, weights="imagenet", input_shape=IMG_SIZE + (3,)
    )
    base.trainable = False

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = base(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(n_classes, activation="softmax")(x)
    model = keras.Model(inputs, outputs)
    return model, base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--fine-epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--fine-lr", type=float, default=1e-4)
    parser.add_argument("--no-finetune", action="store_true")
    parser.add_argument("--out", default=MODEL_PATH)
    args = parser.parse_args()

    tf.random.set_seed(SEED)
    np.random.seed(SEED)

    folders, class_names = list_classes(args.data_dir)
    print("Kelas (urutan output model):", class_names)
    assert len(class_names) == 6, f"Expected 6 classes, got {len(class_names)}"

    train_ds, val_ds = make_datasets(
        args.data_dir, folders, args.batch, args.val_frac
    )

    model, base = build_model(len(class_names))
    model.compile(
        optimizer=keras.optimizers.Adam(args.lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    print("\n=== Fase 1: train head only (base dibekukan) ===")
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs)

    if not args.no_finetune:
        print("\n=== Fase 2: fine-tune (buka 30 layer terakhir EfficientNet) ===")
        base.trainable = True
        for layer in base.layers[:-30]:
            layer.trainable = False
        model.compile(
            optimizer=keras.optimizers.Adam(args.fine_lr),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        model.fit(train_ds, validation_data=val_ds, epochs=args.fine_epochs)

    model.save(args.out)
    with open(CLASS_NAMES_PATH, "w") as f:
        f.write("\n".join(class_names) + "\n")
    print(f"\nModel disimpan: {args.out}")
    print(f"Class names -> {CLASS_NAMES_PATH} (urutan: {class_names})")

    y_true, y_pred = [], []
    for x, y in val_ds:
        p = model.predict(x, verbose=0)
        y_true.extend(y.numpy().tolist())
        y_pred.extend(np.argmax(p, axis=1).tolist())
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    acc = float((y_pred == y_true).mean())
    print(f"\nVal accuracy: {acc:.4f}")
    for i, name in enumerate(class_names):
        mask = y_true == i
        if mask.sum():
            acc_cls = float((y_pred[mask] == y_true[mask]).mean())
            print(f"  {name:15s}: {acc_cls:.4f} (n={int(mask.sum())})")

    cm = tf.math.confusion_matrix(y_true, y_pred, num_classes=len(class_names)).numpy()
    print("\nConfusion matrix (baris=asli, kolom=prediksi):")
    header = "          " + " ".join(f"{n[:7]:>8s}" for n in class_names)
    print(header)
    for i, name in enumerate(class_names):
        row = " ".join(f"{v:8d}" for v in cm[i])
        print(f"{name[:10]:10s} {row}")


if __name__ == "__main__":
    main()
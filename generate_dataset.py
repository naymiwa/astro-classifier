"""
Generate dataset FITS klasifikasi bintang vs galaksi.

Berbeda dari versi awal (Untitled3.ipynb), dataset ini dibuat meniru observasi
teleskop sungguhan supaya CNN yang dilatih bisa generalisasi ke data asli:

    - Bintang  : sumber titik (PSF) -> profil Gaussian/Moffat, FWHM = PSF teleskop.
    - Galaksi  : profil Sersic2D yang DIKONVOLUSI PSF yang sama (terlihat kabur
                 seperti lewat teleskop).
    - Ditambah sky background, readout noise, cosmic rays, bad pixels, dan
                 gradien flat-field ringan.
    - Variasi pixel scale lewat rentang FWHM dan r_eff.

Output: classification_dataset/img_XXXX.fits + classification_labels.csv
(label 0 = star, 1 = galaxy).
"""
import argparse
import os

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.modeling.functional_models import Gaussian2D, Moffat2D, Sersic2D
from scipy import ndimage


def make_psf_kernel(size, fwhm, rng, moffat_prob=0.35):
    """Kernel PSF 2D berpusat (normalisasi total flux = 1)."""
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


def generate_stamp(size, rng):
    """Buat satu stamp FITS (array 2D) berisi satu objek + realisme teleskop."""
    y, x = np.mgrid[0:size, 0:size]

    cx = rng.uniform(60, size - 60)
    cy = rng.uniform(60, size - 60)
    fwhm = rng.uniform(2.0, 7.0)  # pixel scale bervariasi

    is_star = rng.random() < 0.5

    if is_star:
        amp = rng.uniform(300, 3000)
        if rng.random() < 0.35:
            alpha = 2.5
            gamma = fwhm / (2 * np.sqrt(2 ** (1 / alpha) - 1))
            star = Moffat2D(amplitude=amp, x_0=cx, y_0=cy, gamma=gamma, alpha=alpha)
            obj = star(x, y)
        else:
            sigma = fwhm / 2.35482
            star = Gaussian2D(amplitude=amp, x_mean=cx, y_mean=cy,
                              x_stddev=sigma, y_stddev=sigma)
            obj = star(x, y)
        label = 0
        class_name = "star"
    else:
        amp = rng.uniform(50, 1500)
        r_eff = rng.uniform(5, 35)
        n = rng.uniform(0.5, 4.5)
        ellip = rng.uniform(0.0, 0.7)
        theta = rng.uniform(0, np.pi)
        galaxy = Sersic2D(amplitude=amp, r_eff=r_eff, n=n, x_0=cx, y_0=cy,
                          theta=theta, ellip=ellip)
        obj = galaxy(x, y)
        psf = make_psf_kernel(15, fwhm, rng)
        obj = ndimage.convolve(obj, psf, mode="constant", cval=0.0)
        label = 1
        class_name = "galaxy"

    sky = rng.uniform(100, 400)
    img = obj + sky

    readout_noise = rng.uniform(2, 10)
    img = img + rng.normal(0.0, readout_noise, size=(size, size))

    gradient = rng.uniform(-0.15, 0.15) * sky
    img = img + gradient * (x / size - 0.5)

    for _ in range(rng.integers(0, 4)):
        n_rays = int(rng.integers(1, 4))
        for _ in range(n_rays):
            rr = int(rng.integers(0, size))
            cc = int(rng.integers(0, size))
            img[rr, cc] = rng.uniform(800, 5000)

    for _ in range(rng.integers(0, 40)):
        rr = int(rng.integers(0, size))
        cc = int(rng.integers(0, size))
        img[rr, cc] = 0.0

    return np.asarray(img, dtype=np.float32), label, class_name


def generate_workshop_stamp(size, rng):
    """Buat satu stamp gaya notebook workshop (Astronomical_Simulate.ipynb):
    Gaussian2D murni untuk bintang, Sersic2D murni untuk galaksi, TANPA PSF
    convolution. Sebagian kecil sampel dibuat 100% bersih (persis kode
    notebook: tanpa sky background, tanpa noise sama sekali) supaya model
    kenal gaya ini; sisanya dikasih sedikit noise/background ringan supaya
    tidak terlalu sempit sebarannya. Parameter di-random di sekitar nilai
    contoh di notebook (amplitude=5, x_stddev=5 utk bintang;
    amplitude=0.5, r_eff=50, n=5, ellip=0.5 utk galaksi).
    """
    y, x = np.mgrid[0:size, 0:size]
    margin = size * 0.27  # notebook: objek sekitar 1/3 - 2/3 kanvas
    cx = rng.uniform(margin, size - margin)
    cy = rng.uniform(margin, size - margin)

    is_star = rng.random() < 0.5

    if is_star:
        amp = rng.uniform(1.0, 15.0)
        stddev = rng.uniform(2.0, 12.0)
        star = Gaussian2D(amplitude=amp, x_mean=cx, y_mean=cy,
                           x_stddev=stddev, y_stddev=stddev)
        obj = star(x, y)
        label = 0
        class_name = "star"
    else:
        amp = rng.uniform(0.1, 2.0)
        r_eff = rng.uniform(15.0, 70.0)
        n = rng.uniform(1.0, 6.0)
        ellip = rng.uniform(0.0, 0.7)
        theta = rng.uniform(0, np.pi)
        galaxy = Sersic2D(amplitude=amp, r_eff=r_eff, n=n, x_0=cx, y_0=cy,
                           theta=theta, ellip=ellip)
        obj = galaxy(x, y)
        label = 1
        class_name = "galaxy"

    img = obj.astype(np.float64)

    # ~55% sampel dibiarkan 100% bersih (persis notebook: nol noise, nol
    # background) -- sisanya dikasih sedikit realisme ringan biar tidak
    # semuanya identik gaya "buku teks".
    if rng.random() >= 0.55:
        sky = rng.uniform(0.0, 0.3) * max(amp, 0.1)
        img = img + sky
        noise_sigma = rng.uniform(0.0, 0.06) * max(amp, 0.1)
        if noise_sigma > 0:
            img = img + rng.normal(0.0, noise_sigma, size=(size, size))

    return np.asarray(img, dtype=np.float32), label, class_name


def main():
    parser = argparse.ArgumentParser(description="Generate dataset FITS star/galaxy.")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", default="classification_dataset")
    parser.add_argument(
        "--style",
        choices=["realistic", "workshop", "mixed"],
        default="realistic",
        help=(
            "realistic = PSF+noise ala observasi teleskop (default); "
            "workshop = gaya Astronomical_Simulate.ipynb (Gaussian2D/Sersic2D "
            "polos, sering tanpa noise); mixed = campuran acak keduanya."
        ),
    )
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    labels_data = []
    for i in range(args.count):
        if args.style == "workshop":
            use_workshop = True
        elif args.style == "mixed":
            use_workshop = rng.random() < 0.5
        else:
            use_workshop = False

        if use_workshop:
            img, label, class_name = generate_workshop_stamp(args.size, rng)
        else:
            img, label, class_name = generate_stamp(args.size, rng)
        filename = f"img_{i:04d}.fits"
        fits.writeto(os.path.join(args.outdir, filename), img, overwrite=True)
        labels_data.append({"filename": filename, "label": label, "class_name": class_name})

    df = pd.DataFrame(labels_data)
    df.to_csv("classification_labels.csv", index=False)
    print(f"Dataset selesai: {args.count} FITS di '{args.outdir}' + classification_labels.csv")
    print(df["class_name"].value_counts().to_string())


if __name__ == "__main__":
    main()

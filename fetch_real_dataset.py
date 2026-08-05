"""
Ambil dataset FITS asli star/galaxy dari Legacy Surveys DR9.

Sumber:
    - https://www.legacysurvey.org/viewer/ls-dr9/<z>/<x>/<y>.cat.json
      (header Accept: application/json)
      Isi: rd[] = [ra, dec], sourcetype[] = 'P' (PSF=star),
           'R' (REX), 'E' (EXP), 'D' (DEV), 'S' (DUP, skip)
    - https://www.legacysurvey.org/viewer/cutout.fits?ra=..&dec=..&size=64
      &layer=ls-dr9&pixscale=0.262&bands=r  (single-band r, 64x64 float32)

Label: 0 = star (PSF), 1 = galaxy (REX/EXP/DEV). Skip 'S' (duplikaat).

Cara pakai:
    python fetch_real_dataset.py
    python fetch_real_dataset.py --n-stars 600 --n-galaxies 600 --outdir real_dataset
    python fetch_real_dataset.py --workers 4 --tile-limit 400

Output: real_dataset/img_XXXX.fits + real_labels.csv
(kolom: filename, label, class_name, type_letter, ra, dec)
"""
import argparse
import csv
import io
import os
import random
import threading
import time

import numpy as np
import requests
from astropy.io import fits

BASE = "https://www.legacysurvey.org/viewer"
ZOOM = 14
HEADERS = {"Accept": "application/json", "User-Agent": "astro-classifier-fetch"}
PIXSCALE = 0.262  # arcsec/pix, native DECaLS
CUTOUT_SIZE = 64
TIMEOUT = 30


def random_tile():
    """Random tile di zoom 14. Coverage: x ~ 0..2^14, y ~ 0..2^14.
    Kita batasin ke langit yg ada datanya DR9 (dec -30..90)."""
    max_tile = 1 << ZOOM
    x = random.randrange(0, max_tile)
    # DR9 north/south cover banyak. Ambil tile tengah biar coverage baik.
    y = random.randrange(int(max_tile * 0.35), int(max_tile * 0.70))
    return x, y


def fetch_tile_catalog(session, x, y, retries=3):
    """Ambil katalog satu tile, return daftar dict {ra,dec,type}."""
    url = f"{BASE}/ls-dr9/1/{ZOOM}/{x}/{y}.cat.json"
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                j = r.json()
                out = []
                rd = j.get("rd") or []
                st = j.get("sourcetype") or []
                if len(rd) != len(st):
                    return []
                for (ra, dec), t in zip(rd, st):
                    if t in ("P", "R", "E", "D"):
                        out.append({"ra": float(ra), "dec": float(dec), "type": t})
                return out
            if r.status_code in (404, 403):
                return []
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.4 * (attempt + 1))
    return []


def fetch_cutout(session, ra, dec, retries=3):
    """Ambil cutout.fits 64x64 band-r. Return bytes atau None kalau gagal."""
    url = f"{BASE}/cutout.fits"
    params = {
        "ra": f"{ra:.6f}",
        "dec": f"{dec:.6f}",
        "size": CUTOUT_SIZE,
        "layer": "ls-dr9",
        "pixscale": PIXSCALE,
        "bands": "r",
    }
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, stream=False)
            if r.status_code == 200 and r.content[:6] == b"SIMPLE":
                return r.content
            if r.status_code in (404, 400, 403):
                return None
        except requests.RequestException:
            pass
        time.sleep(0.4 * (attempt + 1))
    return None


def is_clean_stamp(fits_bytes, min_flux=0.001):
    """Tolak stamp kosong/korup atau hampir semua NaN."""
    try:
        with fits.open(io.BytesIO(fits_bytes), memmap=False) as hdul:
            data = np.asarray(hdul[0].data, dtype=np.float32)
    except Exception:
        return False
    if data.shape != (CUTOUT_SIZE, CUTOUT_SIZE):
        return False
    if not np.isfinite(data).all():
        if np.isfinite(data).mean() < 0.95:
            return False
        data = np.nan_to_num(data)
    span = float(data.max() - data.min())
    return span > min_flux


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-stars", type=int, default=500)
    parser.add_argument("--n-galaxies", type=int, default=500)
    parser.add_argument("--outdir", default="real_dataset")
    parser.add_argument("--tile-limit", type=int, default=600)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "real_labels.csv")

    session = requests.Session()
    n_stars = 0
    n_galaxies = 0
    n_tiles = 0
    next_idx = 0
    lock = threading.Lock()

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "label", "class_name", "type_letter", "ra", "dec"])

        while (n_stars < args.n_stars or n_galaxies < args.n_galaxies) and n_tiles < args.tile_limit:
            x, y = random_tile()
            n_tiles += 1
            sources = fetch_tile_catalog(session, x, y)
            if not sources:
                if n_tiles % 5 == 0:
                    print(f"tile {n_tiles}: kosong. s/d star={n_stars} galaxy={n_galaxies}", flush=True)
                continue

            random.shuffle(sources)
            for s in sources:
                want_label = 0 if s["type"] == "P" else 1
                if want_label == 0 and n_stars >= args.n_stars:
                    continue
                if want_label == 1 and n_galaxies >= args.n_galaxies:
                    continue
                if s["type"] not in ("P", "R", "E", "D"):
                    continue

                blob = fetch_cutout(session, s["ra"], s["dec"])
                if blob is None or not is_clean_stamp(blob):
                    continue

                with lock:
                    if want_label == 0 and n_stars >= args.n_stars:
                        continue
                    if want_label == 1 and n_galaxies >= args.n_galaxies:
                        continue
                    next_idx += 1
                    fname = f"img_{next_idx:04d}.fits"
                out_path = os.path.join(args.outdir, fname)
                with open(out_path, "wb") as fp:
                    fp.write(blob)
                with lock:
                    if want_label == 0:
                        n_stars += 1
                    else:
                        n_galaxies += 1
                    writer.writerow([
                        fname,
                        want_label,
                        "star" if want_label == 0 else "galaxy",
                        s["type"],
                        f"{s['ra']:.6f}",
                        f"{s['dec']:.6f}",
                    ])
                    f.flush()
                if (n_stars + n_galaxies) % 25 == 0:
                    print(f"tile {n_tiles}: total {n_stars + n_galaxies} ({n_stars} star, {n_galaxies} galaxy)")

    print(f"\nSelesai. Tiles dicoba: {n_tiles}")
    print(f"Stars: {n_stars}, Galaxies: {n_galaxies}, Total: {n_stars + n_galaxies}")
    print(f"Dataset -> {args.outdir} / {csv_path}")


if __name__ == "__main__":
    main()
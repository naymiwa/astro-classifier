"""
Shared FITS preprocessing (used by both training & inference for consistency).

Pipeline:
    load_fits_bytes(bytes)  -> 2D float32 array + quality info
    normalize_fits(array)   -> subtract sky (sigma-clipped median), normalize
                               the 1-99.5% percentile range to [0,1]
    to_model_input(array)   -> resize to 64x64, replicate grayscale to 3 channels
    preprocess_fits(bytes)  -> combines all three + adds a batch dimension
"""
import io

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from PIL import Image
from scipy import ndimage

IMG_SIZE = 64
SATURATED_FRACTION = 0.0005
MAX_SIDE = 2048  # larger frames are downsampled to keep inference fast


def load_fits_bytes(data: bytes):
    """Read a FITS file from memory, return (2D float32 array, quality dict).

    Handles multi-HDU files, 3D cubes (takes the first slice), automatic
    BSCALE/BZERO from astropy, NaN/Inf values, and compressed files
    (.fits.gz) via magic bytes.
    """
    nan_fraction = 0.0
    with fits.open(io.BytesIO(data), memmap=False) as hdul:
        image = None
        for hdu in hdul:
            if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU)) and hdu.data is not None:
                image = hdu
                break
        if image is None:
            raise ValueError("No HDU containing image data was found in this file.")

        raw = np.asarray(image.data)
        if not np.issubdtype(raw.dtype, np.floating):
            raw = raw.astype(np.float64)
        finite = np.isfinite(raw)
        nan_fraction = float(1.0 - finite.mean()) if raw.size else 1.0
        raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)

        if raw.ndim == 3:
            raw = raw[0]
        if raw.ndim != 2:
            raise ValueError(
                "This FITS file is not a 2D image (not a single-object stamp). "
                "It may be a 3D data cube or spectral data. For this demo, "
                "upload a FITS file containing a single celestial object (a stamp)."
            )

    arr = np.asarray(raw, dtype=np.float32)
    if max(arr.shape) > MAX_SIDE:
        factor = MAX_SIDE / max(arr.shape)
        arr = ndimage.zoom(arr, factor, order=1, prefilter=False).astype(np.float32)
    n_max = int((arr >= arr.max()).sum()) if arr.size else 0
    quality = {
        "nan_fraction": round(nan_fraction, 6),
        "saturated": n_max > max(1, int(SATURATED_FRACTION * arr.size)),
    }
    return arr, quality


def normalize_fits(data: np.ndarray) -> np.ndarray:
    """Subtract sky background, then normalize the percentile range to [0,1]."""
    arr = data.astype(np.float32)
    if arr.size == 0:
        return arr
    median, _, _ = sigma_clipped_stats(arr, sigma=3.0, maxiters=5)
    sky = float(median) if np.isfinite(median) else 0.0
    sub = arr - sky
    lo, hi = np.percentile(sub, (1.0, 99.5))
    if not np.isfinite(hi) or hi - lo < 1e-6:
        return np.zeros_like(arr)
    out = (sub - lo) / (hi - lo)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def to_model_input(data: np.ndarray, size: int = IMG_SIZE) -> np.ndarray:
    """Normalize -> resize -> replicate grayscale into 3 channels [0,1]."""
    norm = normalize_fits(data)
    img = Image.fromarray((norm * 255.0).astype(np.uint8), mode="L")
    img = img.resize((size, size), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return np.stack([arr, arr, arr], axis=-1)


def preprocess_fits(data: bytes, size: int = IMG_SIZE):
    """Combines load + normalize + resize, plus a batch dimension."""
    arr, quality = load_fits_bytes(data)
    inp = to_model_input(arr, size)
    return np.expand_dims(inp, axis=0), quality


def render_preview(data: bytes, size: int = 300) -> bytes:
    """Render the normalized stamp as a PNG (RGB, inferno-ish colormap)."""
    arr, _ = load_fits_bytes(data)
    norm = normalize_fits(arr)
    lut = _inferno_lut()
    idx = (np.clip(norm, 0.0, 1.0) * 255.0).astype(np.uint8)
    rgb = lut[idx].reshape(norm.shape[0], norm.shape[1], 3)
    img = Image.fromarray(rgb, mode="RGB").resize((size, size), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _inferno_lut() -> np.ndarray:
    """Inferno-like colormap LUT (256 x 3), no matplotlib dependency."""
    stops = np.array(
        [
            [0.000, 0.000, 0.040],
            [0.122, 0.047, 0.396],
            [0.420, 0.051, 0.593],
            [0.699, 0.119, 0.531],
            [0.910, 0.313, 0.368],
            [0.988, 0.613, 0.186],
            [0.988, 0.851, 0.500],
        ]
    )
    x = np.linspace(0, 1, stops.shape[0])
    xi = np.linspace(0, 1, 256)
    r = np.interp(xi, x, stops[:, 0])
    g = np.interp(xi, x, stops[:, 1])
    b = np.interp(xi, x, stops[:, 2])
    return (np.stack([r, g, b], axis=-1) * 255.0).astype(np.uint8)

"""
core.tampering.ela
------------------
Error Level Analysis (ELA) for detecting digital image manipulation.
Resaves the image at a known JPEG quality level and computes pixel-wise
difference. Edited/pasted regions show higher error rates.

IMPORTANT: ELA only works meaningfully on JPEG images. PNG and other
lossless formats will always show near-zero ELA error (they are lossless),
so we skip or flag ELA differently for such formats.
"""

from io import BytesIO
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageDraw


def _is_lossless_format(image_or_path: Any) -> bool:
    """Check if the source image is a lossless format (PNG, BMP, TIFF)."""
    if isinstance(image_or_path, (str, Path)):
        suffix = Path(str(image_or_path)).suffix.lower()
        return suffix in {".png", ".bmp", ".tiff", ".tif", ".webp"}
    return False


def run_ela_analysis(
    image_or_path: Any,
    out_annotated_path: Optional[str] = None,
    quality: int = 90,
    multiplier: float = 15.0,
    z_score_thresh: float = 7.0,   # Raised threshold — real photos have natural variation
) -> Dict[str, Any]:
    """
    Execute Error Level Analysis and return anomaly metrics.

    For lossless PNG/BMP images: ELA is not meaningful, so we run it but
    do NOT flag as tampered based on ELA alone (too many false positives).
    """
    is_lossless = _is_lossless_format(image_or_path)

    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    rgb = img.convert("RGB")

    # Resave in memory at fixed JPEG quality
    buf = BytesIO()
    rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")

    diff = ImageChops.difference(rgb, resaved)
    diff_arr = np.asarray(diff, dtype=np.float32)

    # Per-pixel Euclidean error magnitude
    error_mag = np.hypot(diff_arr[:, :, 0], np.hypot(diff_arr[:, :, 1], diff_arr[:, :, 2]))

    mean_err = float(error_mag.mean())
    std_err = float(error_mag.std()) + 1e-6
    peak_err = float(error_mag.max())

    # Spatial 20x20 grid analysis
    h, w = error_mag.shape
    gh, gw = max(1, h // 20), max(1, w // 20)
    max_grid_z = 0.0
    flagged_box = None

    for i in range(20):
        for j in range(20):
            block = error_mag[i * gh:(i + 1) * gh, j * gw:(j + 1) * gw]
            if block.size > 0:
                b_mean = float(block.mean())
                z = (b_mean - mean_err) / std_err
                if z > max_grid_z:
                    max_grid_z = z
                if z > z_score_thresh:
                    flagged_box = (j * gw, i * gh, (j + 1) * gw, (i + 1) * gh)

    # For lossless formats: raise threshold significantly (PNG always re-encodes differently)
    effective_thresh = z_score_thresh * 1.8 if is_lossless else z_score_thresh
    is_tampered = bool(max_grid_z > effective_thresh)

    if out_annotated_path:
        enhanced = ImageEnhance.Brightness(diff).enhance(multiplier)
        if flagged_box and is_tampered:
            draw = ImageDraw.Draw(enhanced)
            draw.rectangle(flagged_box, outline=(255, 0, 0), width=3)
        enhanced.save(out_annotated_path)

    return {
        "technique": "Error Level Analysis (ELA)",
        "likely_tampered": is_tampered,
        "z_score": round(max_grid_z, 3),
        "peak_error": round(peak_err, 2),
        "mean_error": round(mean_err, 2),
        "std_error": round(std_err, 2),
        "flagged_box": flagged_box,
        "is_lossless_source": is_lossless,
        "note": "ELA less reliable for PNG/lossless sources" if is_lossless else None,
    }


run_ela = run_ela_analysis

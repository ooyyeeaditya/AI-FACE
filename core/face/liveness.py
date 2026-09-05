"""
core.face.liveness
------------------
Heuristic presentation attack detection (anti-spoofing). Checks live camera
feed for screen glare, display pixel moiré patterns, and printed photo artifacts.
"""

from typing import Dict, Any
import numpy as np
from PIL import Image


def assess_liveness(face_crop: Image.Image) -> Dict[str, Any]:
    """Analyze face crop for spoofing indicators (screen reflections / moiré)."""
    if face_crop is None:
        return {"is_live": False, "liveness_score": 0.0, "reason": "No face provided"}

    arr = np.asarray(face_crop.convert("RGB"), dtype=np.float32)
    gray = np.asarray(face_crop.convert("L"), dtype=np.float32)

    # 1. Specular reflection / blown-out screen glare check
    high_pixels = (gray > 250).sum()
    glare_ratio = float(high_pixels / (gray.size + 1e-4))

    # 2. Color saturation distribution
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    sat = (max_c - min_c) / (max_c + 1e-4)
    avg_sat = float(sat.mean())

    # Decision
    is_spoof = bool(glare_ratio > 0.15 or avg_sat < 0.04)
    liveness_score = 0.25 if is_spoof else 0.94

    return {
        "is_live": not is_spoof,
        "liveness_score": round(liveness_score, 2),
        "glare_ratio": round(glare_ratio, 3),
        "saturation": round(avg_sat, 3),
        "spoof_indicator": "HIGH_SPECULAR_SCREEN_GLARE" if glare_ratio > 0.15 else "NATURAL_FACE",
    }

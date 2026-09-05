"""
core.tampering.copy_move
------------------------
Detects copy-move cloning and repeated text glyph duplication on documents.
Uses 2D gradient dispersion to distinguish true 2D cloned glyphs/stamps from
1D solid stripes and periodic background guilloche patterns.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from PIL import Image


def detect_copy_move_forgery(
    image_or_path: Any,
    block_size: int = 16,
    stride: int = 10,
    similarity_thresh: float = 0.998,
    min_distance: int = 120,
) -> Dict[str, Any]:
    """Detect cloned sub-blocks across the document image using 2D block feature matching."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    gray = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = gray.shape

    scale = 1.0
    if max(h, w) > 600:
        scale = 600.0 / max(h, w)
        img_small = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
        gray = np.asarray(img_small.convert("L"), dtype=np.float32)
        h, w = gray.shape

    blocks = []
    positions = []

    for y in range(0, h - block_size, stride):
        for x in range(0, w - block_size, stride):
            b = gray[y:y + block_size, x:x + block_size]
            gx = np.diff(b, axis=1)
            gy = np.diff(b, axis=0)
            # Require 2D texture variation (eliminates 1D stripes, margin lines, and uniform bands)
            if gx.std() > 8.0 and gy.std() > 8.0 and b.std() > 30.0:
                b_norm = (b - b.mean()) / (b.std() + 1e-4)
                blocks.append(b_norm.flatten())
                positions.append((x, y))

    matched_pairs = 0
    if len(blocks) > 0:
        sample_limit = min(len(blocks), 300)
        indices = np.linspace(0, len(blocks) - 1, sample_limit, dtype=int)
        for i_idx in range(len(indices)):
            i = indices[i_idx]
            b1 = blocks[i]
            x1, y1 = positions[i]
            for j_idx in range(i_idx + 1, min(i_idx + 25, len(indices))):
                j = indices[j_idx]
                x2, y2 = positions[j]
                dist = np.hypot(x1 - x2, y1 - y2)
                if dist >= min_distance:
                    corr = np.dot(b1, blocks[j]) / len(b1)
                    if corr > similarity_thresh:
                        matched_pairs += 1

    is_cloned = bool(matched_pairs >= 10)

    return {
        "technique": "Copy-Move Forgery Detection",
        "likely_cloned": is_cloned,
        "cloned_block_matches": matched_pairs,
    }

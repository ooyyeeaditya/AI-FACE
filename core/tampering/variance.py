"""
core.tampering.variance
-----------------------
Local noise variance and texture consistency analyzer. Detects solid-fill
patches, digitally smoothed text alterations, and background grain inconsistencies.
Distinguishes isolated suspicious patches from naturally uniform digital substrates.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

CELL = 16


def compute_local_std_grid(gray_array: np.ndarray, cell: int = CELL) -> np.ndarray:
    """Compute standard deviation for non-overlapping spatial blocks."""
    h, w = gray_array.shape
    gh, gw = h // cell, w // cell
    grid = np.zeros((gh, gw), dtype=np.float32)
    for i in range(gh):
        for j in range(gw):
            block = gray_array[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
            grid[i, j] = float(block.std())
    return grid


def calibrate_noise_floor(
    reference_images: List[Any],
    region_box: Optional[Tuple[int, int, int, int]] = None,
    percentile: float = 0.5,
) -> float:
    """Calibrate the genuine document noise floor from reference images."""
    pooled = []
    for item in reference_images:
        if isinstance(item, (str, Path)):
            img = Image.open(str(item)).convert("L")
        else:
            img = item.convert("L")
        arr = np.asarray(img, dtype=np.float32)
        if region_box:
            x0, y0, x1, y1 = region_box
            sub = arr[y0:y1, x0:x1]
        else:
            sub = arr
        grid = compute_local_std_grid(sub, cell=CELL)
        pooled.append(grid.flatten())

    if not pooled:
        return 3.5
    combined = np.concatenate(pooled)
    return float(np.percentile(combined, percentile))


def run_variance_analysis(
    image_or_path: Any,
    out_annotated_path: Optional[str] = None,
    region_box: Optional[Tuple[int, int, int, int]] = None,
    noise_floor_threshold: float = 3.5,
    min_cluster_cells: int = 6,
) -> Dict[str, Any]:
    """Analyze document image for local variance collapse and patch tampering."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    gray = img.convert("L")
    arr = np.asarray(gray, dtype=np.float32)

    if region_box:
        x0, y0, x1, y1 = region_box
        sub = arr[y0:y1, x0:x1]
    else:
        x0, y0 = 0, 0
        sub = arr

    grid = compute_local_std_grid(sub, cell=CELL)
    if grid.size == 0:
        return {
            "technique": "Noise Variance Forensics",
            "likely_tampered": False,
            "num_flagged_cells": 0,
            "num_clusters": 0,
            "largest_cluster_size": 0,
            "flagged_box": None,
        }

    mean_grid_noise = float(grid.mean())
    flags = grid < noise_floor_threshold
    num_flagged = int(flags.sum())

    # An isolated forged text patch (e.g. pasted date or erased name) is small (typically 6-150 cells).
    # If the document as a whole has large uniform background (> 15% flat cells) or the cluster is huge (> 150 cells),
    # it is natural document background paper texture, NOT an isolated forged patch.
    is_uniform_digital_substrate = (num_flagged > (grid.size * 0.15)) or (mean_grid_noise < 6.5)

    labeled, n_clusters = ndimage.label(flags, structure=np.ones((3, 3)))
    cluster_sizes = ndimage.sum(flags, labeled, index=range(1, n_clusters + 1)) if n_clusters else []
    largest_cluster_id = int(np.argmax(cluster_sizes)) + 1 if len(cluster_sizes) > 0 else None
    largest_size = int(cluster_sizes[largest_cluster_id - 1]) if largest_cluster_id else 0

    merged_box = None
    is_tampered = False
    max_patch_size = min(150, max(25, int(grid.size * 0.04)))
    if not is_uniform_digital_substrate and largest_cluster_id and (min_cluster_cells <= largest_size <= max_patch_size):
        rows, cols = np.where(labeled == largest_cluster_id)
        bx0 = x0 + int(cols.min()) * CELL
        by0 = y0 + int(rows.min()) * CELL
        bx1 = x0 + (int(cols.max()) + 1) * CELL
        by1 = y0 + (int(rows.max()) + 1) * CELL
        merged_box = (bx0, by0, bx1, by1)
        is_tampered = True

    if out_annotated_path:
        color_img = img.convert("RGB")
        if merged_box and is_tampered:
            d = ImageDraw.Draw(color_img)
            d.rectangle(merged_box, outline=(255, 0, 0), width=4)
        color_img.save(out_annotated_path)

    return {
        "technique": "Noise Variance Forensics",
        "likely_tampered": is_tampered,
        "num_flagged_cells": num_flagged,
        "num_clusters": int(n_clusters),
        "largest_cluster_size": largest_size if is_tampered else 0,
        "flagged_box": merged_box if is_tampered else None,
    }

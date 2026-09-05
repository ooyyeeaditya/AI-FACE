"""
variance_forensics.py
----------------------
A second, complementary forensic signal to ELA: local noise/variance
inconsistency.

Real printed security documents have a textured background (guilloche
patterns, microprint, watermark) with fairly consistent local variance
everywhere. When a forger pastes a solid-fill box over a field to edit
it (exactly what tamper_dob() does, and exactly what a real amateur
forgery looks like), that patch is locally almost perfectly flat -
its local standard deviation collapses relative to its surroundings.

This is a real, published class of technique (noise-level / PRNU-style
inconsistency detection), simplified here to plain local std-dev, which
is enough to reliably catch flat-fill splices without needing a trained
model - and it's honest about being a *different* signal from ELA, not
a fix for ELA's false positives.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

CELL = 16


def local_std_grid(gray: np.ndarray, cell: int = CELL) -> np.ndarray:
    h, w = gray.shape
    gh, gw = h // cell, w // cell
    grid = np.zeros((gh, gw))
    for i in range(gh):
        for j in range(gw):
            block = gray[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
            grid[i, j] = block.std()
    return grid


def flag_flat_patches(grid: np.ndarray, noise_floor_threshold: float):
    """A cell is suspicious if its local std sits BELOW the document's
    calibrated noise floor -- i.e. it has less texture than even plain
    background is supposed to have.

    Why an absolute threshold and not a neighbor-relative one: a page full
    of printed text has plenty of *legitimate* high-std cells (glyph edges,
    security-pattern lines) sitting right next to normal low-std background
    cells. A neighbor-ratio rule flags those legitimate transitions too
    (tested and confirmed empirically: it produced false positives on a
    genuine specimen). An absolute floor, calibrated from what genuine
    noise actually looks like, does not -- because the real "print/scan
    grain" noise never fully vanishes on a genuine document. A perfectly
    flat digitally-pasted patch is the one thing that fully removes it.
    In production this floor would be calibrated per-scanner/per-template
    from a corpus of known-genuine documents, not hardcoded.
    """
    return grid < noise_floor_threshold


def analyze(path: str, out_path: str, region_box=None, noise_floor_threshold: float = 4.0,
            min_cluster_cells: int = 4):
    """A single stray flagged cell is expected noise (any threshold has some
    false-positive rate on unseen genuine documents). A real pasted patch is
    always several cells wide, so we require a CONTIGUOUS cluster of flagged
    cells before calling it tampering -- this is what actually separates the
    signal from calibration noise, not the raw per-cell flag count."""
    img = Image.open(path).convert("L")
    arr = np.asarray(img, dtype=np.float32)

    if region_box:
        x0, y0, x1, y1 = region_box
        sub = arr[y0:y1, x0:x1]
    else:
        x0, y0 = 0, 0
        sub = arr

    grid = local_std_grid(sub, cell=CELL)
    flags = flag_flat_patches(grid, noise_floor_threshold=noise_floor_threshold)

    labeled, n_clusters = ndimage.label(flags, structure=np.ones((3, 3)))  # 8-connectivity
    cluster_sizes = ndimage.sum(flags, labeled, index=range(1, n_clusters + 1)) if n_clusters else []
    largest_cluster_id = int(np.argmax(cluster_sizes)) + 1 if n_clusters else None
    largest_size = int(cluster_sizes[largest_cluster_id - 1]) if largest_cluster_id else 0

    color_img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(color_img)
    merged_box = None
    if largest_cluster_id and largest_size >= min_cluster_cells:
        rows, cols = np.where(labeled == largest_cluster_id)
        bx0, by0 = x0 + cols.min() * CELL, y0 + rows.min() * CELL
        bx1, by1 = x0 + (cols.max() + 1) * CELL, y0 + (rows.max() + 1) * CELL
        d.rectangle((bx0, by0, bx1, by1), outline=(255, 0, 0), width=4)
        merged_box = (bx0, by0, bx1, by1)
    color_img.save(out_path)

    return {
        "num_flagged_cells": int(flags.sum()),
        "num_clusters": int(n_clusters),
        "largest_cluster_size": largest_size,
        "flagged_bounding_box": merged_box,
        "likely_tampered": bool(largest_size >= min_cluster_cells),
    }


def calibrate_noise_floor(genuine_paths: list, region_box, percentile: float = 0.5) -> float:
    """Learn the noise floor from a small corpus of KNOWN-genuine documents
    (the way a real deployment would calibrate per scanner/template), rather
    than hardcoding a number or trusting a single reference image (one
    sample is noisy; pooling several gives a stable low-percentile floor)."""
    pooled = []
    for p in genuine_paths:
        img = Image.open(p).convert("L")
        arr = np.asarray(img, dtype=np.float32)
        x0, y0, x1, y1 = region_box
        grid = local_std_grid(arr[y0:y1, x0:x1], cell=CELL)
        pooled.append(grid.flatten())
    pooled = np.concatenate(pooled)
    return float(np.percentile(pooled, percentile))


if __name__ == "__main__":
    import random as _random
    from generate_specimen import random_identity, render_specimen

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Restrict to the left field-text zone (below header, above MRZ strip,
    # left of the photo box) -- a real system would know this from the
    # document template, same as Module 2's layout validation.
    field_zone = (0, 100, 820, 620)

    # Calibrate the noise floor on a small pool of SEPARATE known-genuine
    # specimens (not the one we're about to test on) -- a proper train/test
    # split: calibrate against a reference corpus, then evaluate on new docs.
    calib_paths = []
    for seed in [901, 902, 903, 904, 905]:
        calib_rng = _random.Random(seed)
        calib_identity = random_identity(calib_rng)
        calib_img, _ = render_specimen(calib_identity, calib_rng)
        p = out_dir / f"_calibration_reference_{seed}.png"
        calib_img.save(p)
        calib_paths.append(str(p))

    threshold = calibrate_noise_floor(calib_paths, field_zone, percentile=0.5)
    print(f"Calibrated noise-floor threshold (0.5th pct over {len(calib_paths)} genuine reference docs): {threshold:.2f}\n")

    print("=== Local-variance forensics: GENUINE ===")
    r1 = analyze(str(out_dir / "specimen_genuine.png"), str(out_dir / "variance_genuine.png"),
                 field_zone, noise_floor_threshold=threshold)
    print(r1)

    print("\n=== Local-variance forensics: TAMPERED ===")
    r2 = analyze(str(out_dir / "specimen_tampered.png"), str(out_dir / "variance_tampered.png"),
                 field_zone, noise_floor_threshold=threshold)
    print(r2)

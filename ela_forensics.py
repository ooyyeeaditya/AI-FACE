"""
ela_forensics.py
-----------------
Error Level Analysis (ELA) - a real, widely-used image-forensics technique
(the same core idea behind tools like FotoForensics).

Idea: a JPEG re-compresses in 8x8 blocks. A region that was pasted/edited
*after* the image's last "settled" compression pass responds differently
to a fresh re-save at a known quality than the rest of the image, which
has already reached a compression steady-state. Diffing the image against
a deliberate re-save at a fixed quality highlights exactly those regions.

This module does NOT know where any edit was made. It only looks at pixels.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def compute_ela(img: Image.Image, quality: int = 90, scale: int = 15) -> Image.Image:
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer)

    diff = ImageChops.difference(img, resaved)
    diff = ImageEnhance.Brightness(diff).enhance(scale)
    return diff


def region_error_scores(diff_img: Image.Image, grid: int = 20):
    """Break the ELA diff into a grid and return mean error per cell, so we
    can report *which* region is most suspicious without hardcoding it."""
    arr = np.asarray(diff_img.convert("L"), dtype=np.float32)
    h, w = arr.shape
    ch, cw = h // grid, w // grid
    scores = np.zeros((grid, grid))
    for i in range(grid):
        for j in range(grid):
            cell = arr[i * ch:(i + 1) * ch, j * cw:(j + 1) * cw]
            scores[i, j] = cell.mean() if cell.size else 0
    return scores


def top_suspicious_region(scores: np.ndarray, grid: int, img_size):
    idx = np.unravel_index(np.argmax(scores), scores.shape)
    row, col = idx
    w, h = img_size
    ch, cw = h // grid, w // grid
    box = (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)
    return box, scores[idx], scores.mean(), scores.std()


def analyze(path: str, out_path: str, quality: int = 90, grid: int = 20):
    img = Image.open(path)
    # First, save through one JPEG pass so ELA has a defined baseline
    # (mirrors how a real scanned/photographed document actually arrives).
    baseline_buf = io.BytesIO()
    img.convert("RGB").save(baseline_buf, "JPEG", quality=95)
    baseline_buf.seek(0)
    working_img = Image.open(baseline_buf)

    diff = compute_ela(working_img, quality=quality)
    scores = region_error_scores(diff, grid=grid)
    box, peak, mean, std = top_suspicious_region(scores, grid, working_img.size)
    z_score = (peak - mean) / std if std > 0 else 0

    # Annotate and save
    from PIL import ImageDraw
    annotated = diff.convert("RGB")
    d = ImageDraw.Draw(annotated)
    d.rectangle(box, outline=(255, 255, 0), width=4)
    annotated.save(out_path)

    return {
        "peak_cell_error": float(peak),
        "mean_cell_error": float(mean),
        "std_cell_error": float(std),
        "z_score": float(z_score),
        "flagged_region_px": box,
        "likely_tampered": bool(z_score > 2.5),
    }


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "output"

    print("=== ELA on GENUINE specimen ===")
    r1 = analyze(str(out_dir / "specimen_genuine.png"), str(out_dir / "ela_genuine.png"))
    for k, v in r1.items():
        print(f"  {k}: {v}")

    print("\n=== ELA on TAMPERED specimen ===")
    r2 = analyze(str(out_dir / "specimen_tampered.png"), str(out_dir / "ela_tampered.png"))
    for k, v in r2.items():
        print(f"  {k}: {v}")

    print("\nVerdict:")
    print(f"  Genuine  -> flagged as tampered: {r1['likely_tampered']} (z={r1['z_score']:.2f})")
    print(f"  Tampered -> flagged as tampered: {r2['likely_tampered']} (z={r2['z_score']:.2f})")

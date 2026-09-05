"""
core.tampering.photo_splice
---------------------------
Detects photo replacement and portrait splicing on identity documents.
Analyzes border gradient discontinuities and edge boundary seams between
the portrait zone and document substrate.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import cv2


def _refine_photo_boundary_from_face(
    gray: np.ndarray,
    face_box: Tuple[int, int, int, int],
) -> Tuple[int, int, int, int]:
    """
    Given a detected face box (fx, fy, fw, fh), search for the outer rectangular
    photo card border cut lines using Sobel edge profiles.
    """
    h, w = gray.shape[:2]
    fx, fy, fw, fh = face_box

    # Search window around face
    x0 = max(0, fx - int(fw * 0.9))
    y0 = max(0, fy - int(fh * 0.7))
    x1 = min(w, fx + fw + int(fw * 0.9))
    y1 = min(h, fy + fh + int(fh * 0.9))

    sobel_h = np.abs(ndimage.sobel(gray, axis=0))
    sobel_v = np.abs(ndimage.sobel(gray, axis=1))

    # Find highest gradient horizontal line above the face and below the face
    try:
        top_slice = sobel_h[y0:fy, x0:x1]
        top_y = y0 + int(np.argmax(np.mean(top_slice, axis=1))) if top_slice.size > 0 else fy - 20
    except Exception:
        top_y = max(0, fy - 20)

    try:
        bot_slice = sobel_h[fy + fh:y1, x0:x1]
        bot_y = (fy + fh) + int(np.argmax(np.mean(bot_slice, axis=1))) if bot_slice.size > 0 else fy + fh + 20
    except Exception:
        bot_y = min(h, fy + fh + 20)

    try:
        left_slice = sobel_v[y0:y1, x0:fx]
        left_x = x0 + int(np.argmax(np.mean(left_slice, axis=0))) if left_slice.size > 0 else fx - 20
    except Exception:
        left_x = max(0, fx - 20)

    try:
        right_slice = sobel_v[y0:y1, fx + fw:x1]
        right_x = (fx + fw) + int(np.argmax(np.mean(right_slice, axis=0))) if right_slice.size > 0 else fx + fw + 20
    except Exception:
        right_x = min(w, fx + fw + 20)

    return (int(left_x), int(top_y), int(right_x), int(bot_y))


def _compute_box_border_strength(gray: np.ndarray, box: Tuple[int, int, int, int]) -> float:
    """Compute mean border gradient along the perimeter of a candidate rectangle."""
    h, w = gray.shape[:2]
    px0, py0, px1, py1 = box
    px0, py0 = max(0, px0), max(0, py0)
    px1, py1 = min(w, px1), min(h, py1)

    if px1 - px0 < 20 or py1 - py0 < 20:
        return 0.0

    pad = 4
    outer_x0, outer_y0 = max(0, px0 - pad), max(0, py0 - pad)
    outer_x1, outer_y1 = min(w, px1 + pad), min(h, py1 + pad)

    perimeter_crop = gray[outer_y0:outer_y1, outer_x0:outer_x1]
    if perimeter_crop.shape[0] < pad * 2 or perimeter_crop.shape[1] < pad * 2:
        return 0.0

    sobel_h = ndimage.sobel(perimeter_crop, axis=0)
    sobel_v = ndimage.sobel(perimeter_crop, axis=1)
    grad_mag = np.hypot(sobel_h, sobel_v)

    border_mask = np.zeros_like(grad_mag, dtype=bool)
    border_mask[pad - 2:pad + 2, :] = True
    border_mask[-pad - 2:-pad + 2, :] = True
    border_mask[:, pad - 2:pad + 2] = True
    border_mask[:, -pad - 2:-pad + 2] = True

    return float(grad_mag[border_mask].mean()) if border_mask.any() else 0.0


def detect_photo_splice(
    image_or_path: Any,
    photo_box: Optional[Tuple[int, int, int, int]] = None,
    out_annotated_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inspect the portrait region for spliced cut lines and edge boundary anomalies.
    Dynamically searches for real face location and refined outer photo borders.
    """
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    rgb = img.convert("RGB")
    w, h = rgb.size
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)

    candidate_boxes = []

    # 1. Try automated face detection to find real face location and outer photo card boundary
    try:
        from core.face.face_engine import detect_face_info_and_box
        _, face_box = detect_face_info_and_box(bgr, is_document=True)
        if face_box:
            refined_box = _refine_photo_boundary_from_face(gray, face_box)
            candidate_boxes.append(refined_box)
    except Exception:
        pass

    # 2. Add explicitly provided photo box if any
    if photo_box:
        candidate_boxes.append(photo_box)
    else:
        candidate_boxes.append((int(w * 0.78), int(h * 0.12), int(w * 0.96), int(h * 0.42)))
        candidate_boxes.append((int(w * 0.05), int(h * 0.20), int(w * 0.35), int(h * 0.75)))

    # Evaluate each candidate box and find the maximum border cut gradient
    best_strength = 0.0
    best_box = candidate_boxes[0]

    for box in candidate_boxes:
        strength = _compute_box_border_strength(gray, box)
        if strength > best_strength:
            best_strength = strength
            best_box = box

    # Decision threshold: A sharp digital paste cut seam has mean gradient > 165.0
    is_spliced = bool(best_strength > 165.0)
    splice_score = float(np.clip(best_strength / 250.0, 0.0, 1.0))

    if out_annotated_path:
        annotated = rgb.copy()
        d = ImageDraw.Draw(annotated)
        color = (255, 0, 0) if is_spliced else (0, 200, 0)
        d.rectangle(best_box, outline=color, width=4)
        annotated.save(out_annotated_path)

    return {
        "technique": "Photo Replacement / Splice Detection",
        "likely_spliced": is_spliced,
        "splice_score": round(splice_score, 3),
        "border_edge_strength": round(best_strength, 2),
        "photo_box": best_box,
    }

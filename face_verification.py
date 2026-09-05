"""Basic face verification module for document owner matching.

This module is deliberately lightweight, but it adds the missing real-world
requirement from the problem statement: comparing the document photo to the
presented person.

It provides:
- face detection in an image
- a simple similarity score using image histogram comparison
- a verification verdict based on a threshold

This is a practical prototype, not a production-grade biometric matcher.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def detect_faces(image_path: str | Path):
    """Return bounding boxes for detected faces in an image."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]


def normalize_face(image_path: str | Path, face_box=None):
    """Crop and normalize face region for comparison."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    if face_box is None:
        faces = detect_faces(image_path)
        if not faces:
            return None
        x, y, w, h = faces[0]
    else:
        x, y, w, h = face_box

    face = image[y:y + h, x:x + w]
    if face.size == 0:
        return None

    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.resize(face, (128, 128))
    return face


def compare_faces(doc_image_path: str | Path, live_image_path: str | Path) -> dict:
    """Compare a document photo against a live image using grayscale histogram similarity."""
    doc_face = normalize_face(doc_image_path)
    live_face = normalize_face(live_image_path)

    if doc_face is None or live_face is None:
        return {
            "matched": False,
            "score": 0.0,
            "status": "No face detected",
            "faces_found": 0,
        }

    hist_doc = cv2.calcHist([doc_face], [0], None, [32], [0, 256])
    hist_live = cv2.calcHist([live_face], [0], None, [32], [0, 256])
    cv2.normalize(hist_doc, hist_doc)
    cv2.normalize(hist_live, hist_live)

    score = cv2.compareHist(hist_doc, hist_live, cv2.HISTCMP_CORREL)
    threshold = 0.65

    return {
        "matched": bool(score >= threshold),
        "score": float(score),
        "status": "Face matches document" if score >= threshold else "Face mismatch or low confidence",
        "faces_found": 2,
    }


if __name__ == "__main__":
    sample_doc = Path(__file__).resolve().parent / "output" / "specimen_genuine.png"
    if sample_doc.exists():
        faces = detect_faces(sample_doc)
        print("Detected faces:", faces)
    else:
        print("No sample document image found. Generate specimens first.")

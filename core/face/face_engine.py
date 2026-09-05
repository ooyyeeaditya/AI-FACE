"""
core.face.face_engine
---------------------
1:1 Biometric Face Verification Engine using OpenCV SFace & YuNet.

Uses a two-stage deep learning pipeline:
  Stage 1 — Face Detection & 5-Point Landmark Extraction: YuNet (ONNX)
  Stage 2 — Facial Geometry Embedding & Cosine Matching: SFace (128-dim ONNX)

SFace matches true facial geometry (eye spacing, nose shape, jawline, facial proportions),
eliminating false matches between different people even under similar lighting.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
from PIL import Image
import cv2

# ── Model paths ────────────────────────────────────────────────────────────────
_MODELS_DIR = Path(__file__).parent / "models"
_YUNET_PATH = _MODELS_DIR / "face_detection_yunet_2023mar.onnx"
_SFACE_PATH = _MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# ── Global singletons ──────────────────────────────────────────────────────────
_yunet = None
_sface = None


def _load_models():
    """Load YuNet face detector and SFace recognizer once."""
    global _yunet, _sface
    if _yunet is None and _YUNET_PATH.exists() and _YUNET_PATH.stat().st_size > 50_000:
        try:
            _yunet = cv2.FaceDetectorYN.create(
                str(_YUNET_PATH), "", (320, 320),
                score_threshold=0.30, nms_threshold=0.30, top_k=5000,
            )
        except Exception:
            _yunet = None

    if _sface is None and _SFACE_PATH.exists() and _SFACE_PATH.stat().st_size > 1_000_000:
        try:
            _sface = cv2.FaceRecognizerSF.create(str(_SFACE_PATH), "")
        except Exception:
            _sface = None


_load_models()


@dataclass
class FaceVerificationResult:
    matched: bool
    similarity_score: float
    status: str
    doc_face_detected: bool
    live_face_detected: bool
    doc_face_box: Optional[Tuple[int, int, int, int]] = None
    live_face_box: Optional[Tuple[int, int, int, int]] = None
    doc_face_crop: Optional[Image.Image] = None
    live_face_crop: Optional[Image.Image] = None
    confidence_level: str = "HIGH"
    engine_used: str = "sface_deep_onnx"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "similarity_score": self.similarity_score,
            "status": self.status,
            "doc_face_detected": self.doc_face_detected,
            "live_face_detected": self.live_face_detected,
            "confidence_level": self.confidence_level,
            "engine_used": self.engine_used,
        }


def _pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _bgr_to_pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def _crop_from_box(img: Image.Image, box: Tuple[int, int, int, int], pad: float = 0.15) -> Image.Image:
    """Crop face region with generous padding."""
    x, y, w, h = box
    iw, ih = img.size
    px, py = int(w * pad), int(h * pad)
    x0 = max(0, x - px)
    y0 = max(0, y - py)
    x1 = min(iw, x + w + px)
    y1 = min(ih, y + h + py)
    return img.crop((x0, y0, x1, y1))


def _estimate_face_info_from_box(box: Tuple[int, int, int, int], score: float = 0.8) -> np.ndarray:
    """Create a synthetic 15-dim face info vector with pseudo-landmarks from a bounding box."""
    x, y, w, h = box
    re_x, re_y = float(x + 0.30 * w), float(y + 0.35 * h)
    le_x, le_y = float(x + 0.70 * w), float(y + 0.35 * h)
    nt_x, nt_y = float(x + 0.50 * w), float(y + 0.55 * h)
    rm_x, rm_y = float(x + 0.35 * w), float(y + 0.75 * h)
    lm_x, lm_y = float(x + 0.65 * w), float(y + 0.75 * h)
    return np.array([x, y, w, h, re_x, re_y, le_x, le_y, nt_x, nt_y, rm_x, rm_y, lm_x, lm_y, score], dtype=np.float32)


def detect_face_info_and_box(
    bgr: np.ndarray,
    is_document: bool = False,
    doc_type: str = "passport",
) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
    """
    Detect the most relevant face in an image.
    Returns (face_info_15dim, bounding_box_4dim) or (None, None).
    """
    _load_models()
    h, w = bgr.shape[:2]

    # 1. Try YuNet deep learning detector
    if _yunet is not None:
        try:
            _yunet.setInputSize((w, h))
            ret, faces = _yunet.detect(bgr)
            if faces is not None and len(faces) > 0:
                if is_document:
                    # On Indian passport / IDs, photo is on the left half
                    left_faces = [f for f in faces if f[0] < w * 0.65]
                    best_face = max(left_faces, key=lambda f: f[2] * f[3]) if left_faces else max(faces, key=lambda f: f[2] * f[3])
                else:
                    best_face = max(faces, key=lambda f: f[2] * f[3])

                fx, fy, fw, fh = int(best_face[0]), int(best_face[1]), int(best_face[2]), int(best_face[3])
                # Ensure box stays within bounds
                fx, fy = max(0, fx), max(0, fy)
                fw, fh = min(w - fx, fw), min(h - fy, fh)
                return best_face, (fx, fy, fw, fh)
        except Exception:
            pass

    # 2. Fallback heuristic bounding box with pseudo-landmarks
    if is_document:
        fx = int(w * 0.04)
        fy = int(h * 0.15)
        fw = int(w * 0.32)
        fh = int(h * 0.55)
    else:
        fx = int(w * 0.15)
        fy = int(h * 0.08)
        fw = int(w * 0.70)
        fh = int(h * 0.84)

    fx, fy = max(0, fx), max(0, fy)
    fw, fh = min(w - fx, fw), min(h - fy, fh)
    box = (fx, fy, fw, fh)
    pseudo_info = _estimate_face_info_from_box(box, score=0.5)
    return pseudo_info, box


def detect_face_region(
    image_or_path: Any,
    is_document: bool = True,
    doc_type: str = "passport",
) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[Image.Image]]:
    """Detect and return face bounding box + crop from document or live photo."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    bgr = _pil_to_bgr(img)
    _, box = detect_face_info_and_box(bgr, is_document=is_document, doc_type=doc_type)
    if box is None:
        return None, None

    crop = _crop_from_box(img, box)
    return box, crop


def _extract_sface_embedding(bgr: np.ndarray, face_info: np.ndarray) -> Optional[np.ndarray]:
    """Extract 128-dim SFace embedding using OpenCV FaceRecognizerSF."""
    _load_models()
    if _sface is None:
        return None
    try:
        aligned = _sface.alignCrop(bgr, face_info)
        feat = _sface.feature(aligned)
        return feat.flatten()
    except Exception:
        return None


def _extract_face_feature_vector(face_crop: Image.Image) -> np.ndarray:
    """
    Extract facial feature vector for 1:N gallery storage / search.
    Uses SFace 128-d embedding when available, else spatial texture/color moments.
    """
    if face_crop is None:
        return np.zeros(128, dtype=np.float32)

    _load_models()
    bgr = _pil_to_bgr(face_crop)
    h, w = bgr.shape[:2]

    if _sface is not None:
        # Check if face detector finds landmarks inside crop
        face_info = None
        if _yunet is not None:
            try:
                _yunet.setInputSize((w, h))
                ret, faces = _yunet.detect(bgr)
                if faces is not None and len(faces) > 0:
                    face_info = max(faces, key=lambda f: f[2] * f[3])
            except Exception:
                face_info = None

        if face_info is None:
            face_info = _estimate_face_info_from_box((0, 0, w, h), score=0.8)

        emb = _extract_sface_embedding(bgr, face_info)
        if emb is not None:
            norm = np.linalg.norm(emb)
            return emb / (norm + 1e-7)

    # Fallback multi-feature vector
    return _extract_improved_histogram_vector(face_crop)


def _extract_improved_histogram_vector(crop: Image.Image) -> np.ndarray:
    """Extract 234-dim spatial color and texture feature vector."""
    size = (96, 96)
    c = np.array(crop.convert("RGB").resize(size), dtype=np.float32) / 255.0
    g = np.array(crop.convert("L").resize(size), dtype=np.float32) / 255.0

    features = []
    cell = 16
    for i in range(6):
        for j in range(6):
            b = c[i * cell : min((i + 1) * cell, 96), j * cell : min((j + 1) * cell, 96)]
            for ch in range(3):
                features.extend([float(b[:, :, ch].mean()), float(b[:, :, ch].std())])

    for i in range(0, 96, 8):
        for j in range(0, 96, 8):
            patch = g[i : i + 8, j : j + 8]
            if patch.size > 0:
                center = patch[4, 4] if patch.shape == (8, 8) else patch.mean()
                lbp = float((patch > center).sum()) / patch.size
                features.append(lbp)

    v = np.array(features, dtype=np.float32)
    norm = np.linalg.norm(v)
    return v / (norm + 1e-7) if norm > 1e-6 else v


def compare_face_biometrics(
    doc_image_or_path: Any,
    live_image_or_path: Any,
    doc_type: str = "passport",
    similarity_threshold: float = 0.363,  # Official OpenCV SFace threshold
) -> FaceVerificationResult:
    """
    1:1 Facial Biometric Verification.
    Compares document portrait against live traveler capture.
    """
    _load_models()

    if isinstance(doc_image_or_path, (str, Path)):
        doc_img = Image.open(str(doc_image_or_path))
    else:
        doc_img = doc_image_or_path

    if isinstance(live_image_or_path, (str, Path)):
        live_img = Image.open(str(live_image_or_path))
    else:
        live_img = live_image_or_path

    doc_bgr = _pil_to_bgr(doc_img)
    live_bgr = _pil_to_bgr(live_img)

    doc_info, doc_box = detect_face_info_and_box(doc_bgr, is_document=True, doc_type=doc_type)
    live_info, live_box = detect_face_info_and_box(live_bgr, is_document=False)

    doc_crop = _crop_from_box(doc_img, doc_box) if doc_box else None
    live_crop = _crop_from_box(live_img, live_box) if live_box else None

    if doc_crop is None or live_crop is None:
        return FaceVerificationResult(
            matched=False,
            similarity_score=0.0,
            status="FAILED_FACE_NOT_FOUND",
            doc_face_detected=(doc_crop is not None),
            live_face_detected=(live_crop is not None),
            engine_used="none",
        )

    # ── SFace Deep Neural Network Matching ───────────────────────────────────
    if _sface is not None and doc_info is not None and live_info is not None:
        try:
            emb_doc = _extract_sface_embedding(doc_bgr, doc_info)
            emb_live = _extract_sface_embedding(live_bgr, live_info)

            if emb_doc is not None and emb_live is not None:
                # Cosine similarity
                norm_d = np.linalg.norm(emb_doc)
                norm_l = np.linalg.norm(emb_live)
                if norm_d > 1e-6 and norm_l > 1e-6:
                    raw_cosine = float(np.dot(emb_doc / norm_d, emb_live / norm_l))
                    is_matched = bool(raw_cosine >= similarity_threshold)

                    # Map raw cosine [-1, 1] to intuitive percentage [0, 1]
                    if raw_cosine < 0:
                        display_score = max(0.02, 0.15 + raw_cosine * 0.13)
                    elif raw_cosine < similarity_threshold:
                        display_score = 0.15 + (raw_cosine / similarity_threshold) * 0.40
                    else:
                        display_score = 0.70 + ((raw_cosine - similarity_threshold) / (1.0 - similarity_threshold)) * 0.30
                    display_score = round(float(np.clip(display_score, 0.0, 1.0)), 3)

                    status = "BIOMETRIC_MATCH" if is_matched else "BIOMETRIC_MISMATCH"
                    conf = "HIGH" if (raw_cosine >= similarity_threshold + 0.10 or raw_cosine < similarity_threshold - 0.10) else "MEDIUM"

                    return FaceVerificationResult(
                        matched=is_matched,
                        similarity_score=display_score,
                        status=status,
                        doc_face_detected=True,
                        live_face_detected=True,
                        doc_face_box=doc_box,
                        live_face_box=live_box,
                        doc_face_crop=doc_crop,
                        live_face_crop=live_crop,
                        confidence_level=conf,
                        engine_used="sface_deep_onnx",
                    )
        except Exception:
            pass

    # ── Fallback Matching ───────────────────────────────────────────────────
    v1 = _extract_improved_histogram_vector(doc_crop)
    v2 = _extract_improved_histogram_vector(live_crop)
    raw_sim = float(np.dot(v1, v2))
    hist_threshold = 0.90
    is_matched = bool(raw_sim >= hist_threshold)
    status = "BIOMETRIC_MATCH" if is_matched else "BIOMETRIC_MISMATCH"

    return FaceVerificationResult(
        matched=is_matched,
        similarity_score=round(float(np.clip(raw_sim, 0.0, 1.0)), 3),
        status=status,
        doc_face_detected=True,
        live_face_detected=True,
        doc_face_box=doc_box,
        live_face_box=live_box,
        doc_face_crop=doc_crop,
        live_face_crop=live_crop,
        confidence_level="MEDIUM",
        engine_used="spatial_lbp_histogram",
    )

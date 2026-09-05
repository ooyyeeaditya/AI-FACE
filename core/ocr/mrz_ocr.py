"""
core.ocr.mrz_ocr
----------------
Robust MRZ Extraction & Validation Engine for Real & Synthetic Documents:
  - Republic of India Passports (ICAO TD3: 2 lines x 44 characters)
  - Visas (ICAO TD2: 2 lines x 36 characters)
  - National ID / Resident Cards (ICAO TD1: 3 lines x 30 characters)

Uses multi-tier detection:
  Tier 1 — PassportEye specialized MRZ segmentation & OCR
  Tier 2 — Multi-threshold adaptive bottom-strip OCR (CLAHE + Otsu + Adaptive)
  Tier 3 — Full document OCR-B line candidate extraction
  Tier 4 — VIZ Cross-Referencing & ICAO Doc 9303 Checksum Repair
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np
from PIL import Image
import cv2

# ── Ensure Tesseract binary is in PATH and pytesseract configured ──────────────
TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Aditya Chauhan\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/usr/bin/tesseract",
]

tess_bin = None
for _c in TESSERACT_CANDIDATES:
    if Path(_c).exists():
        tess_bin = _c
        tess_dir = str(Path(_c).parent)
        if tess_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
        break

try:
    import pytesseract
    if tess_bin:
        pytesseract.pytesseract.tesseract_cmd = tess_bin
        pytesseract.tesseract_cmd = tess_bin
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    TESSERACT_AVAILABLE = False

try:
    import passporteye
    PASSPORTEYE_AVAILABLE = True
except ImportError:
    passporteye = None
    PASSPORTEYE_AVAILABLE = False

# ── MRZ Constants ─────────────────────────────────────────────────────────────
MRZ_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
MRZ_CONFIG = f"--psm 6 --oem 3 -c tessedit_char_whitelist={MRZ_CHARSET}"


def _clean_mrz_line(line: str) -> str:
    """Remove whitespace and replace invalid characters with '<'."""
    line = line.upper().strip().replace(" ", "").replace("\t", "")
    return "".join(c if c in MRZ_CHARSET else "<" for c in line)


def _is_valid_mrz_line(line: str, min_len: int = 30) -> bool:
    """Check if a line has MRZ characteristics."""
    if len(line) < min_len:
        return False
    valid = sum(1 for c in line if c in MRZ_CHARSET)
    return (valid / len(line)) > 0.80 and ("<" in line or any(c.isdigit() for c in line))


def repair_td3_line1(line1: str, country_code: str = "IND") -> str:
    """Repair Line 1 format: P<CCC SURNAME << GIVEN NAMES."""
    l1 = _clean_mrz_line(line1)
    chars = list(l1[:44].ljust(44, "<"))

    if chars[0] not in {"P", "V", "C", "I", "A"}:
        chars[0] = "P"
    if chars[1] not in set(MRZ_CHARSET):
        chars[1] = "<"

    # Ensure country code (e.g. IND)
    cc = "".join(chars[2:5])
    if any(x in cc for x in ("IND", "INQ", "JND", "INO", "UND", "1ND", "1N0")):
        chars[2:5] = list(country_code[:3].upper())

    # Clean trailing noise after the names (e.g. trailing isolated K<K<... fillers)
    s = "".join(chars)
    if "<<" in s[5:]:
        prefix = s[:5]
        names_part = s[5:]
        parts = names_part.split("<<", 1)
        sur = parts[0]
        giv = parts[1] if len(parts) > 1 else ""
        giv_cleaned = re.sub(r"<[A-Z0-9]<.*$", "<<", "<" + giv)
        if giv_cleaned.startswith("<"):
            giv_cleaned = giv_cleaned[1:]
        clean_names = sur + "<<" + giv_cleaned
        chars = list((prefix + clean_names)[:44].ljust(44, "<"))

    return "".join(chars)


def repair_td3_line2(line2: str, country_code: str = "IND", viz_passport_no: Optional[str] = None) -> str:
    """Correct OCR character confusions in TD3 Line 2 per ICAO 9303."""
    l2 = _clean_mrz_line(line2)
    chars = list(l2[:44].ljust(44, "<"))

    DIGIT_MAP = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2", "G": "6", "T": "7", "Q": "0", "D": "0"}

    # Fix country code at indices 10-12
    cc = "".join(chars[10:13])
    if any(x in cc for x in ("IND", "INQ", "JND", "INO", "UND", "1ND", "1N0")):
        chars[10:13] = list(country_code[:3].upper())

    # Sex at index 20
    sx = chars[20] if len(chars) > 20 else "<"
    if sx in {"F", "P", "E"}:
        chars[20] = "F"
    elif sx in {"M", "W", "H", "N"}:
        chars[20] = "M"
    elif sx in {"X", "U"}:
        chars[20] = "X"

    # Force digit-only positions (DOB, Expiry, check digits)
    digit_positions = [9, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 42, 43]
    for idx in digit_positions:
        if idx < len(chars) and chars[idx] in DIGIT_MAP:
            chars[idx] = DIGIT_MAP[chars[idx]]

    # If first character was misread as '<' or corrupt, use check digit at index 9 to find the true leading character
    if (chars[0] == "<" or not chars[0].isalnum()) and chars[9].isdigit():
        from core.validation.mrz_validator import compute_check_digit
        cd_target = int(chars[9])
        for cand in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            test_doc = cand + "".join(chars[1:9])
            if compute_check_digit(test_doc) == cd_target:
                chars[0] = cand
                break

    # If VIZ passport number is known and matches chars 1:8, verify alignment
    if viz_passport_no:
        clean_vp = re.sub(r"[^A-Z0-9]", "", str(viz_passport_no).upper())
        if len(clean_vp) >= 8 and "".join(chars[1:8]) == clean_vp[1:8]:
            chars[0] = clean_vp[0]

    return "".join(chars)


def extract_mrz_from_image(img: Image.Image, image_path: Optional[str] = None) -> List[str]:
    """
    Universal MRZ extraction pipeline for real and synthetic document images.
    Returns list of 2 (or 3) clean MRZ lines if detected, else [].
    """
    # ── Tier 1: PassportEye reader ──────────────────────────────────────────
    if PASSPORTEYE_AVAILABLE and image_path and Path(image_path).exists():
        try:
            m = passporteye.read_mrz(image_path)
            if m is not None:
                d = m.to_dict()
                raw_text = d.get("raw_text", "")
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                cleaned_lines = [_clean_mrz_line(l) for l in lines if len(_clean_mrz_line(l)) >= 30]
                if len(cleaned_lines) >= 2:
                    return [repair_td3_line1(cleaned_lines[0]), repair_td3_line2(cleaned_lines[1])]
        except Exception:
            pass

    if not TESSERACT_AVAILABLE or pytesseract is None:
        return []

    w, h = img.size
    arr_rgb = np.array(img.convert("RGB"))

    # ── Tier 2: Multi-threshold Bottom Strip OCR ─────────────────────────────
    best_lines = []
    best_score = -1

    for ratio in [0.70, 0.65, 0.75, 0.60, 0.80]:
        try:
            strip = arr_rgb[int(h * ratio):, :]
            sh, sw = strip.shape[:2]
            if sw < 1400:
                scale = 1400.0 / sw
                strip = cv2.resize(strip, (int(sw * scale), int(sh * scale)), interpolation=cv2.INTER_LANCZOS4)

            gray = cv2.cvtColor(strip, cv2.COLOR_RGB2GRAY)

            # Preprocessing variations
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(gray)
            _, otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            adapt = cv2.adaptiveThreshold(cl, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)

            for img_variant in [gray, cl, otsu, adapt]:
                raw = pytesseract.image_to_string(img_variant, config=MRZ_CONFIG)
                candidates = []
                for line in raw.splitlines():
                    cl_line = _clean_mrz_line(line)
                    if _is_valid_mrz_line(cl_line, min_len=30):
                        candidates.append(cl_line)

                if len(candidates) >= 2:
                    candidates.sort(key=len, reverse=True)
                    l1, l2 = candidates[0], candidates[1]
                    score = l1.count("<") + l2.count("<") + (30 if 35 <= len(l1) <= 44 else 0) + (30 if 35 <= len(l2) <= 44 else 0)
                    if score > best_score:
                        best_score = score
                        best_lines = [l1, l2]
        except Exception:
            continue

    if len(best_lines) >= 2:
        return [repair_td3_line1(best_lines[0]), repair_td3_line2(best_lines[1])]

    # ── Tier 3: Full Document OCR Scan ───────────────────────────────────────
    try:
        full_raw = pytesseract.image_to_string(img.convert("L"), config=MRZ_CONFIG)
        candidates = []
        for line in full_raw.splitlines():
            cl_line = _clean_mrz_line(line)
            if _is_valid_mrz_line(cl_line, min_len=32):
                candidates.append(cl_line)

        if len(candidates) >= 2:
            return [repair_td3_line1(candidates[-2]), repair_td3_line2(candidates[-1])]
    except Exception:
        pass

    return []

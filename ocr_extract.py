"""
ocr_extract.py
---------------
Module 1: OCR Extraction - for real, from pixels.

No shortcuts: this reads the MRZ strip and the visible "Date of Birth"
field straight off the rendered image using Tesseract, the same engine
family (Tesseract / commercial MRZ readers use the same OCR-then-parse
approach) real document scanners use. Everything downstream (Module 2's
checksum + cross-check) runs on what THIS module actually read, not on
the ground-truth identity object used to generate the specimen.
"""

import re
from datetime import datetime
from pathlib import Path

import pytesseract
from PIL import Image

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for candidate in TESSERACT_CANDIDATES:
    if Path(candidate).exists():
        pytesseract.pytesseract.tesseract_cmd = candidate
        break

MRZ_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
MRZ_TESS_CONFIG = f"--psm 7 -c tessedit_char_whitelist={MRZ_CHARSET}"


def extract_mrz_lines(img: Image.Image, line1_box=(0, 645, 1050, 683),
                       line2_box=(0, 683, 1050, 720)) -> tuple[str, str]:
    """Crop each MRZ line separately and OCR with a restricted character
    set (exactly how real MRZ readers constrain OCR to the ICAO-permitted
    alphabet for reliability). Boxes are derived from the document's known
    layout (mrz_y=H-130, 34px line spacing, font ink offset +6..+25px) --
    the same way a real system uses its template definition to locate the
    MRZ zone before OCR-ing it, rather than guessing at a blind split."""
    def clean(raw: str) -> str:
        return raw.strip().upper().replace(" ", "")

    line1 = clean(pytesseract.image_to_string(img.crop(line1_box).convert("L"), config=MRZ_TESS_CONFIG))
    line2 = clean(pytesseract.image_to_string(img.crop(line2_box).convert("L"), config=MRZ_TESS_CONFIG))

    # Pad/truncate defensively to 44 chars in case OCR drops a trailing '<'
    line1 = (line1 + "<" * 44)[:44]
    line2 = (line2 + "<" * 44)[:44]
    return line1, line2


def extract_field_value(img: Image.Image, box) -> str:
    """OCR a single labeled field's value region (plain text, not MRZ)."""
    crop = img.crop(box).convert("L")
    text = pytesseract.image_to_string(crop, config="--psm 7")
    return text.strip()


def parse_printed_date(text: str):
    """Parse a 'DD MON YYYY' style date as printed on the visible field."""
    text = text.strip().upper().replace(",", "")
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


DIGIT_ONLY_POSITIONS = {9, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 42, 43}
ALPHA_ONLY_POSITIONS = {10, 11, 12}
LETTER_TO_DIGIT = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2"}
DIGIT_TO_LETTER = {v: k for k, v in LETTER_TO_DIGIT.items()}


def correct_ocr_confusions(line2: str) -> str:
    """Real MRZ readers exploit the fact that ICAO 9303 fixes an expected
    character class (digit vs letter) per position in line 2. OCR engines
    routinely confuse O/0, I/1, S/5, B/8, Z/2 -- this doesn't need a model,
    just knowledge of which class is valid at each index, exactly like a
    real MRZ parser does before handing the string to checksum validation."""
    chars = list(line2)
    for i, c in enumerate(chars):
        if i in DIGIT_ONLY_POSITIONS and c in LETTER_TO_DIGIT:
            chars[i] = LETTER_TO_DIGIT[c]
        elif i in ALPHA_ONLY_POSITIONS and c in DIGIT_TO_LETTER:
            chars[i] = DIGIT_TO_LETTER[c]
    return "".join(chars)


if __name__ == "__main__":
    from pathlib import Path
    from mrz_utils import validate_td3_line2
    out_dir = Path(__file__).resolve().parent / "output"

    for name in ["specimen_genuine.png", "specimen_tampered.png"]:
        print(f"=== OCR: {name} ===")
        img = Image.open(out_dir / name)
        l1, l2_raw = extract_mrz_lines(img)
        l2 = correct_ocr_confusions(l2_raw)
        print("  MRZ line 1 (OCR)          :", l1)
        print("  MRZ line 2 (OCR raw)      :", l2_raw)
        print("  MRZ line 2 (class-corrected):", l2, "  [changed]" if l2 != l2_raw else "")

        result = validate_td3_line2(l2)
        print("  Checksum validation      :", result, "-> failures:", result.failures())

        dob_box = (40, 340, 300, 362)
        dob_text = extract_field_value(img, dob_box)
        print("  Printed DOB field (OCR)  :", dob_text)
        print()

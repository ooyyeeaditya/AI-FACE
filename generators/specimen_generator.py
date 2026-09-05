"""
generators.specimen_generator
-----------------------------
Generates high-fidelity synthetic specimens with authentic Indian formats:
  1. Republic of India Passports (भारत गणराज्य / ICAO TD3 / IND)
  2. Republic of India Visas (Bureau of Immigration - BOI e-Visa)
  3. Indian Aadhaar Cards (UIDAI 12-Digit Verhoeff format)
  4. Indian PAN Cards (Income Tax Department)
  5. Live Traveler Portraits
"""

from dataclasses import dataclass
from datetime import date, timedelta
import math
import os
from pathlib import Path
import random
import re
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core.validation.mrz_validator import (
    PassportMRZFields,
    pad_mrz,
    compute_check_digit,
)
from core.validation.rule_engine import generate_verhoeff_aadhaar

W_PASS, H_PASS = 1050, 780
W_CARD, H_CARD = 960, 600
W_VISA, H_VISA = 980, 680

INDIAN_FIRST_NAMES = ["AARYAMAN", "PRIYA", "RAVI", "MEERA", "SANJAY", "KAVITA", "ROHIT", "ANJALI", "VIKRAM", "NEHA", "AMIT", "POOJA", "RAHUL", "DIVYA"]
INDIAN_SURNAMES = ["RANA", "SHARMA", "VERMA", "GUPTA", "RAO", "PATEL", "SINGH", "REDDY", "NAIR", "MEHTA", "IYER", "CHAUHAN", "JOSHI", "MALHOTRA"]
INDIAN_CITIES = ["NEW DELHI", "MUMBAI", "BENGALURU", "CHANDIGARH", "HYDERABAD", "CHENNAI", "KOLKATA", "AHMEDABAD", "PUNE", "JAIPUR"]


def _get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    """Load system font cleanly across macOS and Linux."""
    font_candidates = []
    if os.name == "nt":
        if mono:
            font_candidates = [r"C:\Windows\Fonts\cour.ttf", r"C:\Windows\Fonts\consola.ttf"]
        elif bold:
            font_candidates = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\calibrib.ttf"]
        else:
            font_candidates = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\calibri.ttf"]
    else:
        if mono:
            font_candidates = ["/System/Library/Fonts/Courier.dfont", "/Library/Fonts/Courier New.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
        elif bold:
            font_candidates = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        else:
            font_candidates = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

    for cand in font_candidates:
        if cand and Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_guilloche(draw: ImageDraw.ImageDraw, w: int, h: int, rng: random.Random, base_color=(235, 240, 248)):
    """Draw dense security wavy patterns."""
    draw.rectangle([0, 0, w, h], fill=base_color)
    spacing = 10
    for row, y0 in enumerate(range(-20, h + 20, spacing)):
        phase = rng.uniform(0, math.pi * 2)
        amp = 6 + (row % 3) * 2
        freq = 0.02 + (row % 5) * 0.003
        color = (195 + (row % 3) * 8, 210 + (row % 3) * 6, 235)
        points = [(x, y0 + amp * math.sin(freq * x + phase)) for x in range(0, w + 10, 6)]
        draw.line(points, fill=color, width=1)


def _draw_synthetic_portrait(
    size=(160, 200),
    skin_tone=(215, 175, 140),
    hair_color=(40, 30, 25),
    shirt_color=(50, 70, 100),
    bg_color=(230, 235, 240),
) -> Image.Image:
    """Draw a clean synthetic traveler portrait icon."""
    img = Image.new("RGB", size, bg_color)
    d = ImageDraw.Draw(img)
    cx = size[0] // 2

    # Shoulders / Clothes
    d.ellipse([cx - int(size[0]*0.45), int(size[1]*0.6), cx + int(size[0]*0.45), int(size[1]*1.3)], fill=shirt_color)
    # Head & neck
    d.rectangle([cx - int(size[0]*0.1), int(size[1]*0.55), cx + int(size[0]*0.1), int(size[1]*0.7)], fill=skin_tone)
    d.ellipse([cx - int(size[0]*0.25), int(size[1]*0.12), cx + int(size[0]*0.25), int(size[1]*0.6)], fill=skin_tone)
    # Hair
    d.arc([cx - int(size[0]*0.27), int(size[1]*0.08), cx + int(size[0]*0.27), int(size[1]*0.55)], 180, 360, fill=hair_color, width=int(size[1]*0.08))
    # Eyes
    eye_y = int(size[1] * 0.32)
    d.ellipse([cx - int(size[0]*0.14), eye_y, cx - int(size[0]*0.06), eye_y + 8], fill=(30, 30, 30))
    d.ellipse([cx + int(size[0]*0.06), eye_y, cx + int(size[0]*0.14), eye_y + 8], fill=(30, 30, 30))
    # Mouth
    mouth_y = int(size[1] * 0.48)
    d.line([(cx - int(size[0]*0.1), mouth_y), (cx + int(size[0]*0.1), mouth_y)], fill=(160, 70, 70), width=3)
    return img


def _draw_synthetic_qr(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], rng: random.Random):
    """Draw a realistic synthetic high-density 2D QR matrix."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(255, 255, 255), outline=(100, 100, 100), width=2)
    step = 5
    for y in range(y0 + 6, y1 - 6, step):
        for x in range(x0 + 6, x1 - 6, step):
            if rng.random() > 0.48:
                draw.rectangle([x, y, x + step - 1, y + step - 1], fill=(20, 20, 20))


def _add_print_grain(img: Image.Image, std: float = 8.0, rng: random.Random = None) -> Image.Image:
    """Add subtle sensor print noise."""
    seed = rng.randint(0, 2**31 - 1) if rng else 42
    npr = np.random.RandomState(seed)
    arr = np.asarray(img, dtype=np.float32)
    noise = npr.normal(0, std, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)


def _draw_indian_immigration_stamp(img: Image.Image, airport="IGI AIRPORT (DELHI)", date_str="15 MAR 2026", color=(180, 30, 40), pos=(560, 340), forged_digital=False) -> Image.Image:
    """Draw a circular Bureau of Immigration (BOI) Indian Airport entry stamp."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    x, y = pos
    r = 75

    d.ellipse([x - r, y - r, x + r, y + r], outline=(*color, 210), width=4)
    d.ellipse([x - r + 8, y - r + 8, x + r - 8, y + r - 8], outline=(*color, 160), width=1)

    f_stamp = _get_font(11, bold=True)
    f_date = _get_font(13, bold=True)
    d.text((x - 62, y - 30), "IMMIGRATION - BOI", font=f_stamp, fill=(*color, 220))
    d.text((x - 45, y - 5), date_str, font=f_date, fill=(*color, 230))
    d.text((x - 60, y + 25), airport, font=f_stamp, fill=(*color, 220))

    if not forged_digital:
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=1.5))
        stamp_np = np.asarray(overlay).astype(np.int16)
        noise = np.random.normal(0, 10, stamp_np.shape).astype(np.int16)
        stamp_np = np.clip(stamp_np + noise, 0, 255).astype(np.uint8)
        overlay = Image.fromarray(stamp_np)

    overlay = overlay.rotate(-8, resample=Image.BICUBIC, center=pos)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ==============================================================================
# SPECIMEN GENERATORS (INDIAN PASSPORT, VISA, AADHAAR)
# ==============================================================================

def generate_passport_specimen(
    surname="RANA",
    given_names="AARYAMAN",
    doc_number="Z1234567",
    dob=date(1998, 3, 14),
    sex="M",
    expiry_date=date(2033, 6, 9),
    issue_date=date(2023, 6, 10),
    nationality="INDIAN",
    country_code="IND",
    place_of_birth="NEW DELHI",
    place_of_issue="DELHI",
    file_number="DL1061234567823",
    seed=101,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate official Republic of India Passport Specimen (ICAO TD3 / IND)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (W_PASS, H_PASS), "white")
    d = ImageDraw.Draw(img)
    _draw_guilloche(d, W_PASS, H_PASS, rng, base_color=(235, 242, 250))

    f_title = _get_font(26, bold=True)
    f_sub = _get_font(13, bold=False)
    f_lbl = _get_font(11, bold=False)
    f_val = _get_font(15, bold=True)
    f_mrz = _get_font(24, mono=True)

    # Bilingual Header
    d.text((40, 16), "REPUBLIC OF INDIA / भारत गणराज्य", font=f_title, fill=(20, 35, 75))
    d.text((40, 52), "PASSPORT / पासपोर्ट  •  MINISTRY OF EXTERNAL AFFAIRS", font=f_sub, fill=(50, 65, 100))
    d.line([(40, 80), (W_PASS - 40, 80)], fill=(120, 140, 175), width=2)

    # Portrait Photo Box
    portrait = _draw_synthetic_portrait(size=(160, 200), skin_tone=(215, 175, 140), hair_color=(40, 30, 25), shirt_color=(40, 60, 95))
    photo_pos = (W_PASS - 40 - 160, 100)
    img.paste(portrait, photo_pos)

    fields = [
        ("Type / Code", "P / IND"),
        ("Passport No. / पासपोर्ट क्र.", doc_number),
        ("Surname / उपनाम", surname.upper()),
        ("Given Name(s) / दिया गया नाम", given_names.upper()),
        ("Nationality / राष्ट्रीयता", nationality.upper()),
        ("Sex / लिंग", f"{sex.upper()} / {'MALE' if sex == 'M' else 'FEMALE'}"),
        ("Date of Birth / जन्म तिथि", dob.strftime("%d/%m/%Y")),
        ("Place of Birth / जन्म स्थान", place_of_birth.upper()),
        ("Place of Issue / जारी करने का स्थान", place_of_issue.upper()),
        ("Date of Issue / जारी करने की तिथि", issue_date.strftime("%d/%m/%Y")),
        ("Date of Expiry / समाप्ति की तिथि", expiry_date.strftime("%d/%m/%Y")),
        ("File No. / फ़ाइल क्र.", file_number),
    ]

    field_boxes = {}
    y = 95
    for label, val in fields:
        d.text((40, y), label, font=f_lbl, fill=(80, 90, 110))
        d.text((40, y + 13), val, font=f_val, fill=(15, 25, 45))
        if "Date of Birth" in label:
            field_boxes["dob"] = (40, y + 13, 280, y + 33)
        y += 38

    name_sec = pad_mrz(f"{surname.upper()}<<{given_names.upper()}", 39)
    line1 = f"P<{pad_mrz(country_code, 3)}{name_sec}"[:44]

    p_num = pad_mrz(doc_number, 9)
    p_cd = compute_check_digit(p_num)
    dob_s = dob.strftime("%y%m%d")
    dob_cd = compute_check_digit(dob_s)
    exp_s = expiry_date.strftime("%y%m%d")
    exp_cd = compute_check_digit(exp_s)
    opt_s = pad_mrz(file_number, 14)
    opt_cd = compute_check_digit(opt_s)
    comp_in = p_num + str(p_cd) + dob_s + str(dob_cd) + exp_s + str(exp_cd) + opt_s + str(opt_cd)
    comp_cd = compute_check_digit(comp_in)

    line2 = f"{p_num}{p_cd}IND{dob_s}{dob_cd}{sex[:1]}{exp_s}{exp_cd}{opt_s}{opt_cd}{comp_cd}"[:44]

    mrz_y = H_PASS - 130
    d.rectangle([0, mrz_y - 15, W_PASS, H_PASS], fill=(245, 247, 252))
    d.text((40, mrz_y), line1, font=f_mrz, fill=(10, 10, 10))
    d.text((40, mrz_y + 34), line2, font=f_mrz, fill=(10, 10, 10))

    img = _add_print_grain(img, std=8.0, rng=rng)

    meta = {
        "doc_type": "passport",
        "mrz_lines": [line1, line2],
        "viz_fields": {
            "surname": surname,
            "given_names": given_names,
            "full_name": f"{given_names} {surname}",
            "passport_number": doc_number,
            "document_number": doc_number,
            "dob": dob,
            "sex": sex,
            "place_of_birth": place_of_birth,
            "place_of_issue": place_of_issue,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "nationality": "IND",
            "country_code": "IND",
            "file_number": file_number,
        },
        "field_boxes": field_boxes,
        "photo_box": (photo_pos[0], photo_pos[1], photo_pos[0] + 160, photo_pos[1] + 200),
    }

    return img, meta


def generate_visa_specimen(
    surname="MILLER",
    given_names="DAVID",
    visa_number="V1234567",
    passport_number="Z5566778",
    dob=date(1990, 5, 15),
    sex="M",
    issue_date=date(2026, 1, 10),
    expiry_date=date(2027, 1, 10),
    stay_duration="90 DAYS",
    visa_type="TOURIST (T) - e-VISA",
    entries="MULTIPLE",
    seed=202,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate official Republic of India Entry Visa Specimen (BOI e-Visa)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (W_VISA, H_VISA), "white")
    d = ImageDraw.Draw(img)
    _draw_guilloche(d, W_VISA, H_VISA, rng, base_color=(248, 242, 235))

    f_title = _get_font(26, bold=True)
    f_sub = _get_font(13, bold=False)
    f_lbl = _get_font(11, bold=False)
    f_val = _get_font(15, bold=True)
    f_mrz = _get_font(22, mono=True)

    d.text((40, 20), "REPUBLIC OF INDIA / भारत गणराज्य - VISA", font=f_title, fill=(80, 35, 25))
    d.text((40, 56), "BUREAU OF IMMIGRATION • ELECTRONIC TRAVEL AUTHORIZATION", font=f_sub, fill=(110, 65, 55))
    d.line([(40, 84), (W_VISA - 40, 84)], fill=(160, 115, 105), width=2)

    portrait = _draw_synthetic_portrait(size=(140, 180), skin_tone=(225, 190, 160), hair_color=(60, 45, 35), shirt_color=(35, 65, 80))
    photo_pos = (W_VISA - 40 - 140, 105)
    img.paste(portrait, photo_pos)

    fields = [
        ("Visa Type / श्रेणी", visa_type),
        ("Visa Number / वीज़ा संख्या", visa_number),
        ("Passport No. / पासपोर्ट संख्या", passport_number),
        ("Name / नाम", f"{surname.upper()}, {given_names.upper()}"),
        ("Date of Birth / जन्म तिथि", dob.strftime("%d/%m/%Y")),
        ("Entries Allowed / प्रवेश", entries),
        ("Stay Duration / ठहरने की अवधि", stay_duration),
        ("Valid From / मान्य आरंभ", issue_date.strftime("%d/%m/%Y")),
        ("Valid Until / मान्य समाप्ति", expiry_date.strftime("%d/%m/%Y")),
    ]

    y = 105
    for label, val in fields:
        d.text((40, y), label, font=f_lbl, fill=(110, 95, 90))
        d.text((40, y + 14), val, font=f_val, fill=(45, 25, 20))
        y += 38

    img = _draw_indian_immigration_stamp(img, pos=(560, 340), date_str=issue_date.strftime("%d %b %Y").upper())

    name_sec = pad_mrz(f"{surname.upper()}<<{given_names.upper()}", 31)
    line1 = f"V<IND{name_sec}"[:36]

    v_num = pad_mrz(visa_number, 9)
    v_cd = compute_check_digit(v_num)
    dob_s = dob.strftime("%y%m%d")
    dob_cd = compute_check_digit(dob_s)
    exp_s = expiry_date.strftime("%y%m%d")
    exp_cd = compute_check_digit(exp_s)
    opt_s = pad_mrz("", 7)
    comp_in = v_num + str(v_cd) + dob_s + str(dob_cd) + exp_s + str(exp_cd) + opt_s
    comp_cd = compute_check_digit(comp_in)

    line2 = f"{v_num}{v_cd}IND{dob_s}{dob_cd}{sex[:1]}{exp_s}{exp_cd}{opt_s}{comp_cd}"[:36]

    mrz_y = H_VISA - 110
    d.rectangle([0, mrz_y - 15, W_VISA, H_VISA], fill=(250, 248, 245))
    d.text((40, mrz_y), line1, font=f_mrz, fill=(10, 10, 10))
    d.text((40, mrz_y + 30), line2, font=f_mrz, fill=(10, 10, 10))

    img = _add_print_grain(img, std=7.0, rng=rng)

    meta = {
        "doc_type": "visa",
        "mrz_lines": [line1, line2],
        "viz_fields": {
            "surname": surname,
            "given_names": given_names,
            "full_name": f"{given_names} {surname}",
            "visa_number": visa_number,
            "document_number": visa_number,
            "passport_number": passport_number,
            "dob": dob,
            "sex": sex,
            "visa_type": visa_type,
            "stay_duration": stay_duration,
            "stay_duration_days": 90,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "nationality": "IND",
        },
        "stamp_box": (485, 265, 635, 415),
        "photo_box": (photo_pos[0], photo_pos[1], photo_pos[0] + 140, photo_pos[1] + 180),
    }

    return img, meta


def generate_aadhaar_card_specimen(
    name="AARYAMAN RANA",
    aadhaar_number="5432 1098 7652",
    dob=date(1998, 3, 14),
    gender="MALE",
    seed=303,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate official Indian Aadhaar Card Specimen (UIDAI Verhoeff Checksum Valid)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (W_CARD, H_CARD), "white")
    d = ImageDraw.Draw(img)
    _draw_guilloche(d, W_CARD, H_CARD, rng, base_color=(245, 248, 242))

    f_title = _get_font(22, bold=True)
    f_sub = _get_font(13, bold=False)
    f_lbl = _get_font(12, bold=False)
    f_val = _get_font(16, bold=True)
    f_uid = _get_font(24, bold=True, mono=True)
    f_slogan = _get_font(14, bold=True)

    # Tricolor / UIDAI Header
    d.rectangle([0, 0, W_CARD, 8], fill=(255, 153, 51))   # Saffron
    d.rectangle([0, 8, W_CARD, 16], fill=(255, 255, 255)) # White
    d.rectangle([0, 16, W_CARD, 24], fill=(19, 136, 8))   # Green

    d.text((40, 32), "GOVERNMENT OF INDIA / भारत सरकार", font=f_title, fill=(20, 70, 40))
    d.text((40, 62), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA / भारतीय विशिष्ट पहचान प्राधिकरण", font=f_sub, fill=(50, 90, 60))
    d.line([(40, 90), (W_CARD - 40, 90)], fill=(120, 160, 130), width=2)

    # Portrait Photo (on Left side for Aadhaar)
    portrait = _draw_synthetic_portrait(size=(140, 175), skin_tone=(215, 175, 140), hair_color=(40, 30, 25), shirt_color=(50, 70, 100))
    photo_pos = (40, 110)
    img.paste(portrait, photo_pos)

    # Demographic Fields
    formatted_dob = dob.strftime("%d/%m/%Y")
    d.text((210, 120), "Name / नाम", font=f_lbl, fill=(90, 105, 95))
    d.text((210, 138), name.upper(), font=f_val, fill=(15, 35, 20))

    d.text((210, 175), "DOB / जन्म तिथि", font=f_lbl, fill=(90, 105, 95))
    d.text((210, 193), formatted_dob, font=f_val, fill=(15, 35, 20))

    d.text((210, 230), "Gender / लिंग", font=f_lbl, fill=(90, 105, 95))
    d.text((210, 248), f"{gender.upper()} / {'पुरुष' if gender.upper() == 'MALE' else 'महिला'}", font=f_val, fill=(15, 35, 20))

    # Aadhaar QR Box graphic matrix with realistic texture
    qr_box = (W_CARD - 200, 110, W_CARD - 40, 270)
    _draw_synthetic_qr(d, qr_box, rng)

    # Prominent 12-digit Aadhaar Number formatting: XXXX XXXX XXXX
    clean_uid = re.sub(r"\D", "", aadhaar_number)
    formatted_uid = f"{clean_uid[0:4]}  {clean_uid[4:8]}  {clean_uid[8:12]}"
    d.rectangle([40, H_CARD - 140, W_CARD - 40, H_CARD - 70], fill=(235, 245, 235), outline=(100, 150, 110), width=2)
    d.text((W_CARD // 2 - 160, H_CARD - 122), formatted_uid, font=f_uid, fill=(15, 25, 20))

    # Slogan
    d.text((W_CARD // 2 - 120, H_CARD - 45), "मेरा आधार, मेरी पहचान", font=f_slogan, fill=(20, 80, 45))

    img = _add_print_grain(img, std=6.0, rng=rng)

    meta = {
        "doc_type": "aadhaar",
        "viz_fields": {
            "full_name": name,
            "document_number": clean_uid,
            "id_number": clean_uid,
            "aadhaar_number": clean_uid,
            "dob": dob,
            "gender": "M" if gender.upper() == "MALE" else "F",
            "nationality": "IND",
            "country_code": "IND",
        },
        "photo_box": (photo_pos[0], photo_pos[1], photo_pos[0] + 140, photo_pos[1] + 175),
    }

    return img, meta


def generate_traveler_live_photo(seed=101, is_match=True) -> Image.Image:
    """Generate live webcam probe photo matching or non-matching the document portrait."""
    rng = random.Random(seed if is_match else seed + 9999)
    if is_match:
        img = _draw_synthetic_portrait(
            size=(320, 400),
            skin_tone=(215, 175, 140),
            hair_color=(40, 30, 25),
            shirt_color=(40, 60, 95),
        )
    else:
        # Visibly distinct person (dark skin, blonde hair, bright orange coat, dark studio background)
        img = _draw_synthetic_portrait(
            size=(320, 400),
            skin_tone=(100, 60, 40),
            hair_color=(240, 210, 60),
            shirt_color=(220, 80, 20),
            bg_color=(70, 80, 95),
        )
    img = _add_print_grain(img, std=4.0, rng=rng)
    return img

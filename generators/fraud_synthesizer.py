"""
generators.fraud_synthesizer
----------------------------
Injects realistic fraud, tampering, and counterfeit patterns into Indian
specimens for testing and validation:
  - DOB Text Manipulation (solid-fill patch + font modification)
  - Photo Replacement / Splicing (mismatched portrait with sharp cut-line)
  - Visa Stamp Forgery (digital vector overlay without ink bleed)
  - Expired Indian Passport
  - Indian Bureau of Immigration (BOI) Lookout Circular / Blacklisted Document
  - Tampered Aadhaar Card (Invalid Verhoeff Checksum)
"""

from datetime import date, timedelta
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw

from generators.specimen_generator import (
    generate_passport_specimen,
    generate_visa_specimen,
    generate_aadhaar_card_specimen,
    _draw_synthetic_portrait,
    _draw_indian_immigration_stamp,
    _get_font,
)


def inject_dob_tamper(passport_img: Image.Image, meta: Dict[str, Any], years_offset: int = -8) -> Tuple[Image.Image, Dict[str, Any]]:
    """Simulate solid-fill bitmap text alteration on Date of Birth field."""
    tampered_img = passport_img.copy()
    d = ImageDraw.Draw(tampered_img)

    old_dob: date = meta["viz_fields"]["dob"]
    new_dob = old_dob.replace(year=old_dob.year + years_offset)

    y = 95 + 6 * 38 + 13
    d.rectangle([38, y - 2, 280, y + 20], fill=(255, 255, 255))
    f_val = _get_font(15, bold=True)
    d.text((40, y), new_dob.strftime("%d/%m/%Y"), font=f_val, fill=(15, 25, 45))

    new_meta = dict(meta)
    new_meta["viz_fields"] = dict(meta["viz_fields"])
    new_meta["viz_fields"]["dob"] = new_dob
    new_meta["fraud_injected"] = "DOB_TEXT_MANIPULATION"
    return tampered_img, new_meta


def inject_photo_splice(passport_img: Image.Image, meta: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
    """Simulate photo replacement / splicing with a different portrait & sharp cut-line boundary."""
    tampered_img = passport_img.copy()
    px0, py0, px1, py1 = meta.get("photo_box", (850, 100, 1010, 300))
    w = px1 - px0
    h = py1 - py0

    impostor_portrait = _draw_synthetic_portrait(size=(w, h), skin_tone=(140, 95, 70), hair_color=(210, 180, 60), shirt_color=(180, 30, 30))
    d_p = ImageDraw.Draw(impostor_portrait)
    d_p.rectangle([0, 0, w - 1, h - 1], outline=(40, 40, 40), width=3)
    tampered_img.paste(impostor_portrait, (px0, py0))

    new_meta = dict(meta)
    new_meta["fraud_injected"] = "PHOTO_REPLACEMENT_SPLICE"
    return tampered_img, new_meta


def inject_visa_stamp_forgery(visa_img: Image.Image, meta: Dict[str, Any]) -> Tuple[Image.Image, Dict[str, Any]]:
    """Simulate forged digital visa entry stamp with razor-sharp alpha boundary and no ink bleed."""
    tampered_img = visa_img.copy()
    tampered_img = _draw_indian_immigration_stamp(tampered_img, pos=(560, 340), forged_digital=True, color=(220, 10, 10))

    new_meta = dict(meta)
    new_meta["fraud_injected"] = "STAMP_FORGERY_DIGITAL_OVERLAY"
    return tampered_img, new_meta


def generate_expired_passport() -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate an Indian passport whose expiry date is in the past."""
    img, meta = generate_passport_specimen(
        surname="GUPTA",
        given_names="RAVI",
        doc_number="Z7654321",
        dob=date(1985, 5, 20),
        issue_date=date(2013, 1, 15),
        expiry_date=date(2023, 1, 14),
        seed=404,
    )
    meta["fraud_injected"] = "EXPIRED_DOCUMENT"
    return img, meta


def generate_blacklisted_passport() -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate an Indian passport matching the BOI / CBI Lookout Circular database."""
    img, meta = generate_passport_specimen(
        surname="SINGH",
        given_names="VIKRAM",
        doc_number="Z9876543",
        dob=date(1980, 5, 12),
        issue_date=date(2022, 3, 10),
        expiry_date=date(2032, 3, 9),
        seed=505,
    )
    meta["fraud_injected"] = "BLACKLISTED_BOI_LOC_PASSPORT"
    return img, meta


def generate_tampered_aadhaar() -> Tuple[Image.Image, Dict[str, Any]]:
    """Generate an Aadhaar card with a tampered 12th digit (fails Verhoeff checksum)."""
    # 234567890124 is valid Verhoeff. 234567890129 is invalid Verhoeff!
    img, meta = generate_aadhaar_card_specimen(
        name="AARYAMAN RANA",
        aadhaar_number="2345 6789 0129",
        dob=date(1998, 3, 14),
        gender="MALE",
        seed=606,
    )
    meta["fraud_injected"] = "INVALID_VERHOEFF_AADHAAR"
    return img, meta

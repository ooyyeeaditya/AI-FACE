"""
generate_specimen.py
---------------------
Generates synthetic "training specimen" passport bio-data pages for a
FICTIONAL country (UTOPIA / country code UTO) — the same convention used
by DHS and ICAO training material, precisely so these images can never be
confused with, or misused as, a real government-issued document.

Every specimen is:
  - built from randomly generated fake identities (no real people)
  - stamped with a large diagonal "SPECIMEN" watermark
  - labelled "TRAINING SPECIMEN - NOT A GOVERNMENT DOCUMENT"
  - issued by "UTOPIA", ICAO's standard fictional test country

Two outputs per identity:
  1. A GENUINE specimen: all visible fields + MRZ are internally consistent
     (MRZ check digits validate).
  2. A TAMPERED specimen: one visible field (date of birth) is edited on the
     image WITHOUT regenerating the MRZ underneath it - exactly what an
     amateur forger does, and exactly what Module 2 (MRZ re-validation) and
     Module 3 (visual forensics) are supposed to catch.

This produces matched genuine/tampered training pairs for the tampering
detection classifier, without ever touching a real identity document.
"""

import os
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mrz_utils import PassportMRZFields, build_td3_mrz


def _font_path(*candidates: str) -> str | None:
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _resolve_fonts() -> dict[str, str | None]:
    if os.name == "nt":
        return {
            "regular": _font_path(
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\ARIAL.TTF",
                r"C:\Windows\Fonts\arialregular.ttf",
                r"C:\Windows\Fonts\calibri.ttf",
            ),
            "bold": _font_path(
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\ARIALBD.TTF",
                r"C:\Windows\Fonts\calibrib.ttf",
            ),
            "mono": _font_path(
                r"C:\Windows\Fonts\cour.ttf",
                r"C:\Windows\Fonts\courbd.ttf",
                r"C:\Windows\Fonts\consola.ttf",
                r"C:\Windows\Fonts\lucon.ttf",
            ),
        }

    font_dir = "/usr/share/fonts/truetype/dejavu"
    return {
        "regular": _font_path(f"{font_dir}/DejaVuSans.ttf", f"{font_dir}/DejaVuSansCondensed.ttf"),
        "bold": _font_path(f"{font_dir}/DejaVuSans-Bold.ttf", f"{font_dir}/DejaVuSansCondensed-Bold.ttf"),
        "mono": _font_path(f"{font_dir}/DejaVuSansMono.ttf", f"{font_dir}/DejaVuSansMono.ttf"),
    }


FONT_PATHS = _resolve_fonts()
FONT_REGULAR = FONT_PATHS["regular"]
FONT_BOLD = FONT_PATHS["bold"]
FONT_MONO = FONT_PATHS["mono"]


def _load_font(path: str | None, size: int) -> ImageFont.ImageFont:
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

W, H = 1050, 780
MARGIN = 40

FIRST_NAMES = ["ARUN", "PRIYA", "RAVI", "MEERA", "SANJAY", "KAVITA", "ROHIT", "ANJALI", "VIKRAM", "NEHA"]
SURNAMES = ["SHARMA", "VERMA", "GUPTA", "RAO", "PATEL", "SINGH", "REDDY", "NAIR", "MEHTA", "IYER"]
CITIES = ["NEW DELHI", "SPRINGFIELD", "RIVERTON", "LAKE CITY", "PORT AURORA", "MOUNT VALE"]


@dataclass
class SyntheticIdentity:
    surname: str
    given_names: str
    passport_number: str
    dob: date
    sex: str
    expiry: date
    place_of_birth: str
    date_of_issue: date


def random_identity(rng: random.Random) -> SyntheticIdentity:
    surname = rng.choice(SURNAMES)
    given = rng.choice(FIRST_NAMES)
    passport_number = "U" + "".join(rng.choices("0123456789", k=7)) + rng.choice("ABCXYZ")
    birth_year = rng.randint(1965, 2004)
    dob = date(birth_year, rng.randint(1, 12), rng.randint(1, 28))
    issue = date(2023, rng.randint(1, 12), rng.randint(1, 28))
    expiry = date(issue.year + 10, issue.month, issue.day)
    return SyntheticIdentity(
        surname=surname, given_names=given, passport_number=passport_number,
        dob=dob, sex=rng.choice(["M", "F"]), expiry=expiry,
        place_of_birth=rng.choice(CITIES), date_of_issue=issue,
    )


def _guilloche_background(draw: ImageDraw.ImageDraw, w: int, h: int, rng: random.Random):
    """Dense, evenly-covering wavy-line security-style background (generic,
    not a copy of any real document's pattern). Density matters here: it's
    what gives the local-variance tamper detector a stable baseline texture
    to compare against, the same way a real security-paper microprint does."""
    import math
    base_color = (223, 233, 245)
    draw.rectangle([0, 0, w, h], fill=base_color)
    spacing = 9
    for row, y0 in enumerate(range(-20, h + 20, spacing)):
        phase = rng.uniform(0, math.pi * 2)
        amp = 6 + (row % 3) * 2
        freq = 0.02 + (row % 5) * 0.004
        color = (196 + (row % 3) * 8, 208 + (row % 3) * 6, 232)
        points = [
            (x, y0 + amp * math.sin(freq * x + phase))
            for x in range(0, w + 10, 6)
        ]
        draw.line(points, fill=color, width=1)


def _draw_placeholder_photo(size=(160, 200), rng: random.Random = None) -> Image.Image:
    """Generic abstract silhouette icon (not a real or AI-generated face) to
    stand in for a photo box, avoiding any real/synthetic-likeness concerns."""
    img = Image.new("RGB", size, (235, 235, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0] - 1, size[1] - 1], outline=(120, 120, 120), width=2)
    cx = size[0] // 2
    d.ellipse([cx - 35, 30, cx + 35, 100], fill=(160, 170, 185))  # head
    d.pieslice([cx - 60, 90, cx + 60, 220], 180, 360, fill=(160, 170, 185))  # shoulders
    d.text((size[0] // 2 - 22, size[1] - 22), "SPECIMEN", fill=(150, 40, 40),
            font=_load_font(FONT_BOLD, 11))
    return img


def _add_print_scan_grain(img: Image.Image, std: float = 9.0, rng: random.Random = None) -> Image.Image:
    """Add a uniform, subtle sensor/print-scan noise floor across the whole
    document. Real printed+scanned or camera-captured documents always carry
    this grain; a freshly pasted, digitally-drawn patch (like tamper_dob's
    solid-fill box) will NOT have it, which is exactly the inconsistency
    variance_forensics.py is built to detect. This mirrors real PRNU /
    sensor-noise forensic techniques, simplified for a synthetic demo."""
    seed = rng.randint(0, 2**31 - 1) if rng else 0
    npr = np.random.RandomState(seed)
    arr = np.asarray(img, dtype=np.float32)
    noise = npr.normal(0, std, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)


def _watermark(img: Image.Image, text="SPECIMEN"):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    font = _load_font(FONT_BOLD, 70)
    for y in range(-100, img.size[1] + 100, 160):
        for x in range(-200, img.size[0] + 200, 380):
            txt_layer = Image.new("RGBA", (500, 150), (0, 0, 0, 0))
            td = ImageDraw.Draw(txt_layer)
            td.text((0, 0), text, font=font, fill=(200, 30, 30, 90))
            txt_layer = txt_layer.rotate(28, expand=True)
            overlay.alpha_composite(txt_layer, (x, y))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def render_specimen(identity: SyntheticIdentity, rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    _guilloche_background(d, W, H, rng)

    f_title = _load_font(FONT_BOLD, 30)
    f_sub = _load_font(FONT_REGULAR, 16)
    f_label = _load_font(FONT_REGULAR, 12)
    f_value = _load_font(FONT_BOLD, 17)
    f_mono = _load_font(FONT_MONO, 26)

    d.text((MARGIN, 20), "UTOPIA", font=f_title, fill=(30, 40, 90))
    d.text((MARGIN, 58), "PASSPORT  \u2022  FICTIONAL ICAO TEST COUNTRY (CODE: UTO)", font=f_sub, fill=(60, 70, 110))
    d.line([(MARGIN, 90), (W - MARGIN, 90)], fill=(120, 130, 160), width=2)

    photo = _draw_placeholder_photo(rng=rng)
    photo_pos = (W - MARGIN - photo.width, 110)
    img.paste(photo, photo_pos)

    fields = [
        ("Type / Code", f"P / UTO"),
        ("Passport No.", identity.passport_number),
        ("Surname", identity.surname),
        ("Given Names", identity.given_names),
        ("Nationality", "UTOPIAN"),
        ("Date of Birth", identity.dob.strftime("%d %b %Y").upper()),
        ("Sex", identity.sex),
        ("Place of Birth", identity.place_of_birth),
        ("Date of Issue", identity.date_of_issue.strftime("%d %b %Y").upper()),
        ("Date of Expiry", identity.expiry.strftime("%d %b %Y").upper()),
        ("Authority", "MINISTRY OF SPECIMEN AFFAIRS"),
    ]
    y = 115
    for label, value in fields:
        d.text((MARGIN, y), label.upper(), font=f_label, fill=(90, 95, 110))
        d.text((MARGIN, y + 15), value, font=f_value, fill=(20, 25, 45))
        y += 42

    mrz_fields = PassportMRZFields(
        surname=identity.surname, given_names=identity.given_names,
        passport_number=identity.passport_number, nationality="UTO",
        dob=identity.dob, sex=identity.sex, expiry=identity.expiry,
        country_code="UTO",
    )
    line1, line2 = build_td3_mrz(mrz_fields)

    mrz_y = H - 130
    d.rectangle([0, mrz_y - 15, W, H], fill=(245, 246, 250))
    d.text((MARGIN, mrz_y), line1, font=f_mono, fill=(10, 10, 10))
    d.text((MARGIN, mrz_y + 34), line2, font=f_mono, fill=(10, 10, 10))

    footer_font = _load_font(FONT_REGULAR, 11)
    d.text((MARGIN, H - 18),
           "TRAINING SPECIMEN \u2014 NOT A GOVERNMENT DOCUMENT \u2014 SYNTHETIC DATA \u2014 ICAO FICTIONAL TEST COUNTRY 'UTOPIA'",
           font=footer_font, fill=(150, 30, 30))

    img = _add_print_scan_grain(img, std=9.0, rng=rng)
    img = _watermark(img)
    return img, (line1, line2)


def tamper_dob(img: Image.Image, identity: SyntheticIdentity) -> Image.Image:
    """Simulate the most common real-world amateur forgery: editing a visible
    field (date of birth) directly on the image bitmap WITHOUT regenerating
    the cryptographic/checksum-bearing MRZ underneath. Module 2's MRZ
    re-validation and Module 3's pixel-level forensics should both catch this."""
    tampered = img.copy()
    d = ImageDraw.Draw(tampered)

    # Recompute where the DOB value was drawn (5th field in the list above)
    field_index = 5  # 0-based: Type/Code, Passport No, Surname, Given Names, Nationality, DOB
    y = 115 + field_index * 42 + 15
    new_dob = identity.dob.replace(year=identity.dob.year - 8)  # make them "8 years younger"

    # Paint over the old value and write the new one (classic bitmap edit)
    d.rectangle([MARGIN - 2, y - 2, MARGIN + 260, y + 22], fill=(255, 255, 255))
    f_value = _load_font(FONT_BOLD, 17)
    d.text((MARGIN, y), new_dob.strftime("%d %b %Y").upper(), font=f_value, fill=(20, 25, 45))
    # NOTE: MRZ lines at the bottom are deliberately left untouched -> mismatch
    return tampered


def decode_mrz_dob(line2: str) -> str:
    """Pull the DOB back out of an (untouched) MRZ line 2, YYMMDD -> readable."""
    yy, mm, dd = line2[13:15], line2[15:17], line2[17:19]
    year = int(yy)
    year += 2000 if year < 30 else 1900  # simple pivot, fine for this demo
    return date(year, int(mm), int(dd)).strftime("%d %b %Y").upper()


def main():
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)

    identity = random_identity(rng)
    genuine_img, (line1, line2) = render_specimen(identity, rng)
    genuine_path = out_dir / "specimen_genuine.png"
    genuine_img.save(genuine_path)
    print(f"Saved genuine specimen  -> {genuine_path}")
    print("  MRZ line 1:", line1)
    print("  MRZ line 2:", line2)

    tampered_img = tamper_dob(genuine_img, identity)
    tampered_path = out_dir / "specimen_tampered.png"
    tampered_img.save(tampered_path)
    print(f"Saved tampered specimen -> {tampered_path}")

    # ---- Module 2 style cross-check: printed field vs MRZ-encoded field ----
    mrz_dob = decode_mrz_dob(line2)
    printed_dob_genuine = identity.dob.strftime("%d %b %Y").upper()
    printed_dob_tampered = identity.dob.replace(year=identity.dob.year - 8).strftime("%d %b %Y").upper()

    print("\n--- Field cross-check (visible OCR field vs MRZ-decoded field) ---")
    print(f"Genuine  : printed DOB = {printed_dob_genuine} | MRZ DOB = {mrz_dob} | match = {printed_dob_genuine == mrz_dob}")
    print(f"Tampered : printed DOB = {printed_dob_tampered} | MRZ DOB = {mrz_dob} | match = {printed_dob_tampered == mrz_dob}")
    print("-> The tampered copy has a visible field that disagrees with the")
    print("   untouched MRZ underneath it. This is exactly the signal Module 2")
    print("   should raise as a hard flag, independent of any visual forensics.")

    return identity, genuine_path, tampered_path, line1, line2


if __name__ == "__main__":
    main()

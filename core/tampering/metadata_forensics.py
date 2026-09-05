"""
core.tampering.metadata_forensics
---------------------------------
Analyzes image metadata, EXIF headers, and compression tags for traces of
photo manipulation software (Photoshop, GIMP, Canva, ExifTool).
Excludes legitimate government PDF exporters (Adobe Acrobat, UIDAI PDF Engine).
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ExifTags

# Explicit raster editing and metadata tampering tools
KNOWN_MANIPULATION_SOFTWARE = [
    "PHOTOSHOP", "GIMP", "GNU IMAGE MANIPULATION", "CANVA", "PAINT.NET",
    "PIXELMATOR", "AFFINITY PHOTO", "EXIFTOOL"
]


def extract_image_metadata(image_or_path: Any) -> Dict[str, Any]:
    """Extract raw metadata tags and EXIF attributes from image."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    info = dict(img.info)
    exif_data = {}

    try:
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                exif_data[tag_name] = str(value)
    except Exception:
        pass

    return {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
        "info": info,
        "exif": exif_data,
    }


def analyze_metadata_integrity(image_or_path: Any) -> Dict[str, Any]:
    """Examine image for digital editor signatures and metadata anomalies."""
    meta = extract_image_metadata(image_or_path)
    exif = meta.get("exif", {})
    info = meta.get("info", {})

    detected_software = []
    reasons = []

    # Check Software tag in EXIF
    software_tag = str(exif.get("Software", "")).upper()
    for sw in KNOWN_MANIPULATION_SOFTWARE:
        if sw in software_tag:
            detected_software.append(sw)
            reasons.append(f"EXIF Software tag references image editor {sw}: '{exif.get('Software')}'")

    # Check info dictionary strings
    for k, v in info.items():
        v_str = str(v).upper()
        # Exclude legitimate PDF and viewer tags like "Adobe PDF Library", "Acrobat"
        if "ADOBE PDF" in v_str or "ACROBAT" in v_str:
            continue
        for sw in KNOWN_MANIPULATION_SOFTWARE:
            if sw in v_str and sw not in detected_software:
                detected_software.append(sw)
                reasons.append(f"Image info field '{k}' contains editor trace: {sw}")

    # Check for document scanner / camera provenance
    has_camera_make = "Make" in exif or "Model" in exif
    has_datetime = "DateTimeOriginal" in exif or "DateTime" in exif

    is_suspicious = len(detected_software) > 0

    return {
        "technique": "Metadata & EXIF Forensics",
        "likely_edited_in_software": is_suspicious,
        "detected_software": detected_software,
        "reasons": reasons,
        "has_camera_make": has_camera_make,
        "has_datetime": has_datetime,
        "software_tag": exif.get("Software", "None"),
    }

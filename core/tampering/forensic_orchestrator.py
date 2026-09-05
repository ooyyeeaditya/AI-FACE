"""
core.tampering.forensic_orchestrator
------------------------------------
Orchestrates the complete multi-signal forensic inspection suite:
  1. Error Level Analysis (ELA)
  2. Local Variance & Noise Floor Forensics
  3. Photo Replacement / Splice Detection
  4. Visa Stamp Authenticity Analysis
  5. Image Metadata & Software Signature Forensics
  6. Copy-Move Forgery Detection
Dynamically computes regions of interest on real uploaded documents.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from PIL import Image

from core.tampering.ela import run_ela_analysis
from core.tampering.variance import run_variance_analysis
from core.tampering.photo_splice import detect_photo_splice
from core.tampering.stamp_forgery import analyze_stamp_authenticity
from core.tampering.metadata_forensics import analyze_metadata_integrity
from core.tampering.copy_move import detect_copy_move_forgery


@dataclass
class TamperingReport:
    is_tampered: bool = False
    tamper_confidence: float = 0.0
    ela_result: Dict[str, Any] = field(default_factory=dict)
    variance_result: Dict[str, Any] = field(default_factory=dict)
    photo_splice_result: Dict[str, Any] = field(default_factory=dict)
    stamp_forgery_result: Dict[str, Any] = field(default_factory=dict)
    metadata_result: Dict[str, Any] = field(default_factory=dict)
    copy_move_result: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    heatmap_paths: Dict[str, str] = field(default_factory=dict)


def run_full_forensics(
    image_or_path: Union[str, Path, Image.Image],
    output_dir: Optional[Union[str, Path]] = None,
    field_zone: Optional[Tuple[int, int, int, int]] = None,
    photo_box: Optional[Tuple[int, int, int, int]] = None,
    noise_floor_threshold: float = 3.5,
) -> TamperingReport:
    """Run all 6 tampering detection algorithms and generate visual heatmap overlays dynamically."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path))
    else:
        img = image_or_path

    w, h = img.size

    # Dynamically locate photo box if not provided
    if not photo_box:
        try:
            import cv2
            import numpy as np
            bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
            from core.face.face_engine import detect_face_info_and_box
            _, doc_box = detect_face_info_and_box(bgr, is_document=True)
            if doc_box:
                fx, fy, fw, fh = doc_box
                photo_box = (fx, fy, fx + fw, fy + fh)
            else:
                photo_box = (int(w * 0.78), int(h * 0.12), int(w * 0.96), int(h * 0.42))
        except Exception:
            photo_box = (int(w * 0.78), int(h * 0.12), int(w * 0.96), int(h * 0.42))

    if not field_zone:
        # Dynamically define visual field zone excluding photo box and MRZ strip
        px0, py0, px1, py1 = photo_box
        if px0 > w // 2:
            # Photo is on right side (Passport)
            field_zone = (int(w * 0.04), int(h * 0.10), max(int(w * 0.5), px0 - 20), int(h * 0.70))
        else:
            # Photo is on left side (Aadhaar / ID)
            field_zone = (min(int(w * 0.5), px1 + 20), int(h * 0.10), int(w * 0.95), int(h * 0.70))

    if output_dir:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
    else:
        out_p = None

    stem = Path(str(image_or_path)).stem if isinstance(image_or_path, (str, Path)) else "specimen"

    ela_out = str(out_p / f"{stem}_ela.png") if out_p else None
    var_out = str(out_p / f"{stem}_variance.png") if out_p else None
    splice_out = str(out_p / f"{stem}_splice.png") if out_p else None
    stamp_out = str(out_p / f"{stem}_stamp.png") if out_p else None

    # 1. ELA
    ela_res = run_ela_analysis(image_or_path, out_annotated_path=ela_out)

    # 2. Local Variance
    var_res = run_variance_analysis(
        image_or_path,
        out_annotated_path=var_out,
        region_box=field_zone,
        noise_floor_threshold=noise_floor_threshold,
    )

    # 3. Photo Splice
    splice_res = detect_photo_splice(
        image_or_path,
        photo_box=photo_box,
        out_annotated_path=splice_out,
    )

    # 4. Stamp Forgery
    stamp_res = analyze_stamp_authenticity(image_or_path, out_annotated_path=stamp_out)

    # 5. Metadata
    meta_res = analyze_metadata_integrity(image_or_path)

    # 6. Copy Move
    cm_res = detect_copy_move_forgery(image_or_path)

    # Aggregate signals
    reasons = []
    tamper_flags = 0

    if var_res.get("likely_tampered"):
        tamper_flags += 1
        reasons.append(f"Text manipulation detected: local variance collapse (cluster size {var_res['largest_cluster_size']})")

    if splice_res.get("likely_spliced"):
        tamper_flags += 1
        reasons.append(f"Photo replacement detected: edge gradient anomaly ({splice_res['border_edge_strength']})")

    if stamp_res.get("likely_forged"):
        tamper_flags += 1
        reasons.append("Visa stamp forgery detected: digital overlay / sharp alpha boundary")

    if meta_res.get("likely_edited_in_software"):
        tamper_flags += 1
        reasons.extend(meta_res.get("reasons", []))

    if cm_res.get("likely_cloned"):
        tamper_flags += 1
        reasons.append(f"Copy-move text cloning detected ({cm_res['cloned_block_matches']} matched blocks)")

    if ela_res.get("likely_tampered"):
        reasons.append(f"Error Level Analysis flagged anomalous compression zone (z={ela_res['z_score']})")

    is_tampered = bool(tamper_flags > 0)
    confidence = min(1.0, 0.4 + 0.25 * tamper_flags) if is_tampered else 0.95

    heatmaps = {}
    if ela_out and Path(ela_out).exists():
        heatmaps["ela"] = ela_out
    if var_out and Path(var_out).exists():
        heatmaps["variance"] = var_out
    if splice_out and Path(splice_out).exists():
        heatmaps["photo_splice"] = splice_out
    if stamp_out and Path(stamp_out).exists():
        heatmaps["stamp"] = stamp_out

    return TamperingReport(
        is_tampered=is_tampered,
        tamper_confidence=round(confidence, 3),
        ela_result=ela_res,
        variance_result=var_res,
        photo_splice_result=splice_res,
        stamp_forgery_result=stamp_res,
        metadata_result=meta_res,
        copy_move_result=cm_res,
        reasons=reasons,
        heatmap_paths=heatmaps,
    )

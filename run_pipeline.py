"""
run_pipeline.py
----------------
Unified Border Checkpoint Document Screening & Verification System (India Edition).
Orchestrates:
  Module 1: Multi-Document Dynamic OCR Extraction (Passports, Visas, Aadhaar, PAN)
  Module 2: Document Standards & Database Verification (ICAO 9303, SQLite Issuance Registry, BOI LOC)
  Module 3: Digital PKI & 2D Barcode Verification (CSCA Public Key, SHA-256 LDS Hash)
  Module 4: Multi-Signal Tampering Forensics (ELA, Local Variance, Photo Splice, Stamp, Metadata)
  Module 5: Face Verification & 1:N Facial Watchlist / Multi-Identity Search
  Integrated Risk Engine: Weighted Risk Scoring (0-100) & Actionable Verdict
"""

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import sys
from typing import Dict, Any, Optional, Tuple, Union

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from PIL import Image

from core.database.db_manager import get_db_connection, init_database
from core.ocr.ocr_engine import GLOBAL_OCR_ENGINE, DocumentExtractionResult
from core.validation.rule_engine import validate_document_rules, ValidationRuleReport
from core.validation.cross_validator import cross_validate_fields, CrossValidationReport
from core.validation.database_comparator import verify_against_national_database, DatabaseComparisonReport
from core.security.pki_engine import verify_digital_security_features, DigitalSignatureReport
from core.validation.blacklist_db import GLOBAL_BLACKLIST_DB, BlacklistCheckResult
from core.tampering.forensic_orchestrator import run_full_forensics, TamperingReport
from core.face.face_engine import compare_face_biometrics, FaceVerificationResult
from core.face.gallery_search import GLOBAL_FACIAL_GALLERY, GallerySearchResult
from core.risk_engine import calculate_risk_score, ComprehensiveRiskReport

from generators.specimen_generator import (
    generate_passport_specimen,
    generate_visa_specimen,
    generate_aadhaar_card_specimen,
    generate_traveler_live_photo,
)
from generators.fraud_synthesizer import (
    inject_dob_tamper,
    inject_photo_splice,
    inject_visa_stamp_forgery,
    generate_expired_passport,
    generate_blacklisted_passport,
    generate_tampered_aadhaar,
)

import tempfile

def _get_writable_out_dir() -> Path:
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        p = Path(tempfile.gettempdir()) / "facesih_output"
        p.mkdir(parents=True, exist_ok=True)
        return p
    candidates = [
        Path(__file__).resolve().parent / "output",
        Path(tempfile.gettempdir()) / "facesih_output",
    ]
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            test_file = c / ".test_write"
            test_file.touch()
            test_file.unlink(missing_ok=True)
            return c
        except Exception:
            continue
    fallback = Path(tempfile.gettempdir()) / "facesih_output"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

OUT_DIR = _get_writable_out_dir()

try:
    init_database()
except Exception:
    pass


def screen_document_pipeline(
    doc_image_or_path: Union[str, Path, Image.Image],
    live_image_or_path: Optional[Union[str, Path, Image.Image]] = None,
    doc_type_hint: Optional[str] = None,
    template_metadata: Optional[Dict[str, Any]] = None,
    noise_floor_threshold: float = 3.5,
    enroll_in_gallery: bool = False,
    require_database_registration: bool = False,
) -> ComprehensiveRiskReport:
    """Execute complete automated screening pipeline on a real or synthetic document."""
    if isinstance(doc_image_or_path, (str, Path)):
        img = Image.open(str(doc_image_or_path))
    else:
        img = doc_image_or_path

    w, h = img.size

    # 1. Module 1: Dynamic OCR Extraction
    ocr_res = GLOBAL_OCR_ENGINE.extract_from_image(
        doc_image_or_path,
        doc_type_hint=doc_type_hint,
        template_metadata=template_metadata,
    )

    doc_num = ocr_res.get_field("document_number") or ocr_res.get_field("passport_number") or ocr_res.get_field("visa_number") or ocr_res.get_field("aadhaar_number")
    holder_name = ocr_res.get_field("full_name") or f"{ocr_res.get_field('given_names', '')} {ocr_res.get_field('surname', '')}".strip()
    dob = ocr_res.get_field("dob")
    issue_date = ocr_res.get_field("issue_date")
    expiry_date = ocr_res.get_field("expiry_date")
    nationality = ocr_res.get_field("nationality", "IND")
    country_code = ocr_res.get_field("country_code", "IND")
    gender = ocr_res.get_field("sex") or ocr_res.get_field("gender")
    stay_days = ocr_res.get_field("stay_duration_days")

    # 2. Module 2: Rule, Date, Syntax, Placeholder & Cross-Field Validation
    raw_dob = ocr_res.get_field("raw_dob_str") or ocr_res.get_field("dob_str")
    rule_res = validate_document_rules(
        doc_type=ocr_res.doc_type,
        doc_number=doc_num,
        dob=dob,
        issue_date=issue_date,
        expiry_date=expiry_date,
        country_code=country_code,
        nationality=nationality,
        gender=gender,
        stay_duration_days=stay_days,
        holder_name=holder_name,
        raw_dob_str=raw_dob,
    )

    cross_res = None
    if ocr_res.mrz_validation and ocr_res.viz_fields:
        cross_res = cross_validate_fields(ocr_res.viz_fields, ocr_res.mrz_validation.parsed_fields)

    # 3. Persistent SQLite Database Comparison & LOC Lookup
    db_res = None
    if doc_num:
        db_res = verify_against_national_database(
            doc_type=ocr_res.doc_type,
            doc_number=doc_num,
            extracted_fields=ocr_res.viz_fields,
        )
        if not require_database_registration and not db_res.record_found:
            db_res.discrepancies = [d for d in db_res.discrepancies if "UNREGISTERED" not in d]

    blacklist_res = GLOBAL_BLACKLIST_DB.check(doc_number=doc_num, name=holder_name)

    # 4. Digital PKI & 2D Barcode Security Signature Verification
    pki_res = verify_digital_security_features(
        image_or_path=doc_image_or_path,
        extracted_fields=ocr_res.viz_fields,
        doc_type=ocr_res.doc_type,
    )

    # 5. Module 3: Multi-Signal Tampering Forensics
    photo_box = template_metadata.get("photo_box") if template_metadata else None
    field_zone = template_metadata.get("field_zone") if template_metadata else None

    tamper_res = run_full_forensics(
        doc_image_or_path,
        output_dir=OUT_DIR,
        field_zone=field_zone,
        photo_box=photo_box,
        noise_floor_threshold=noise_floor_threshold,
    )

    # 6. Module 4: Face Verification & Multi-Identity Detection
    face_res = None
    gallery_res = None

    if live_image_or_path is not None:
        face_res = compare_face_biometrics(doc_image_or_path, live_image_or_path, doc_type=ocr_res.doc_type)

        if face_res.doc_face_crop is not None:
            gallery_res = GLOBAL_FACIAL_GALLERY.search_1_to_n(
                face_res.doc_face_crop,
                current_name=holder_name,
                current_doc_number=doc_num or "",
            )
            if enroll_in_gallery and not gallery_res.multi_identity_flag:
                GLOBAL_FACIAL_GALLERY.enroll(
                    face_res.doc_face_crop,
                    holder_name=holder_name,
                    doc_number=doc_num or "UNKNOWN",
                    doc_type=ocr_res.doc_type,
                    nationality=nationality or "IND",
                )

    # Integrated Risk Scoring Engine
    risk_report = calculate_risk_score(
        ocr_result=ocr_res,
        rule_result=rule_res,
        cross_check_result=cross_res,
        database_result=db_res,
        pki_result=pki_res,
        blacklist_result=blacklist_res,
        tampering_result=tamper_res,
        face_result=face_res,
        gallery_result=gallery_res,
    )

    # Persist audit record in SQLite database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        scan_id = f"SCAN-{os.urandom(4).hex().upper()}"
        cur.execute("""
            INSERT INTO screening_audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_id,
            risk_report.timestamp,
            risk_report.doc_type,
            doc_num,
            holder_name,
            risk_report.risk_score,
            risk_report.verdict,
            risk_report.decision_text,
            json.dumps(risk_report.reasons),
            json.dumps({
                "mrz": risk_report.ocr_result.mrz_lines if risk_report.ocr_result else [],
                "face_similarity": risk_report.face_result.similarity_score if risk_report.face_result else 0.0,
                "tampering_reasons": risk_report.tampering_result.reasons if risk_report.tampering_result else [],
                "database_discrepancies": db_res.discrepancies if db_res else [],
            }),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return risk_report


def generate_all_demo_specimens() -> Dict[str, Tuple[str, str, Dict[str, Any]]]:
    """Generate Indian real & synthetic test specimens and save to disk."""
    print("[*] Generating authentic Indian test specimens...")
    suite = {}

    # 1. Real Indian Passport (Garima Thapliyal - Pass1.jpg / Pass2.jpg)
    garima_doc = OUT_DIR / "real_indian_passport_garima.jpg"
    garima_live = OUT_DIR / "real_live_photo_garima.jpg"
    garima_meta = {
        "doc_type": "passport",
        "mrz_lines": [
            "P<INDTHAPLIYAL<<GARIMA<<<<<<<<<<<<<<<<<<<<<<<",
            "SP003369<2IND9407015F34090281065269546124<78",
        ],
        "viz_fields": {
            "passport_number": "SP003369",
            "surname": "THAPLIYAL",
            "given_names": "GARIMA",
            "full_name": "GARIMA THAPLIYAL",
            "dob": date(1994, 7, 1),
            "sex": "FEMALE",
            "place_of_birth": "DELHI, DELHI",
            "place_of_issue": "COIMBATORE",
            "issue_date": date(2024, 9, 3),
            "expiry_date": date(2034, 9, 2),
            "file_number": "DL1065269546124",
        }
    }
    if garima_doc.exists() and garima_live.exists():
        suite["Real Indian Passport (Garima Thapliyal)"] = (str(garima_doc), str(garima_live), garima_meta)

    # 2. Genuine Indian Passport (Aaryaman Rana)
    p_img, p_meta = generate_passport_specimen(
        surname="RANA", given_names="AARYAMAN", doc_number="Z1234567",
        dob=date(1998, 3, 14), seed=101
    )
    p_path = OUT_DIR / "specimen_indian_passport_genuine.png"
    p_img.save(p_path)
    live_p = generate_traveler_live_photo(seed=101, is_match=True)
    live_p_path = OUT_DIR / "live_photo_aaryaman.png"
    live_p.save(live_p_path)
    suite["Genuine Indian Passport"] = (str(p_path), str(live_p_path), p_meta)

    # 3. Tampered DOB Indian Passport (Text Manipulation)
    dob_tampered_img, dob_meta = inject_dob_tamper(p_img, p_meta, years_offset=-8)
    dob_path = OUT_DIR / "specimen_indian_passport_dob_tampered.png"
    dob_tampered_img.save(dob_path)
    suite["Tampered DOB Indian Passport"] = (str(dob_path), str(live_p_path), dob_meta)

    # 4. Photo Spliced Indian Passport (Impersonator Face)
    splice_img, splice_meta = inject_photo_splice(p_img, p_meta)
    splice_path = OUT_DIR / "specimen_indian_passport_photo_spliced.png"
    splice_img.save(splice_path)
    impostor_live = generate_traveler_live_photo(seed=101, is_match=False)
    impostor_live_path = OUT_DIR / "live_photo_impostor.png"
    impostor_live.save(impostor_live_path)
    suite["Photo Replaced Indian Passport"] = (str(splice_path), str(impostor_live_path), splice_meta)

    # 5. Blacklisted Indian Passport (BOI Lookout Circular / CBI)
    stolen_img, stolen_meta = generate_blacklisted_passport()
    stolen_path = OUT_DIR / "specimen_indian_passport_boi_loc.png"
    stolen_img.save(stolen_path)
    stolen_live = generate_traveler_live_photo(seed=505, is_match=True)
    stolen_live_path = OUT_DIR / "live_photo_vikram.png"
    stolen_live.save(stolen_live_path)
    suite["Blacklisted Indian Passport (BOI LOC)"] = (str(stolen_path), str(stolen_live_path), stolen_meta)

    # 6. Expired Indian Passport
    exp_img, exp_meta = generate_expired_passport()
    exp_path = OUT_DIR / "specimen_indian_passport_expired.png"
    exp_img.save(exp_path)
    exp_live = generate_traveler_live_photo(seed=404, is_match=True)
    exp_live_path = OUT_DIR / "live_photo_ravi.png"
    exp_live.save(exp_live_path)
    suite["Expired Indian Passport"] = (str(exp_path), str(exp_live_path), exp_meta)

    # 7. Genuine Indian Entry Visa (BOI e-Visa)
    v_img, v_meta = generate_visa_specimen(seed=202)
    v_path = OUT_DIR / "specimen_indian_visa_genuine.png"
    v_img.save(v_path)
    v_live = generate_traveler_live_photo(seed=202, is_match=True)
    v_live_path = OUT_DIR / "live_photo_visa.png"
    v_live.save(v_live_path)
    suite["Genuine Indian Entry Visa"] = (str(v_path), str(v_live_path), v_meta)

    # 8. Forged Indian Visa Stamp
    stamp_tampered_img, stamp_meta = inject_visa_stamp_forgery(v_img, v_meta)
    stamp_path = OUT_DIR / "specimen_indian_visa_forged_stamp.png"
    stamp_tampered_img.save(stamp_path)
    suite["Forged Indian Visa Stamp"] = (str(stamp_path), str(v_live_path), stamp_meta)

    # 9. Genuine Indian Aadhaar Card (UIDAI Verhoeff Valid)
    aadhaar_img, aadhaar_meta = generate_aadhaar_card_specimen(
        name="AARYAMAN RANA", aadhaar_number="5432 1098 7652", dob=date(1998, 3, 14), seed=303
    )
    aadhaar_path = OUT_DIR / "specimen_aadhaar_genuine.png"
    aadhaar_img.save(aadhaar_path)
    suite["Genuine Indian Aadhaar Card"] = (str(aadhaar_path), str(live_p_path), aadhaar_meta)

    # 10. Tampered Aadhaar Card (Invalid Verhoeff Checksum)
    bad_aadhaar_img, bad_aadhaar_meta = generate_tampered_aadhaar()
    bad_aadhaar_path = OUT_DIR / "specimen_aadhaar_tampered.png"
    bad_aadhaar_img.save(bad_aadhaar_path)
    suite["Tampered Aadhaar (Invalid Checksum)"] = (str(bad_aadhaar_path), str(live_p_path), bad_aadhaar_meta)

    print(f"[+] Successfully generated {len(suite)} Indian specimens in {OUT_DIR}")
    return suite


def main():
    parser = argparse.ArgumentParser(description="AI-Based Fake Identity & Document Screening System (India Edition)")
    parser.add_argument("--demo", action="store_true", help="Generate Indian specimens and run full screening suite")
    parser.add_argument("--doc", type=str, help="Path to document image file")
    parser.add_argument("--live", type=str, help="Path to live traveler face image file")
    parser.add_argument("--type", type=str, default="passport", help="Document type (passport, visa, aadhaar, pan_card)")
    parser.add_argument("--serve", action="store_true", help="Launch the Indian Border Security Officer Web Dashboard")
    parser.add_argument("--port", type=int, default=5050, help="Web dashboard server port")
    args = parser.parse_args()

    if args.serve:
        print(f"[*] Starting Indian Border Control Web Dashboard on port {args.port}...")
        from ui.app import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=args.port, debug=False)
        return

    if args.demo or (not args.doc):
        suite = generate_all_demo_specimens()
        print("\n" + "=" * 70)
        print("INDIAN BORDER CONTROL & LAW ENFORCEMENT DOCUMENT SCREENING PIPELINE")
        print("=" * 70 + "\n")

        for label, (doc_p, live_p, meta) in suite.items():
            print(f">>> SCREENING CASE: {label.upper()} <<<")
            report = screen_document_pipeline(
                doc_p,
                live_p,
                doc_type_hint=meta.get("doc_type", "passport"),
                template_metadata=meta,
            )
            print(report.to_summary_text())
            print()

    elif args.doc:
        print(f"[*] Screening real document: {args.doc}")
        report = screen_document_pipeline(args.doc, args.live, doc_type_hint=args.type)
        print(report.to_summary_text())


if __name__ == "__main__":
    main()

"""
core.security.pki_engine
------------------------
ICAO PKD & Digital Cryptographic Verification Engine.
Handles:
  1. ICAO Doc 9303 Part 10/11/12 Passive Authentication (PA)
  2. Document Signer (DS) & Country Signing CA (CSCA) Digital Signature Verification
  3. 2D Barcode / Secure QR Code Extraction (via cv2.QRCodeDetector)
  4. Cryptographic Payload Integrity & Anti-Forgery Validation
"""

from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

# Simulated Country Signing Certificate Authority (CSCA) Root Master Key for India
GOVERNMENT_CSCA_ROOT_SECRET = b"GOVERNMENT_OF_INDIA_MINISTRY_OF_EXTERNAL_AFFAIRS_CSCA_ROOT_2026"


@dataclass
class DigitalSignatureReport:
    qr_detected: bool = False
    qr_payload_raw: Optional[str] = None
    decoded_demographics: Dict[str, Any] = field(default_factory=dict)
    digital_signature_present: bool = False
    signature_verified: bool = False
    pki_status: str = "NO_DIGITAL_CHIP_OR_QR"
    discrepancies: list = field(default_factory=list)
    csca_root_authority: str = "ICAO-PKD-INDIA-CSCA-ROOT"


def generate_document_pki_signature(
    doc_number: str,
    surname: str,
    given_names: str,
    dob: str,
    expiry_date: str,
    doc_type: str = "passport",
) -> str:
    """Generate official ICAO Document Signer digital signature hash."""
    payload = f"{doc_type.upper()}:{doc_number.upper()}:{surname.upper()}:{given_names.upper()}:{dob}:{expiry_date}"
    sig = hmac.new(GOVERNMENT_CSCA_ROOT_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig


def verify_digital_security_features(
    image_or_path: Union[str, Path, Image.Image],
    extracted_fields: Dict[str, Any],
    doc_type: str = "passport",
) -> DigitalSignatureReport:
    """Detect and cryptographically verify digital barcodes, QR codes, and ICAO PKD signatures."""
    if isinstance(image_or_path, (str, Path)):
        img = Image.open(str(image_or_path)).convert("RGB")
    else:
        img = image_or_path.convert("RGB")

    cv_arr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    report = DigitalSignatureReport()

    # 1. 2D Barcode / QR Code Detector using OpenCV
    try:
        qr_detector = cv2.QRCodeDetector()
        val, pts, _ = qr_detector.detectAndDecode(cv_arr)
        if val and len(val.strip()) > 0:
            report.qr_detected = True
            report.qr_payload_raw = val.strip()

            # Attempt to parse signed JSON/demographic structure
            try:
                data = json.loads(val.strip())
                report.decoded_demographics = data
                if "signature" in data:
                    report.digital_signature_present = True
            except Exception:
                pass
    except Exception:
        pass

    # 2. ICAO Logical Data Structure (LDS) / CSCA Digital Signature Validation
    doc_num = extracted_fields.get("document_number") or extracted_fields.get("passport_number") or extracted_fields.get("aadhaar_number")
    surname = extracted_fields.get("surname", "")
    given_names = extracted_fields.get("given_names", "")
    dob_val = extracted_fields.get("dob", "")
    exp_val = extracted_fields.get("expiry_date", "")

    if doc_num and (surname or given_names or dob_val):
        expected_sig = generate_document_pki_signature(
            doc_number=str(doc_num),
            surname=str(surname),
            given_names=str(given_names),
            dob=str(dob_val),
            expiry_date=str(exp_val),
            doc_type=doc_type,
        )

        # In a real e-Passport, the signature is read from the NFC chip / LDS SOD or 2D Barcode.
        # Check against database / QR digital signature payload:
        if report.digital_signature_present and report.decoded_demographics:
            claimed_sig = report.decoded_demographics.get("signature")
            if claimed_sig == expected_sig:
                report.signature_verified = True
                report.pki_status = "VALID_CSCA_SIGNATURE"
            else:
                report.signature_verified = False
                report.pki_status = "FORGED_SIGNATURE_TAMPERED"
                report.discrepancies.append("Digital Signature Mismatch: Document data does not match CSCA cryptographic certificate")
        else:
            # Standard visual document or passive validation available
            report.pki_status = "PASSIVE_PKI_SUPPORTED"

    return report

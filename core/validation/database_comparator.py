"""
core.validation.database_comparator
-----------------------------------
Authoritative Database Verification Engine.
Compares OCR-extracted fields against official persistent records in:
  - Central Passport Issuance Registry (MEA / ICAO National Database)
  - Bureau of Immigration (BOI) Visa Registry
  - UIDAI Aadhaar Central Identity Repository (CIDR)
  - BOI Lookout Circulars (LOC) & INTERPOL SLTD
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import re
from typing import Dict, Any, List, Optional, Tuple

from core.database.db_manager import get_db_connection


@dataclass
class DatabaseComparisonReport:
    doc_number: str
    doc_type: str
    record_found: bool = False
    is_active: bool = False
    status_in_db: str = "UNKNOWN"
    discrepancies: List[str] = field(default_factory=list)
    db_record: Optional[Dict[str, Any]] = None
    scanned_fields: Optional[Dict[str, Any]] = None
    lookout_circular_hits: List[Dict[str, Any]] = field(default_factory=list)
    interpol_hits: List[Dict[str, Any]] = field(default_factory=list)
    pki_signature_valid: bool = False
    pki_details: str = ""


def verify_against_national_database(
    doc_type: str,
    doc_number: Optional[str],
    extracted_fields: Dict[str, Any],
) -> DatabaseComparisonReport:
    """Compare extracted document data against persistent SQLite government database."""
    clean_doc_num = re.sub(r"[^A-Z0-9]", "", (doc_number or "").upper())
    clean_type = (doc_type or "passport").lower().strip()

    report = DatabaseComparisonReport(
        doc_number=clean_doc_num,
        doc_type=clean_type,
        scanned_fields=extracted_fields,
    )

    if not clean_doc_num:
        report.discrepancies.append("No document number available for database lookup")
        return report

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Query Issuance Registries
    if clean_type == "passport":
        cur.execute("SELECT * FROM issued_passports WHERE passport_number = ?", (clean_doc_num,))
        row = cur.fetchone()
        if row:
            report.record_found = True
            report.db_record = dict(row)
            report.status_in_db = row["status"]
            report.is_active = (row["status"] == "ACTIVE")

            if row["status"] != "ACTIVE":
                report.discrepancies.append(f"National Database Record Status is '{row['status']}' (Document is not active)")

            # Cross-compare fields between Scanned Document and National Registry
            # A. Name Comparison
            scanned_name = extracted_fields.get("full_name") or f"{extracted_fields.get('given_names', '')} {extracted_fields.get('surname', '')}".strip().upper()
            db_name = row["full_name"].strip().upper()
            if scanned_name and scanned_name != db_name:
                report.discrepancies.append(f"Name Mismatch: Scanned '{scanned_name}' != Database '{db_name}'")

            # B. Date of Birth Comparison
            scanned_dob = extracted_fields.get("dob")
            if scanned_dob:
                dob_str = scanned_dob.isoformat() if isinstance(scanned_dob, date) else str(scanned_dob)
                if dob_str != row["dob"]:
                    report.discrepancies.append(f"DOB Alteration Detected: Scanned '{dob_str}' != Database '{row['dob']}'")

            # C. Expiry Date Comparison
            scanned_exp = extracted_fields.get("expiry_date")
            if scanned_exp:
                exp_str = scanned_exp.isoformat() if isinstance(scanned_exp, date) else str(scanned_exp)
                if exp_str != row["expiry_date"]:
                    report.discrepancies.append(f"Expiry Date Mismatch: Scanned '{exp_str}' != Database '{row['expiry_date']}'")

        else:
            report.record_found = False
            report.discrepancies.append(
                f"UNREGISTERED DOCUMENT: Passport '{clean_doc_num}' does not exist in Central Passport Issuance Registry (Suspected Counterfeit)"
            )

    elif clean_type in {"aadhaar", "national_id"}:
        clean_uid = re.sub(r"\D", "", clean_doc_num)
        cur.execute("SELECT * FROM aadhaar_cidr WHERE aadhaar_number = ?", (clean_uid,))
        row = cur.fetchone()
        if row:
            report.record_found = True
            report.db_record = dict(row)
            report.status_in_db = row["status"]
            report.is_active = (row["status"] == "ACTIVE")
            if row["status"] != "ACTIVE":
                report.discrepancies.append(f"UIDAI Database Status is '{row['status']}'")
        else:
            report.record_found = False
            report.discrepancies.append(
                f"UNREGISTERED AADHAAR: Number '{clean_uid}' is not enrolled in UIDAI Central Identity Repository"
            )

    elif clean_type == "visa":
        cur.execute("SELECT * FROM issued_visas WHERE visa_number = ?", (clean_doc_num,))
        row = cur.fetchone()
        if row:
            report.record_found = True
            report.db_record = dict(row)
            report.status_in_db = row["status"]
            report.is_active = (row["status"] == "VALID")
        else:
            report.record_found = False
            report.discrepancies.append(f"UNREGISTERED VISA: Visa '{clean_doc_num}' not found in Bureau of Immigration Registry")

    # 2. Check BOI Lookout Circulars (LOC)
    holder_name = extracted_fields.get("full_name") or f"{extracted_fields.get('given_names', '')} {extracted_fields.get('surname', '')}".strip()
    cur.execute("""
        SELECT * FROM boi_lookout_circulars
        WHERE doc_number = ? OR (name IS NOT NULL AND name = ?)
    """, (clean_doc_num, holder_name.upper() if holder_name else None))
    for r in cur.fetchall():
        report.lookout_circular_hits.append(dict(r))

    # 3. Check INTERPOL SLTD
    cur.execute("SELECT * FROM interpol_sltd WHERE doc_number = ?", (clean_doc_num,))
    for r in cur.fetchall():
        report.interpol_hits.append(dict(r))

    conn.close()
    return report

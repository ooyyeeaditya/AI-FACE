"""
core.validation.rule_engine
---------------------------
Core rule engine for identity documents:
  - Expiry and logical date validity
  - Age calculation and minor travel rules
  - Indian Passport Number syntax (ICAO 9303 / IND)
  - Aadhaar Cards (UIDAI 12-digit Verhoeff Checksum & Structural Rules)
  - PAN Card syntax (Income Tax Dept format)
  - Synthetic / Placeholder / Fake Document Detection (e.g. XXXX, 0000 1111 2222)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import re
from typing import Dict, Any, List, Optional, Tuple

INDIAN_PASSPORT_REGEX = re.compile(r"^[A-Z][0-9]{7}$")
INDIAN_VISA_REGEX = re.compile(r"^[A-Z0-9]{7,12}$")
AADHAAR_REGEX = re.compile(r"^[2-9][0-9]{11}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

KNOWN_PLACEHOLDERS = {
    "XXXX", "TEST", "SAMPLE", "DUMMY", "PLACEHOLDER", "UNKNOWN", "JOHN DOE",
    "FIRSTNAME LASTNAME", "NAME XXXX", "SURNAME", "GIVEN NAME", "XXXX XXXX"
}

KNOWN_FAKE_NUMBERS = {
    "000000000000", "111111111111", "000011112222", "123456789012",
    "999999999999", "123412341234", "00000000", "12345678", "XXXXXXXX"
}

VALID_COUNTRY_CODES = {
    "IND", "USA", "GBR", "CAN", "AUS", "DEU", "FRA", "SGP", "ARE",
    "JPN", "CHN", "NZL", "MYS", "THA", "RUS", "BRA", "ZAF", "NPL", "BGD", "LKA"
}


# VERHOEFF ALGORITHM (Official UIDAI Aadhaar 12-Digit Checksum)
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff_aadhaar(aadhaar_str: str) -> bool:
    """Validate 12-digit Aadhaar number using UIDAI's official Verhoeff checksum."""
    clean = re.sub(r"\D", "", aadhaar_str)
    if len(clean) != 12 or clean.startswith(('0', '1')):
        return False
    c = 0
    reversed_digits = [int(x) for x in reversed(clean)]
    for i, digit in enumerate(reversed_digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    return c == 0


def generate_verhoeff_aadhaar(base_11_digits: str) -> str:
    """Compute and append the 12th Verhoeff checksum digit to an 11-digit base."""
    clean = re.sub(r"\D", "", base_11_digits)[:11]
    c = 0
    reversed_digits = [int(x) for x in reversed(clean)]
    for i, digit in enumerate(reversed_digits, start=1):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    check_digit = _VERHOEFF_INV[c]
    return f"{clean}{check_digit}"


@dataclass
class ValidationRuleReport:
    is_valid: bool = True
    is_expired: bool = False
    days_until_expiry: Optional[int] = None
    calculated_age: Optional[int] = None
    is_minor: bool = False
    date_logic_ok: bool = True
    country_code_ok: bool = True
    format_syntax_ok: bool = True
    stay_duration_ok: bool = True
    national_id_valid: bool = True
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_document_rules(
    doc_type: str,
    doc_number: Optional[str] = None,
    dob: Optional[date] = None,
    issue_date: Optional[date] = None,
    expiry_date: Optional[date] = None,
    country_code: Optional[str] = None,
    nationality: Optional[str] = None,
    gender: Optional[str] = None,
    stay_duration_days: Optional[int] = None,
    holder_name: Optional[str] = None,
    raw_dob_str: Optional[str] = None,
    reference_date: Optional[date] = None,
) -> ValidationRuleReport:
    """Validate logical consistency, date bounds, format rules, and Indian standards."""
    if reference_date is None:
        reference_date = date.today()

    report = ValidationRuleReport()
    doc_type_clean = (doc_type or "passport").lower().strip()
    doc_num_clean = re.sub(r"[^A-Z0-9]", "", (doc_number or "").upper())

    # 1. Check for Missing Credentials
    if not doc_num_clean:
        report.is_valid = False
        report.format_syntax_ok = False
        report.issues.append("Unparseable / Missing Document Number: No valid credential ID detected")

    # 2. Check for Synthetic / Placeholder Identity
    if holder_name:
        h_upper = holder_name.upper().strip()
        for p in KNOWN_PLACEHOLDERS:
            if p in h_upper:
                report.is_valid = False
                report.issues.append(f"Synthetic / Placeholder Name detected: '{holder_name}'")
                break

    if raw_dob_str:
        r_upper = str(raw_dob_str).upper()
        if any(p in r_upper for p in ["XX", "00-00", "DD-MM", "YYYY", "0000"]):
            report.is_valid = False
            report.date_logic_ok = False
            report.issues.append(f"Synthetic / Placeholder Date of Birth detected: '{raw_dob_str}'")

    if doc_num_clean in KNOWN_FAKE_NUMBERS or (len(doc_num_clean) >= 8 and len(set(doc_num_clean)) <= 2):
        report.is_valid = False
        report.format_syntax_ok = False
        report.issues.append(f"Obvious Dummy / Fake Number Pattern detected: '{doc_num_clean}'")

    # 3. Document Expiry Checks
    if expiry_date:
        delta = (expiry_date - reference_date).days
        report.days_until_expiry = delta
        if delta < 0:
            report.is_expired = True
            report.is_valid = False
            report.issues.append(f"Document is EXPIRED (Expired {abs(delta)} days ago on {expiry_date})")
        elif delta < 180:
            report.warnings.append(f"Document expires soon ({delta} days remaining - requires >= 6 months for entry)")

    # 4. Date Logic Checks
    if dob and issue_date:
        if issue_date < dob:
            report.date_logic_ok = False
            report.is_valid = False
            report.issues.append(f"Issue date ({issue_date}) is earlier than Date of Birth ({dob})")

    if issue_date and expiry_date:
        if expiry_date <= issue_date:
            report.date_logic_ok = False
            report.is_valid = False
            report.issues.append(f"Expiry date ({expiry_date}) is earlier than or equal to Issue date ({issue_date})")

    # 5. Age & Minor Checks
    if dob:
        age_years = reference_date.year - dob.year - (
            (reference_date.month, reference_date.day) < (dob.month, dob.day)
        )
        report.calculated_age = age_years
        if age_years < 0 or age_years > 120:
            report.date_logic_ok = False
            report.is_valid = False
            report.issues.append(f"Unrealistic date of birth: calculated age is {age_years} years")
        elif age_years < 18:
            report.is_minor = True
            report.warnings.append(f"Traveler is a minor (Age: {age_years}) - requires parental authorization")

    # 6. Country & Nationality
    if country_code:
        cc = country_code.strip().upper()
        if cc not in VALID_COUNTRY_CODES and cc not in {"IND", "UTO"}:
            report.country_code_ok = False
            report.warnings.append(f"Non-standard issuing country code: {country_code}")

    # 7. Dedicated Indian Document Syntax Validation
    if doc_type_clean == "passport":
        if country_code in {"IND", "UTO"} or not country_code:
            if doc_num_clean and not INDIAN_PASSPORT_REGEX.match(doc_num_clean) and len(doc_num_clean) != 8:
                report.format_syntax_ok = False
                report.warnings.append(f"Passport number '{doc_num_clean}' does not match standard 8-char Indian format")

    elif doc_type_clean in {"national_id", "aadhaar", "aadhaar_card"}:
        clean_uid = re.sub(r"\D", "", doc_number or "")
        if not clean_uid or len(clean_uid) != 12:
            report.national_id_valid = False
            report.is_valid = False
            report.issues.append(f"Aadhaar Number '{doc_number}' is invalid (Must be exactly 12 digits)")
        else:
            if clean_uid.startswith(('0', '1')):
                report.national_id_valid = False
                report.is_valid = False
                report.issues.append(f"Aadhaar Number cannot start with '{clean_uid[0]}' (UIDAI rule requires 2-9)")
            elif not validate_verhoeff_aadhaar(clean_uid):
                report.national_id_valid = False
                report.is_valid = False
                report.issues.append(f"Aadhaar checksum validation FAILED (Invalid Verhoeff digit for {clean_uid})")

    elif doc_type_clean == "pan_card":
        if not PAN_REGEX.match(doc_num_clean):
            report.national_id_valid = False
            report.is_valid = False
            report.issues.append(f"PAN format invalid '{doc_num_clean}' (Must be 5 letters + 4 digits + 1 letter)")

    elif doc_type_clean == "visa":
        if not INDIAN_VISA_REGEX.match(doc_num_clean):
            report.format_syntax_ok = False
            report.warnings.append(f"Visa number format '{doc_num_clean}' is non-standard")

    if report.issues:
        report.is_valid = False

    return report

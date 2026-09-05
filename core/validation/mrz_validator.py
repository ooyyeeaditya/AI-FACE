"""
core.validation.mrz_validator
-----------------------------
Comprehensive ICAO Doc 9303 check-digit computation and validation engine
supporting all standard Machine Readable Travel Document (MRTD) formats:
  - TD1 (3 lines x 30 chars): ID cards, Residence Permits, Border Crosser Cards
  - TD2 (2 lines x 36 chars): Official Travel Documents, Visas (MRV-B)
  - TD3 (2 lines x 44 chars): Standard Passports, Visas (MRV-A)

Implements the official ICAO 7-3-1 modulus 10 weighting algorithm.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import re
from typing import Optional, Tuple, List, Dict, Any

WEIGHTS = [7, 3, 1]


@dataclass
class PassportMRZFields:
    surname: str
    given_names: str
    passport_number: str
    nationality: str
    dob: date
    sex: str
    expiry: date
    country_code: str
    personal_number: str = ""


def char_value(c: str) -> int:
    """Map a single MRZ character to its numeric value per ICAO 9303."""
    if c == "<":
        return 0
    if c.isdigit():
        return int(c)
    if c.isalpha():
        return ord(c.upper()) - ord("A") + 10
    raise ValueError(f"Invalid ICAO MRZ character: {c!r}")


def compute_check_digit(data: str) -> int:
    """Compute the ICAO 9303 check digit using weights 7, 3, 1 repeating."""
    total = 0
    for i, c in enumerate(data):
        total += char_value(c) * WEIGHTS[i % 3]
    return total % 10


def verify_check_digit(data: str, digit: str) -> bool:
    """Verify check digit against computed value. Allows '<' if data is empty/fillers."""
    if digit == "<":
        return data.strip("<") == ""
    if not digit.isdigit():
        return False
    return compute_check_digit(data) == int(digit)


def pad_mrz(s: str, length: int) -> str:
    cleaned = re.sub(r"[^A-Z0-9<]", "<", str(s).upper())[:length]
    return cleaned + "<" * (length - len(cleaned))


def parse_mrz_date(yy_mm_dd: str, is_dob: bool = False) -> Optional[date]:
    """Parse YYMMDD string from MRZ with century pivot logic."""
    cleaned = yy_mm_dd.strip("<")
    if len(cleaned) != 6 or not cleaned.isdigit():
        return None
    yy = int(cleaned[0:2])
    mm = int(cleaned[2:4])
    dd = int(cleaned[4:6])

    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None

    current_century = (datetime.now().year // 100) * 100
    if is_dob:
        current_yy = datetime.now().year % 100
        century = (current_century - 100) if yy > current_yy else current_century
    else:
        century = current_century if yy < 80 else (current_century - 100)

    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def build_td3_mrz(f: PassportMRZFields) -> Tuple[str, str]:
    """Build ICAO TD3 MRZ lines from fields."""
    name_field = f"{f.surname.upper()}<<{f.given_names.upper()}".replace(" ", "<")
    line1 = "P<" + pad_mrz(f.country_code.upper(), 3) + pad_mrz(name_field, 39)
    line1 = pad_mrz(line1, 44)

    passport_no = pad_mrz(f.passport_number.upper(), 9)
    passport_cd = compute_check_digit(passport_no)

    dob_str = f.dob.strftime("%y%m%d")
    dob_cd = compute_check_digit(dob_str)

    expiry_str = f.expiry.strftime("%y%m%d")
    expiry_cd = compute_check_digit(expiry_str)

    personal_no = pad_mrz(f.personal_number, 14)
    personal_cd = compute_check_digit(personal_no)

    composite_input = (
        passport_no + str(passport_cd) + dob_str + str(dob_cd) +
        expiry_str + str(expiry_cd) + personal_no + str(personal_cd)
    )
    composite_cd = compute_check_digit(composite_input)

    line2 = (
        passport_no + str(passport_cd) +
        pad_mrz(f.nationality.upper(), 3) +
        dob_str + str(dob_cd) +
        f.sex.upper()[:1] +
        expiry_str + str(expiry_cd) +
        personal_no + str(personal_cd) +
        str(composite_cd)
    )
    line2 = pad_mrz(line2, 44)
    return line1, line2


@dataclass
class MRZValidationResult:
    doc_format: str
    document_number_ok: bool = True
    dob_ok: bool = True
    expiry_ok: bool = True
    optional_data_ok: bool = True
    composite_ok: bool = True
    raw_lines: List[str] = field(default_factory=list)
    parsed_fields: Dict[str, Any] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return (
            self.document_number_ok
            and self.dob_ok
            and self.expiry_ok
            and self.optional_data_ok
            and self.composite_ok
        )

    def evaluate_failures(self) -> List[str]:
        fails = []
        if not self.document_number_ok:
            fails.append("Document number check digit mismatch")
        if not self.dob_ok:
            fails.append("Date-of-birth check digit mismatch")
        if not self.expiry_ok:
            fails.append("Expiry date check digit mismatch")
        if not self.optional_data_ok:
            fails.append("Optional/Personal number check digit mismatch")
        if not self.composite_ok:
            fails.append("Composite (overall) check digit mismatch")
        self.failures = fails
        return fails


def validate_td3(lines: List[str]) -> MRZValidationResult:
    """Validate standard 2-line x 44-char Passport MRZ."""
    if len(lines) < 2:
        res = MRZValidationResult(doc_format="TD3", raw_lines=lines)
        res.document_number_ok = res.dob_ok = res.expiry_ok = res.composite_ok = False
        res.evaluate_failures()
        return res

    line1 = pad_mrz(lines[0].strip(), 44)
    line2 = pad_mrz(lines[1].strip(), 44)

    doc_code = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    name_section = line1[5:44]
    name_parts = name_section.split("<<", 1)
    surname = name_parts[0].replace("<", " ").strip()
    given_names = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""

    doc_no = line2[0:9]
    doc_no_cd = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob_str = line2[13:19]
    dob_cd = line2[19]
    sex = line2[20].replace("<", "X")
    expiry_str = line2[21:27]
    expiry_cd = line2[27]
    optional_data = line2[28:42]
    optional_cd = line2[42]
    composite_cd = line2[43]

    doc_no_ok = verify_check_digit(doc_no, doc_no_cd)
    dob_ok = verify_check_digit(dob_str, dob_cd)
    expiry_ok = verify_check_digit(expiry_str, expiry_cd)
    optional_ok = verify_check_digit(optional_data, optional_cd)

    composite_input = (
        doc_no + doc_no_cd + dob_str + dob_cd + expiry_str + expiry_cd + optional_data + optional_cd
    )
    composite_ok = verify_check_digit(composite_input, composite_cd)

    parsed = {
        "document_type": doc_code,
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "full_name": f"{given_names} {surname}".strip(),
        "document_number": doc_no.replace("<", "").strip(),
        "nationality": nationality,
        "dob": parse_mrz_date(dob_str, is_dob=True),
        "dob_str": dob_str,
        "sex": sex,
        "expiry_date": parse_mrz_date(expiry_str, is_dob=False),
        "expiry_str": expiry_str,
        "optional_data": optional_data.replace("<", "").strip(),
    }

    result = MRZValidationResult(
        doc_format="TD3",
        document_number_ok=doc_no_ok,
        dob_ok=dob_ok,
        expiry_ok=expiry_ok,
        optional_data_ok=optional_ok,
        composite_ok=composite_ok,
        raw_lines=[line1, line2],
        parsed_fields=parsed,
    )
    result.evaluate_failures()
    return result


def validate_td2(lines: List[str]) -> MRZValidationResult:
    """Validate 2-line x 36-char Visa / Travel Document MRZ (MRV-B)."""
    if len(lines) < 2:
        res = MRZValidationResult(doc_format="TD2", raw_lines=lines)
        res.document_number_ok = res.dob_ok = res.expiry_ok = res.composite_ok = False
        res.evaluate_failures()
        return res

    line1 = pad_mrz(lines[0].strip(), 36)
    line2 = pad_mrz(lines[1].strip(), 36)

    doc_code = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    name_section = line1[5:36]
    name_parts = name_section.split("<<", 1)
    surname = name_parts[0].replace("<", " ").strip()
    given_names = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""

    doc_no = line2[0:9]
    doc_no_cd = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob_str = line2[13:19]
    dob_cd = line2[19]
    sex = line2[20].replace("<", "X")
    expiry_str = line2[21:27]
    expiry_cd = line2[27]
    optional_data = line2[28:35]
    composite_cd = line2[35]

    doc_no_ok = verify_check_digit(doc_no, doc_no_cd)
    dob_ok = verify_check_digit(dob_str, dob_cd)
    expiry_ok = verify_check_digit(expiry_str, expiry_cd)

    composite_input = (
        doc_no + doc_no_cd + dob_str + dob_cd + expiry_str + expiry_cd + optional_data
    )
    composite_ok = verify_check_digit(composite_input, composite_cd)

    parsed = {
        "document_type": doc_code,
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "full_name": f"{given_names} {surname}".strip(),
        "document_number": doc_no.replace("<", "").strip(),
        "nationality": nationality,
        "dob": parse_mrz_date(dob_str, is_dob=True),
        "dob_str": dob_str,
        "sex": sex,
        "expiry_date": parse_mrz_date(expiry_str, is_dob=False),
        "expiry_str": expiry_str,
        "optional_data": optional_data.replace("<", "").strip(),
    }

    result = MRZValidationResult(
        doc_format="TD2",
        document_number_ok=doc_no_ok,
        dob_ok=dob_ok,
        expiry_ok=expiry_ok,
        optional_data_ok=True,
        composite_ok=composite_ok,
        raw_lines=[line1, line2],
        parsed_fields=parsed,
    )
    result.evaluate_failures()
    return result


def validate_td1(lines: List[str]) -> MRZValidationResult:
    """Validate 3-line x 30-char National ID / Residence Permit MRZ."""
    if len(lines) < 3:
        res = MRZValidationResult(doc_format="TD1", raw_lines=lines)
        res.document_number_ok = res.dob_ok = res.expiry_ok = res.composite_ok = False
        res.evaluate_failures()
        return res

    line1 = pad_mrz(lines[0].strip(), 30)
    line2 = pad_mrz(lines[1].strip(), 30)
    line3 = pad_mrz(lines[2].strip(), 30)

    doc_code = line1[0:2].replace("<", "")
    issuing_country = line1[2:5].replace("<", "")
    doc_no = line1[5:14]
    doc_no_cd = line1[14]
    opt1 = line1[15:30]

    dob_str = line2[0:6]
    dob_cd = line2[6]
    sex = line2[7].replace("<", "X")
    expiry_str = line2[8:14]
    expiry_cd = line2[14]
    nationality = line2[15:18].replace("<", "")
    opt2 = line2[18:29]
    composite_cd = line2[29]

    name_section = line3[0:30]
    name_parts = name_section.split("<<", 1)
    surname = name_parts[0].replace("<", " ").strip()
    given_names = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""

    doc_no_ok = verify_check_digit(doc_no, doc_no_cd)
    dob_ok = verify_check_digit(dob_str, dob_cd)
    expiry_ok = verify_check_digit(expiry_str, expiry_cd)

    composite_input = (
        doc_no + doc_no_cd + opt1 + dob_str + dob_cd + expiry_str + expiry_cd + opt2
    )
    composite_ok = verify_check_digit(composite_input, composite_cd)

    parsed = {
        "document_type": doc_code,
        "issuing_country": issuing_country,
        "surname": surname,
        "given_names": given_names,
        "full_name": f"{given_names} {surname}".strip(),
        "document_number": doc_no.replace("<", "").strip(),
        "nationality": nationality,
        "dob": parse_mrz_date(dob_str, is_dob=True),
        "dob_str": dob_str,
        "sex": sex,
        "expiry_date": parse_mrz_date(expiry_str, is_dob=False),
        "expiry_str": expiry_str,
        "optional_data": (opt1 + opt2).replace("<", "").strip(),
    }

    result = MRZValidationResult(
        doc_format="TD1",
        document_number_ok=doc_no_ok,
        dob_ok=dob_ok,
        expiry_ok=expiry_ok,
        optional_data_ok=True,
        composite_ok=composite_ok,
        raw_lines=[line1, line2, line3],
        parsed_fields=parsed,
    )
    result.evaluate_failures()
    return result


def auto_validate_mrz(mrz_lines: List[str]) -> MRZValidationResult:
    """Automatically detect MRZ format (TD1, TD2, TD3) and run validation."""
    cleaned = [line.strip().replace(" ", "") for line in mrz_lines if line.strip()]
    if len(cleaned) == 3 and all(len(l) >= 28 for l in cleaned):
        return validate_td1(cleaned)
    elif len(cleaned) == 2:
        max_len = max(len(l) for l in cleaned)
        if max_len >= 40:
            return validate_td3(cleaned)
        else:
            return validate_td2(cleaned)
    elif len(cleaned) >= 2:
        return validate_td3(cleaned[:2])
    else:
        res = MRZValidationResult(doc_format="UNKNOWN", raw_lines=cleaned)
        res.document_number_ok = res.dob_ok = res.expiry_ok = res.composite_ok = False
        res.evaluate_failures()
        return res

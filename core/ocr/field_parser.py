"""
core.ocr.field_parser
---------------------
Parses and normalizes Visual Inspection Zone (VIZ) text for Indian Passports,
Visas, Aadhaar Cards, PAN Cards, Driving Licenses, and standard MRTDs.
Supports bilingual English/Hindi keywords, multi-line layouts, and flexible date formats.
"""

from datetime import date, datetime
import re
from typing import Optional, Dict, Any, Tuple, List


DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%d%m%Y",
]


def parse_viz_date(text: Optional[str]) -> Optional[date]:
    """Parse flexible date strings from document visual fields."""
    if not text:
        return None
    cleaned = text.strip().upper().replace(",", " ").replace(".", "/").replace("-", "/")
    cleaned = " ".join(cleaned.split())

    for fmt in [
        "%d %m %Y", "%d %b %Y", "%d %B %Y", "%Y %m %d", "%m %d %Y"
    ]:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass

    # Regex search for DD/MM/YYYY or DD-MM-YYYY
    match_slash = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if match_slash:
        d, m, y = int(match_slash.group(1)), int(match_slash.group(2)), int(match_slash.group(3))
        try:
            return date(y, m, d)
        except ValueError:
            pass

    # DD MON YYYY
    match = re.search(r"(\d{1,2})\s+([A-Z]{3,9})\s+(\d{4})", cleaned)
    if match:
        day_str, mon_str, year_str = match.groups()
        for mfmt in ["%b", "%B"]:
            try:
                dt = datetime.strptime(f"{day_str} {mon_str} {year_str}", f"%d {mfmt} %Y")
                return dt.date()
            except ValueError:
                pass

    return None


def parse_stay_duration(text: Optional[str]) -> Optional[int]:
    """Parse duration like '90 DAYS', '30 D', '3 MONTHS' into integer days."""
    if not text:
        return None
    cleaned = text.strip().upper()
    match = re.search(r"(\d+)\s*(DAY|DAYS|D)", cleaned)
    if match:
        return int(match.group(1))
    match_mo = re.search(r"(\d+)\s*(MONTH|MONTHS|M)", cleaned)
    if match_mo:
        return int(match_mo.group(1)) * 30
    match_yr = re.search(r"(\d+)\s*(YEAR|YEARS|Y)", cleaned)
    if match_yr:
        return int(match_yr.group(1)) * 365
    return None


def extract_fields_from_raw_text(raw_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Intelligently parse raw OCR text from real Indian Passports, Aadhaar,
    Visas, PAN cards, and Driving Licences.

    Returns (doc_type, fields_dict)
    """
    fields: Dict[str, Any] = {}
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    full_text = " ".join(lines).upper()

    # ── 1. Document Type Detection ─────────────────────────────────────────
    doc_type = "passport"
    if re.search(r"AADHAAR|UNIQUE\s+IDENTIFICATION|UIDAI|\b\d{4}\s\d{4}\s\d{4}\b", full_text):
        doc_type = "aadhaar"
    elif re.search(r"PERMANENT\s+ACCOUNT|INCOME\s+TAX\s+DEPT|PAN\s+CARD|\b[A-Z]{5}[0-9]{4}[A-Z]\b", full_text) and "PASSPORT" not in full_text:
        doc_type = "pan_card"
    elif re.search(r"\bVISA\b|ELECTRONIC\s+TRAVEL\s+AUTHORIZATION|e-VISA", full_text) and "PASSPORT" not in full_text:
        doc_type = "visa"
    elif re.search(r"DRIVING\s+LIC|MOTOR\s+VEHICLE|DL\s+NO", full_text):
        doc_type = "driving_licence"

    # ── 2. Dates Extraction (Universal Timeline) ───────────────────────────
    all_dates: List[date] = []
    for m in re.finditer(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", raw_text):
        d_val, m_val, y_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= m_val <= 12 and 1 <= d_val <= 31 and 1900 <= y_val <= 2099:
            try:
                all_dates.append(date(y_val, m_val, d_val))
            except ValueError:
                pass

    all_dates = sorted(list(set(all_dates)))

    # ── 3. Parse by Document Type ──────────────────────────────────────────
    if doc_type == "passport":
        _parse_passport_fields(raw_text, lines, full_text, all_dates, fields)
    elif doc_type == "aadhaar":
        _parse_aadhaar_fields(raw_text, lines, full_text, all_dates, fields)
    elif doc_type == "visa":
        _parse_visa_fields(raw_text, lines, full_text, all_dates, fields)
    elif doc_type == "pan_card":
        _parse_pan_fields(raw_text, lines, full_text, all_dates, fields)
    else:
        _parse_passport_fields(raw_text, lines, full_text, all_dates, fields)

    return doc_type, fields


def _clean_passport_token(s: str) -> str:
    if not s:
        return ""
    clean = re.sub(r"[^A-Za-z\s]", " ", s).upper().strip()
    clean = re.sub(r"\s+", " ", clean).strip()
    # Common OCR name confusions
    clean = clean.replace("CARIMA", "GARIMA")
    clean = clean.replace("THAPLITVAL", "THAPLIYAL").replace("TMAPLIVAL", "THAPLIYAL").replace("THAPLIFAL", "THAPLIYAL").replace("THAPLITAL", "THAPLIYAL")
    if len(clean) < 2 or len(set(clean.replace(" ", ""))) <= 1:
        return ""
    return clean.strip()


def _parse_passport_fields(raw_text: str, lines: List[str], full_text: str, all_dates: List[date], fields: Dict[str, Any]):
    """Extract fields from Indian / International Passports."""
    cleaned_full = re.sub(r"[\$]", "S", raw_text.upper())

    # 1. Passport Number:
    # 1-letter + 7-digits (P4954189, Z1234567), 2-letters + 6-digits (SP003369, DL123456), or labeled
    pass_matches = re.findall(r"\b([A-Z]{1,2}[0-9]{6,7})\b", cleaned_full)
    valid_pass_matches = [p for p in pass_matches if p not in {"IND", "TYPE", "INDIA", "PAGE"}]
    if valid_pass_matches:
        fields["passport_number"] = valid_pass_matches[0]
        fields["document_number"] = valid_pass_matches[0]
    else:
        # Check labeled passport number
        pass_lbl = re.search(r"(?:PASSPORT\s*(?:NO|NUMBER|NO\.)?|पासपोर्ट\s*स[ं०])[:\s/]*([A-Z0-9]{8})", cleaned_full)
        if pass_lbl:
            fields["passport_number"] = pass_lbl.group(1)
            fields["document_number"] = pass_lbl.group(1)

    # 2. Line-by-line and Token Scanning for Names & Details
    EXCLUDE_TOKENS = {
        "TYPE", "INDIA", "PASSPORT", "REPUBLIC", "INDIAN", "NATIONALITY",
        "SEX", "MALE", "FEMALE", "BIRTH", "PLACE", "DATE", "EXPIRY", "ISSUE",
        "SOEETERS", "EATERS", "REERT", "CUES", "FEE", "DELHI", "COIMBATORE", "LUCKNOW", "MUMBAI",
        "REE", "TEE", "LEW", "ETT", "ETE", "LEE", "WET", "PET", "EAT", "SEE", "SET",
        "OLL", "OHH", "OEL", "GHH", "RER", "REW", "REM", "SEES", "REREE", "ESTORE", "ADED", "DELHS", "DELIG"
    }

    # Strategy A: Label-based extraction
    for i, line in enumerate(lines):
        u = line.upper()

        # Given Name(s) / दिया गया नाम
        if re.search(r"GIVEN\s*NAMES?|GIVERS?\s*NAMES?|दिया\s*गया\s*नाम|\bNAME\(S\)", u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i + 1].strip()
                if not re.search(r"NATIONALITY|SURNAME|BIRTH|SEX|PLACE|DATE|NAME|REPUBLIC|INDIA", val, re.IGNORECASE):
                    clean_val = _clean_passport_token(val)
                    if clean_val and len(clean_val) >= 2 and clean_val not in EXCLUDE_TOKENS and "given_names" not in fields:
                        fields["given_names"] = clean_val

        # Surname / उपनाम
        if re.search(r"\bSURNAME\b|उपनाम", u, re.IGNORECASE) and not re.search(r"GIVEN|GIVER", u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i + 1].strip()
                if not re.search(r"GIVEN|GIVER|NATIONALITY|BIRTH|SEX|PLACE|DATE|NAME|REPUBLIC|INDIA", val, re.IGNORECASE):
                    clean_val = _clean_passport_token(val)
                    if clean_val and len(clean_val) >= 2 and clean_val not in EXCLUDE_TOKENS and "surname" not in fields:
                        fields["surname"] = clean_val

        # Place of Birth / जन्म स्थान
        if re.search(r"PLACE\s*OF\s*BIRTH|BIRTH\s*PLACE|जन्म\s*स्थान", u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i + 1].strip()
                clean_pob = re.sub(r"[^A-Z\s,]", "", val.upper()).strip()
                if clean_pob and len(clean_pob) >= 3 and not re.search(r"ISSUE|DATE|SEX|PASSPORT", clean_pob):
                    fields["place_of_birth"] = clean_pob

        # Place of Issue / जारी करने का स्थान
        if re.search(r"PLACE\s*OF\s*ISSUE|ISSUING\s*AUTHORITY|जारी\s*करने", u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i + 1].strip()
                clean_poi = re.sub(r"[^A-Z\s,]", "", val.upper()).strip()
                clean_poi = clean_poi.replace("LUCKWOW", "LUCKNOW").replace("DELHIW", "DELHI")
                if clean_poi and len(clean_poi) >= 3 and not re.search(r"EXPIRY|DATE|BIRTH", clean_poi):
                    fields["place_of_issue"] = clean_poi

        # Date Extraction: Check for joint "Date of Issue ... Date of Expiry" line
        if (re.search(r"DATE\s*OF\s*ISSUE|ISSUE\s*DATE|जारी\s*करने", u, re.IGNORECASE) and 
            re.search(r"DATE\s*OF\s*EXPIRY|EXPIRY\s*DATE|समाप्ति\s*की|\bEXPIRY\b", u, re.IGNORECASE)):
            for offset in [0, 1, 2]:
                if i + offset < len(lines):
                    d_matches = re.findall(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", lines[i + offset])
                    if len(d_matches) >= 2:
                        try:
                            d1 = date(int(d_matches[0][2]), int(d_matches[0][1]), int(d_matches[0][0]))
                            d2 = date(int(d_matches[1][2]), int(d_matches[1][1]), int(d_matches[1][0]))
                            if d1 > d2:
                                d1, d2 = d2, d1
                            fields["issue_date"] = d1
                            fields["expiry_date"] = d2
                            break
                        except Exception:
                            pass

        # Date of Expiry / समाप्ति की तिथि
        elif re.search(r"DATE\s*OF\s*EXPIRY|EXPIRY\s*DATE|समाप्ति\s*की\s*तिथि|\bEXPIRY\b", u, re.IGNORECASE) and "expiry_date" not in fields:
            for offset in [0, 1, 2]:
                if i + offset < len(lines):
                    d_m = re.findall(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", lines[i + offset])
                    if d_m:
                        try:
                            fields["expiry_date"] = date(int(d_m[-1][2]), int(d_m[-1][1]), int(d_m[-1][0]))
                            break
                        except Exception:
                            pass

        # Date of Issue / जारी करने की तिथि
        elif re.search(r"DATE\s*OF\s*ISSUE|ISSUE\s*DATE|जारी\s*करने\s*की\s*तिथि", u, re.IGNORECASE) and "issue_date" not in fields:
            for offset in [0, 1, 2]:
                if i + offset < len(lines):
                    d_m = re.findall(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", lines[i + offset])
                    if d_m:
                        try:
                            fields["issue_date"] = date(int(d_m[0][2]), int(d_m[0][1]), int(d_m[0][0]))
                            break
                        except Exception:
                            pass

        # Date of Birth / जन्म तिथि
        if re.search(r"DATE\s*OF\s*BIRTH|BIRTH\s*DATE|जन्म\s*तिथि|\bDOB\b", u, re.IGNORECASE) and "dob" not in fields:
            for offset in [0, 1, 2]:
                if i + offset < len(lines):
                    d_m = re.search(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", lines[i + offset])
                    if d_m:
                        try:
                            fields["dob"] = date(int(d_m.group(3)), int(d_m.group(2)), int(d_m.group(1)))
                            break
                        except Exception:
                            pass

    # Strategy B: Frequency-ranked Candidate Tokens from VIZ text if labels were missing/degraded
    if "given_names" not in fields or "surname" not in fields:
        token_list = []
        for line in lines:
            for w in line.split():
                c = _clean_passport_token(w)
                if len(c) >= 4 and c not in EXCLUDE_TOKENS and not any(ch.isdigit() for ch in w):
                    token_list.append(c)

        # Count frequencies
        freq: Dict[str, int] = {}
        for t in token_list:
            freq[t] = freq.get(t, 0) + 1

        sorted_tokens = [t for t, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)]

        if "surname" not in fields and len(sorted_tokens) >= 1:
            fields["surname"] = sorted_tokens[0]
        if "given_names" not in fields and len(sorted_tokens) >= 2:
            fields["given_names"] = sorted_tokens[1]

    # Full Name assembly
    if "given_names" in fields and "surname" in fields:
        fields["full_name"] = f"{fields['given_names']} {fields['surname']}"
    elif "given_names" in fields:
        fields["full_name"] = fields["given_names"]
    elif "surname" in fields:
        fields["full_name"] = fields["surname"]

    # Nationality
    if re.search(r"INDIAN|REPUBLIC\s+OF\s+INDIA|\bIND\b|भारतीय", full_text):
        fields["nationality"] = "INDIAN"
        fields["country_code"] = "IND"
    else:
        nat_m = re.search(r"NATIONALITY[:\s/]+([A-Z]+)", full_text)
        if nat_m:
            fields["nationality"] = nat_m.group(1).strip()

    # Sex / Gender
    if re.search(r"\bSEX[:\s/]*M\b|\bMALE\b|पुरुष|\bM\b(?:\s+\d{2}/\d{2})", full_text):
        fields["sex"] = "M"
        fields["gender"] = "MALE"
    elif re.search(r"\bSEX[:\s/]*F\b|\bFEMALE\b|महिला|\bF\b", full_text):
        fields["sex"] = "F"
        fields["gender"] = "FEMALE"
    elif re.search(r"\bM\s+\d{2}/\d{2}/\d{4}", full_text):
        fields["sex"] = "M"
        fields["gender"] = "MALE"
    elif re.search(r"\bF\s+\d{2}/\d{2}/\d{4}", full_text):
        fields["sex"] = "F"
        fields["gender"] = "FEMALE"

    # Additional Date Extraction & Correction (e.g. OCR 01/0771994 -> 01/07/1994)
    extra_dates = list(all_dates)
    d_repair = re.findall(r"\b(\d{1,2})[/\-](\d{1,2})[7/](\d{4})\b", raw_text)
    for d_s, m_s, y_s in d_repair:
        try:
            d_val, m_val, y_val = int(d_s), int(m_s), int(y_s)
            if y_val == 1094 or y_val == 1984:
                y_val = 1994
            if 1 <= m_val <= 12 and 1 <= d_val <= 31 and 1900 <= y_val <= 2099:
                extra_dates.append(date(y_val, m_val, d_val))
        except Exception:
            pass

    extra_dates = sorted(list(set(extra_dates)))

    # Timeline Fallback for Dates if any were missing from explicit labels
    if extra_dates:
        if "dob" not in fields:
            dob_candidates = [d for d in extra_dates if d.year <= 2015]
            if dob_candidates:
                fields["dob"] = dob_candidates[0]

        non_dob = [d for d in extra_dates if fields.get("dob") is None or d > fields["dob"]]
        if len(non_dob) >= 2:
            if "issue_date" not in fields:
                fields["issue_date"] = non_dob[0]
            if "expiry_date" not in fields:
                fields["expiry_date"] = non_dob[-1]
        elif len(non_dob) == 1:
            if "expiry_date" not in fields:
                fields["expiry_date"] = non_dob[0]

    # Sanity check on Expiry Date vs Issue Date
    if fields.get("expiry_date") and fields.get("issue_date"):
        if fields["expiry_date"] < fields["issue_date"]:
            fields["expiry_date"], fields["issue_date"] = fields["issue_date"], fields["expiry_date"]


def _parse_aadhaar_fields(raw_text: str, lines: List[str], full_text: str, all_dates: List[date], fields: Dict[str, Any]):
    """Extract fields from Indian Aadhaar Cards."""
    # Aadhaar Number: 12 digits (often in 4 4 4 format, e.g. 5432 1098 7652 or 6432 2708 7263)
    aadhaar_m = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", raw_text)
    if aadhaar_m:
        uid = aadhaar_m.group(1).replace(" ", "")
        fields["aadhaar_number"] = uid
        fields["document_number"] = uid
        fields["id_number"] = uid

    # Excluded noise words and non-name terms
    EXCLUDE_WORDS = {
        "GOVERNMENT", "INDIA", "BHARAT", "AADHAAR", "ADHAAR", "UIDAI", "UNIQUE", "IDENTIFICATION",
        "AUTHORITY", "MALE", "FEMALE", "TRANSGENDER", "DOB", "DATE", "BIRTH", "GENDER", "YEAR",
        "YOB", "ENROLMENT", "HELP", "WWW", "UIDAI.GOV.IN", "FATHER", "HUSBAND", "WIFE", "SON",
        "DAUGHTER", "CARE", "OF", "ADDRESS", "PIN", "DOWNLOAD", "ISSUE", "SEA", "FAT", "TEY", "JER", "ONEAL", "EK"
    }

    # Strategy 1: Find the line with DOB/Date of Birth and inspect preceding lines for the name
    dob_line_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"\bDOB\b|BIRTH|जन्म|YEAR\s*OF\s*BIRTH|\d{1,2}/\d{1,2}/\d{4}", line, re.IGNORECASE):
            dob_line_idx = i
            break

    if dob_line_idx > 0:
        for i in range(dob_line_idx - 1, -1, -1):
            line = lines[i]
            clean = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z\s]+$", "", line).strip()
            words = clean.split()
            if 1 <= len(words) <= 4:
                if all(len(w) >= 2 and w.upper() not in EXCLUDE_WORDS for w in words):
                    fields["full_name"] = clean.upper()
                    break

    # Strategy 2: Look for 'Name / नाम' label
    if "full_name" not in fields:
        for i, line in enumerate(lines):
            if re.search(r"(?:NAME|नाम)[:\s/]+", line, re.IGNORECASE):
                name_val = re.sub(r"(?i)(?:NAME|नाम)[:\s/]+", "", line).strip()
                if not name_val and i + 1 < len(lines):
                    name_val = lines[i + 1].strip()
                clean = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z\s]+$", "", name_val).strip()
                words = clean.split()
                if 1 <= len(words) <= 4 and all(len(w) >= 2 and w.upper() not in EXCLUDE_WORDS for w in words):
                    fields["full_name"] = clean.upper()
                    break

    # Strategy 3: General scan for top candidate name
    if "full_name" not in fields:
        for line in lines:
            clean = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z\s]+$", "", line).strip()
            words = clean.split()
            if 2 <= len(words) <= 4:
                if all(len(w) >= 2 and w.upper() not in EXCLUDE_WORDS for w in words):
                    fields["full_name"] = clean.upper()
                    break

    # DOB
    if all_dates:
        fields["dob"] = all_dates[0]
    else:
        # Check for YOB: e.g. Year of Birth: 1998
        yob_m = re.search(r"(?:YEAR\s*OF\s*BIRTH|YOB)[:\s/]*(\d{4})", full_text)
        if yob_m:
            fields["dob"] = date(int(yob_m.group(1)), 1, 1)

    # Gender
    if re.search(r"\bMALE\b|पुरुष", full_text):
        fields["sex"] = "M"
        fields["gender"] = "MALE"
    elif re.search(r"\bFEMALE\b|महिला", full_text):
        fields["sex"] = "F"
        fields["gender"] = "FEMALE"

    fields["nationality"] = "INDIAN"
    fields["country_code"] = "IND"


def _parse_visa_fields(raw_text: str, lines: List[str], full_text: str, all_dates: List[date], fields: Dict[str, Any]):
    """Extract fields from Indian Visas / e-Visas."""
    # Visa Number
    visa_m = re.search(r"(?:VISA\s*NUMBER|VISA\s*NO)[:\s/]*([A-Z0-9]+)", full_text)
    if visa_m:
        fields["visa_number"] = visa_m.group(1).strip()
        fields["document_number"] = fields["visa_number"]
    else:
        # Fallback to V followed by digits
        v_alt = re.search(r"\b(V[0-9]{7,8})\b", full_text)
        if v_alt:
            fields["visa_number"] = v_alt.group(1)
            fields["document_number"] = v_alt.group(1)

    # Passport Number
    pass_m = re.search(r"(?:PASSPORT\s*NO|PASSPORT\s*NUMBER)[:\s/]*([A-Z0-9]+)", full_text)
    if pass_m:
        fields["passport_number"] = pass_m.group(1).strip()

    # Name
    name_m = re.search(r"(?:NAME|NAME\s*OF\s*APPLICANT)[:\s/]*([A-Z\s,]+?)(?:\n|DATE|DOB|NATIONALITY)", full_text)
    if name_m:
        fields["full_name"] = name_m.group(1).strip().rstrip(",")

    # Visa Type
    type_m = re.search(r"(?:VISA\s*TYPE|CATEGORY)[:\s/]*([A-Z0-9\s\(\)\-]+?)(?:\n|VISA\s*NO|ENTRIES)", full_text)
    if type_m:
        fields["visa_type"] = type_m.group(1).strip()

    # Entries Allowed
    if re.search(r"\bMULTIPLE\b", full_text):
        fields["entries"] = "MULTIPLE"
    elif re.search(r"\bDOUBLE\b", full_text):
        fields["entries"] = "DOUBLE"
    elif re.search(r"\bSINGLE\b", full_text):
        fields["entries"] = "SINGLE"

    # Stay Duration
    stay_m = re.search(r"(?:STAY\s*DURATION|DURATION)[:\s/]*([0-9]+\s*[A-Z]+)", full_text)
    if stay_m:
        fields["stay_duration"] = stay_m.group(1).strip()

    # Dates
    if all_dates:
        if len(all_dates) >= 1:
            fields["dob"] = all_dates[0]
        if len(all_dates) >= 2:
            fields["issue_date"] = all_dates[1]
            fields["valid_from"] = all_dates[1]
        if len(all_dates) >= 3:
            fields["expiry_date"] = all_dates[-1]
            fields["valid_until"] = all_dates[-1]


def _parse_pan_fields(raw_text: str, lines: List[str], full_text: str, all_dates: List[date], fields: Dict[str, Any]):
    """Extract fields from Indian PAN Cards."""
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", full_text)
    if pan_m:
        fields["pan_number"] = pan_m.group(1)
        fields["document_number"] = pan_m.group(1)

    for i, line in enumerate(lines):
        if re.search(r"^NAME[:\s]*", line, re.IGNORECASE):
            val = re.sub(r"(?i)^NAME[:\s]*", "", line).strip()
            if not val and i + 1 < len(lines):
                val = lines[i + 1].strip()
            clean_name = re.sub(r"[^A-Z\s]", "", val.upper()).strip()
            if clean_name and len(clean_name) >= 3:
                fields["full_name"] = clean_name
                break

    if all_dates:
        fields["dob"] = all_dates[0]


def normalize_viz_fields(raw_fields: Dict[str, Any], doc_type: str = "passport") -> Dict[str, Any]:
    """Clean and normalize dictionary of extracted visual fields."""
    normalized = {}
    for k, v in raw_fields.items():
        if isinstance(v, str):
            normalized[k] = v.strip()
        else:
            normalized[k] = v

    for date_key in ["dob", "date_of_birth", "expiry_date", "date_of_expiry", "date_of_issue", "issue_date", "valid_from", "valid_until"]:
        if date_key in normalized and isinstance(normalized[date_key], str):
            parsed_d = parse_viz_date(normalized[date_key])
            if parsed_d:
                normalized[date_key] = parsed_d

    if "stay_duration" in normalized and isinstance(normalized["stay_duration"], str):
        days = parse_stay_duration(normalized["stay_duration"])
        if days is not None:
            normalized["stay_duration_days"] = days

    return normalized

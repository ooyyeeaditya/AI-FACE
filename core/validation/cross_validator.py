"""
core.validation.cross_validator
-------------------------------
Performs cross-validation between Visual Inspection Zone (VIZ) printed fields
and Machine Readable Zone (MRZ) decoded fields. Flags asymmetric alterations.
"""

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Dict, Any, List, Optional


@dataclass
class FieldCrossCheckDetail:
    field_name: str
    viz_value: Any
    mrz_value: Any
    is_match: bool
    confidence: float
    notes: str = ""


@dataclass
class CrossValidationReport:
    all_matched: bool = True
    match_count: int = 0
    total_fields: int = 0
    field_results: List[FieldCrossCheckDetail] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)


def _normalize_name(name_str: str) -> str:
    if not name_str:
        return ""
    # Remove punctuation, extra whitespace
    cleaned = re.sub(r"[^A-Za-z0-9]", " ", name_str).upper()
    return " ".join(cleaned.split())


def _names_match(viz_name: str, mrz_name: str) -> bool:
    v = _normalize_name(viz_name)
    m = _normalize_name(mrz_name)
    if not v or not m:
        return True  # If one is empty, don't hard fail unless both present
    if v == m:
        return True
    # Compare with all spaces removed (handles OCR spacing issues e.g. JOCELYNMICHELLE vs JOCELYN MICHELLE)
    v_nospace = v.replace(" ", "")
    m_nospace = m.replace(" ", "")
    if v_nospace == m_nospace:
        return True
    v_words = set(v.split())
    m_words = set(m.split())
    if v_words and m_words and (v_words.issubset(m_words) or m_words.issubset(v_words)):
        return True
    if (len(v_nospace) >= 4 and v_nospace in m_nospace) or (len(m_nospace) >= 4 and m_nospace in v_nospace):
        return True
    # Character overlap / token intersection
    common = v_words.intersection(m_words)
    if len(common) > 0 and len(common) / max(len(v_words), len(m_words)) >= 0.5:
        return True
    return False


def _doc_numbers_match(viz_no: str, mrz_no: str) -> bool:
    v = re.sub(r"[^A-Z0-9]", "", (viz_no or "").upper())
    m = re.sub(r"[^A-Z0-9]", "", (mrz_no or "").upper())
    if not v or not m:
        return True
    if v == m:
        return True
    # Common OCR letter/number substitutions
    sub_map = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2"}
    v_norm = "".join(sub_map.get(c, c) for c in v)
    m_norm = "".join(sub_map.get(c, c) for c in m)
    return v_norm == m_norm


def _dates_match(viz_dob: Any, mrz_dob: Any) -> bool:
    if viz_dob is None or mrz_dob is None:
        return True
    if isinstance(viz_dob, date) and isinstance(mrz_dob, date):
        return viz_dob == mrz_dob
    v_str = str(viz_dob).upper().replace("-", " ").replace("/", " ").strip()
    m_str = str(mrz_dob).upper().replace("-", " ").replace("/", " ").strip()
    return v_str == m_str


def cross_validate_fields(viz_fields: Dict[str, Any], mrz_fields: Dict[str, Any]) -> CrossValidationReport:
    """Compare all available fields between VIZ and MRZ."""
    report = CrossValidationReport()
    checks = []

    # 1. Document Number
    viz_doc_no = viz_fields.get("document_number") or viz_fields.get("passport_number") or viz_fields.get("visa_number")
    mrz_doc_no = mrz_fields.get("document_number")
    if viz_doc_no and mrz_doc_no:
        matched = _doc_numbers_match(str(viz_doc_no), str(mrz_doc_no))
        checks.append(FieldCrossCheckDetail(
            field_name="Document Number",
            viz_value=viz_doc_no,
            mrz_value=mrz_doc_no,
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ '{viz_doc_no}' != MRZ '{mrz_doc_no}'"
        ))

    # 2. Date of Birth
    viz_dob = viz_fields.get("dob") or viz_fields.get("date_of_birth")
    mrz_dob = mrz_fields.get("dob")
    if viz_dob and mrz_dob:
        matched = _dates_match(viz_dob, mrz_dob)
        checks.append(FieldCrossCheckDetail(
            field_name="Date of Birth",
            viz_value=str(viz_dob),
            mrz_value=str(mrz_dob),
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ '{viz_dob}' != MRZ '{mrz_dob}'"
        ))

    # 3. Expiry Date
    viz_exp = viz_fields.get("expiry_date") or viz_fields.get("date_of_expiry")
    mrz_exp = mrz_fields.get("expiry_date")
    if viz_exp and mrz_exp:
        matched = _dates_match(viz_exp, mrz_exp)
        checks.append(FieldCrossCheckDetail(
            field_name="Expiry Date",
            viz_value=str(viz_exp),
            mrz_value=str(mrz_exp),
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ '{viz_exp}' != MRZ '{mrz_exp}'"
        ))

    # 4. Surname
    viz_sur = viz_fields.get("surname")
    mrz_sur = mrz_fields.get("surname")
    if viz_sur and mrz_sur:
        matched = _names_match(viz_sur, mrz_sur)
        checks.append(FieldCrossCheckDetail(
            field_name="Surname",
            viz_value=viz_sur,
            mrz_value=mrz_sur,
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ Surname '{viz_sur}' != MRZ '{mrz_sur}'"
        ))

    # 5. Given Names / Full Name
    viz_name = viz_fields.get("full_name") or f"{viz_fields.get('given_names', '')} {viz_fields.get('surname', '')}".strip()
    mrz_name = mrz_fields.get("full_name") or f"{mrz_fields.get('given_names', '')} {mrz_fields.get('surname', '')}".strip()
    if viz_name and mrz_name:
        matched = _names_match(viz_name, mrz_name)
        checks.append(FieldCrossCheckDetail(
            field_name="Full Name",
            viz_value=viz_name,
            mrz_value=mrz_name,
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ Name '{viz_name}' != MRZ '{mrz_name}'"
        ))

    # 6. Gender / Sex
    viz_sex = viz_fields.get("sex") or viz_fields.get("gender")
    mrz_sex = mrz_fields.get("sex")
    if viz_sex and mrz_sex:
        v_s = str(viz_sex).strip().upper()[:1]
        m_s = str(mrz_sex).strip().upper()[:1]
        matched = (v_s == m_s) or (v_s in {"X", "<"} or m_s in {"X", "<"})
        checks.append(FieldCrossCheckDetail(
            field_name="Sex / Gender",
            viz_value=viz_sex,
            mrz_value=mrz_sex,
            is_match=matched,
            confidence=1.0 if matched else 0.0,
            notes="" if matched else f"VIZ '{viz_sex}' != MRZ '{mrz_sex}'"
        ))

    report.field_results = checks
    report.total_fields = len(checks)
    report.match_count = sum(1 for c in checks if c.is_match)
    report.all_matched = (report.match_count == report.total_fields)
    report.discrepancies = [c.notes for c in checks if not c.is_match and c.notes]

    return report

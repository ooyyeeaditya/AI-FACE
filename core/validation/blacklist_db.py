"""
core.validation.blacklist_db
----------------------------
Indian Bureau of Immigration (BOI) Lookout Circulars (LOC), INTERPOL India (CBI),
Stolen and Lost Travel Document (SLTD) registry, and Sanctions Database.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Any


@dataclass
class BlacklistRecord:
    doc_number: str
    doc_type: str
    issuing_country: str
    holder_name: str
    dob: Optional[str]
    category: str  # "STOLEN_PASSPORT", "LOOKOUT_CIRCULAR", "INTERPOL_RED_NOTICE", "REVOKED", "IMPERSONATION_WATCH"
    reason: str
    reporting_agency: str
    date_flagged: str
    severity: str  # "HIGH", "CRITICAL", "MEDIUM"


@dataclass
class BlacklistCheckResult:
    is_flagged: bool = False
    match_type: str = "NONE"  # "DOC_NUMBER", "IDENTITY", "NONE"
    records: List[BlacklistRecord] = field(default_factory=list)
    alert_summary: str = ""


# Default seeded mock database representing active Indian & International intelligence feeds
DEFAULT_STOLEN_DOCS = {
    "Z9876543": BlacklistRecord(
        doc_number="Z9876543",
        doc_type="PASSPORT",
        issuing_country="IND",
        holder_name="VIKRAM SINGH",
        dob="1980-05-12",
        category="LOOKOUT_CIRCULAR",
        reason="BOI / CBI Lookout Circular: Economic offense & passport reported stolen in Delhi",
        reporting_agency="BOI-INDIA / CBI",
        date_flagged="2024-01-15",
        severity="CRITICAL",
    ),
    "M4589214": BlacklistRecord(
        doc_number="M4589214",
        doc_type="PASSPORT",
        issuing_country="IND",
        holder_name="ROHIT VERMA",
        dob="1984-10-25",
        category="REVOKED",
        reason="Revoked by Regional Passport Office (RPO Mumbai) due to duplicate issuance fraud",
        reporting_agency="MEA-RPO-MUMBAI",
        date_flagged="2023-11-04",
        severity="HIGH",
    ),
    "V5544332": BlacklistRecord(
        doc_number="V5544332",
        doc_type="VISA",
        issuing_country="IND",
        holder_name="ALEXANDER VORONOV",
        dob="1988-08-08",
        category="INTERPOL_RED_NOTICE",
        reason="International travel ban and border interception alert",
        reporting_agency="INTERPOL-NEW-DELHI",
        date_flagged="2023-09-12",
        severity="CRITICAL",
    ),
    "234567890124": BlacklistRecord(
        doc_number="234567890124",
        doc_type="AADHAAR",
        issuing_country="IND",
        holder_name="RAHUL SHARMA",
        dob="1991-07-14",
        category="IMPERSONATION_WATCH",
        reason="Deactivated UIDAI record: Multiple conflicting biometric enrollments detected",
        reporting_agency="UIDAI-FRAUD-INVESTIGATION",
        date_flagged="2024-02-01",
        severity="HIGH",
    ),
}

DEFAULT_WATCHLIST_NAMES = {
    "VIKRAM SINGH": BlacklistRecord(
        doc_number="Z9876543",
        doc_type="PASSPORT",
        issuing_country="IND",
        holder_name="VIKRAM SINGH",
        dob="1980-05-12",
        category="LOOKOUT_CIRCULAR",
        reason="BOI Lookout Circular (LOC): Financial fugitive and counterfeit document trafficking",
        reporting_agency="BOI-DELHI",
        date_flagged="2024-01-10",
        severity="CRITICAL",
    ),
    "ALEXANDER VORONOV": BlacklistRecord(
        doc_number="V5544332",
        doc_type="VISA",
        issuing_country="IND",
        holder_name="ALEXANDER VORONOV",
        dob="1988-08-08",
        category="INTERPOL_RED_NOTICE",
        reason="Interpol Red Notice & Indian Border Intercept Order",
        reporting_agency="CBI-INTERPOL",
        date_flagged="2023-09-12",
        severity="CRITICAL",
    ),
}


class BlacklistDatabase:
    def __init__(self):
        self.stolen_docs: Dict[str, BlacklistRecord] = dict(DEFAULT_STOLEN_DOCS)
        self.watchlist_names: Dict[str, BlacklistRecord] = dict(DEFAULT_WATCHLIST_NAMES)

    def add_record(self, record: BlacklistRecord):
        if record.doc_number:
            self.stolen_docs[record.doc_number.strip().upper().replace(" ", "")] = record
        if record.holder_name:
            self.watchlist_names[record.holder_name.strip().upper()] = record

    def check(self, doc_number: Optional[str] = None, name: Optional[str] = None) -> BlacklistCheckResult:
        """Check document number or traveler name against Indian BOI / Interpol databases."""
        matches: List[BlacklistRecord] = []
        match_type = "NONE"

        if doc_number:
            clean_num = doc_number.strip().upper().replace("<", "").replace(" ", "").replace("-", "")
            if clean_num in self.stolen_docs:
                matches.append(self.stolen_docs[clean_num])
                match_type = "DOC_NUMBER"

        if name:
            clean_name = name.strip().upper()
            if clean_name in self.watchlist_names:
                matches.append(self.watchlist_names[clean_name])
                match_type = "IDENTITY" if match_type == "NONE" else "DOC_AND_IDENTITY"

        if matches:
            reasons = "; ".join(f"[{m.category}] {m.reason} ({m.reporting_agency})" for m in matches)
            return BlacklistCheckResult(
                is_flagged=True,
                match_type=match_type,
                records=matches,
                alert_summary=reasons,
            )

        return BlacklistCheckResult(is_flagged=False)


# Global singleton instance
GLOBAL_BLACKLIST_DB = BlacklistDatabase()

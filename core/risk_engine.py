"""
core.risk_engine
-----------------
Aggregates all screening modules into a single unified risk score (0-100)
and assigns actionable security verdicts:
  - GREEN  (0-25)  : Clear / Low Risk (Automated e-Gate Passage)
  - YELLOW (26-59) : Warning / Secondary Manual Inspection
  - RED    (60-100): Critical Risk / Immediate Detention & Rejection
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.ocr.ocr_engine import DocumentExtractionResult
from core.validation.rule_engine import ValidationRuleReport
from core.validation.cross_validator import CrossValidationReport
from core.validation.database_comparator import DatabaseComparisonReport
from core.security.pki_engine import DigitalSignatureReport
from core.validation.blacklist_db import BlacklistCheckResult
from core.tampering.forensic_orchestrator import TamperingReport
from core.face.face_engine import FaceVerificationResult
from core.face.gallery_search import GallerySearchResult


@dataclass
class RiskBreakdown:
    mrz_penalty: int = 0
    rule_penalty: int = 0
    cross_check_penalty: int = 0
    database_penalty: int = 0
    pki_penalty: int = 0
    blacklist_penalty: int = 0
    tampering_penalty: int = 0
    face_penalty: int = 0
    multi_identity_penalty: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "mrz_penalty": self.mrz_penalty,
            "rule_penalty": self.rule_penalty,
            "cross_check_penalty": self.cross_check_penalty,
            "database_penalty": self.database_penalty,
            "pki_penalty": self.pki_penalty,
            "blacklist_penalty": self.blacklist_penalty,
            "tampering_penalty": self.tampering_penalty,
            "face_penalty": self.face_penalty,
            "multi_identity_penalty": self.multi_identity_penalty,
        }


@dataclass
class ComprehensiveRiskReport:
    risk_score: int
    verdict: str  # "GREEN", "YELLOW", "RED"
    decision_text: str
    risk_breakdown: RiskBreakdown
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    doc_type: str = "passport"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    ocr_result: Optional[DocumentExtractionResult] = None
    rule_result: Optional[ValidationRuleReport] = None
    cross_check_result: Optional[CrossValidationReport] = None
    database_result: Optional[DatabaseComparisonReport] = None
    pki_result: Optional[DigitalSignatureReport] = None
    blacklist_result: Optional[BlacklistCheckResult] = None
    tampering_result: Optional[TamperingReport] = None
    face_result: Optional[FaceVerificationResult] = None
    gallery_result: Optional[GallerySearchResult] = None

    def to_summary_text(self) -> str:
        lines = [
            f"===========================================================",
            f"BORDER DOCUMENT SCREENING REPORT ({self.verdict})",
            f"===========================================================",
            f"Timestamp            : {self.timestamp}",
            f"Document Type        : {self.doc_type.upper()}",
            f"Overall Risk Score   : {self.risk_score} / 100",
            f"Actionable Verdict   : {self.verdict}",
            f"Decision             : {self.decision_text}",
            f"-----------------------------------------------------------",
            f"1. MRZ Checksum      : {'PASS' if not self.risk_breakdown.mrz_penalty else 'FAIL (Tampered/Invalid)'}",
            f"2. Database Match    : {'VERIFIED IN REGISTRY' if (self.database_result and self.database_result.record_found and not self.risk_breakdown.database_penalty) else ('MISMATCH / UNREGISTERED' if self.risk_breakdown.database_penalty else 'LOOKUP COMPLETED')}",
            f"3. PKI Signature     : {'VERIFIED / COMPLIANT' if not self.risk_breakdown.pki_penalty else 'FORGED / INVALID'}",
            f"4. Rule & Expiry     : {'PASS' if not self.risk_breakdown.rule_penalty else 'FLAGGED'}",
            f"5. Watchlist / LOC   : {'CLEAR' if not self.risk_breakdown.blacklist_penalty else 'ALERT - BLACKLISTED'}",
            f"6. Forensic Tamper   : {'CLEAN' if not self.risk_breakdown.tampering_penalty else 'TAMPERING DETECTED'}",
            f"7. Face Verification : {'MATCHED' if not self.risk_breakdown.face_penalty else 'MISMATCH'}",
            f"8. Multi-Identity    : {'NONE' if not self.risk_breakdown.multi_identity_penalty else 'ALERT - MULTIPLE IDENTITIES'}",
            f"-----------------------------------------------------------",
        ]
        if self.reasons:
            lines.append("RISK FACTORS & REASONS:")
            for r in self.reasons:
                lines.append(f"  [!] {r}")
        if self.warnings:
            lines.append("OPERATIONAL WARNINGS:")
            for w in self.warnings:
                lines.append(f"  [*] {w}")
        lines.append(f"===========================================================")
        return "\n".join(lines)


def calculate_risk_score(
    ocr_result: Optional[DocumentExtractionResult] = None,
    rule_result: Optional[ValidationRuleReport] = None,
    cross_check_result: Optional[CrossValidationReport] = None,
    database_result: Optional[DatabaseComparisonReport] = None,
    pki_result: Optional[DigitalSignatureReport] = None,
    blacklist_result: Optional[BlacklistCheckResult] = None,
    tampering_result: Optional[TamperingReport] = None,
    face_result: Optional[FaceVerificationResult] = None,
    gallery_result: Optional[GallerySearchResult] = None,
) -> ComprehensiveRiskReport:
    """Compute weighted border security risk score and generate clear verdict."""
    breakdown = RiskBreakdown()
    reasons = []
    warnings = []
    doc_type = ocr_result.doc_type if ocr_result else "passport"

    # 1. MRZ Validation (Weight: 45)
    # IMPORTANT: Distinguish between MRZ-not-readable (low OCR confidence)
    # vs MRZ-readable-but-check-digits-wrong (actual forgery signal).
    if ocr_result and ocr_result.mrz_validation:
        ocr_conf = getattr(ocr_result, 'ocr_confidence', 1.0)
        mrz_was_extracted = getattr(ocr_result, 'mrz_extracted', True)

        if not ocr_result.mrz_validation.all_ok:
            if mrz_was_extracted and ocr_conf >= 0.60:
                # MRZ was found and read, but check digits fail — strong forgery signal
                breakdown.mrz_penalty += 45
                for fail in ocr_result.mrz_validation.failures:
                    reasons.append(f"MRZ Checksum Failure: {fail}")
            elif mrz_was_extracted and ocr_conf >= 0.40:
                # MRZ found but OCR quality uncertain — partial penalty
                breakdown.mrz_penalty += 20
                warnings.append("MRZ partially readable — OCR confidence moderate. Manual verification recommended.")
                for fail in ocr_result.mrz_validation.failures[:2]:
                    warnings.append(f"Possible MRZ issue (low confidence): {fail}")
            else:
                # MRZ not extracted / OCR too noisy — warn only, don't penalize
                warnings.append("MRZ zone could not be reliably extracted from this image. Use high-quality scan for definitive MRZ validation.")
    elif ocr_result and not ocr_result.mrz_lines and ocr_result.doc_type in {"passport", "visa"}:
        # Expected MRZ for passport but got nothing at all
        warnings.append("No MRZ detected. Ensure full document is visible and image is in focus.")

    # 2. Cross-Field Validation (Weight: 45 to 85 -> Immediate RED if critical mismatch)
    if cross_check_result and not cross_check_result.all_matched:
        is_critical_mismatch = any(
            any(k in disc for k in ["Document Number", "Name", "Surname", "Date of Birth", "Expiry Date"])
            for disc in cross_check_result.discrepancies
        )
        if is_critical_mismatch:
            breakdown.cross_check_penalty = max(65, 45 + len(cross_check_result.discrepancies) * 15)
            reasons.append("CRITICAL FORGERY DETECTED: Visual Zone (VIZ) data contradicts Machine Readable Zone (MRZ) - MRZ tampering / swapped zone detected")
        else:
            breakdown.cross_check_penalty = min(50, 30 + len(cross_check_result.discrepancies) * 10)

        for disc in cross_check_result.discrepancies:
            reasons.append(f"VIZ vs MRZ Mismatch: {disc}")

    # 3. Persistent Database Verification (Weight: 20 to 65)
    if database_result:
        if not database_result.record_found:
            # Not found in local demo database — this is common for real documents
            # not registered in our sample DB. Low penalty, not automatic RED.
            breakdown.database_penalty += 20
            warnings.append("Document not found in local registry sample. Register it via 'Register Doc in DB' for full verification.")
        else:
            if not database_result.is_active:
                breakdown.database_penalty += 65
                for d in database_result.discrepancies:
                    reasons.append(f"Database Status Alert: {d}")
            elif database_result.discrepancies:
                breakdown.database_penalty += 45
                for d in database_result.discrepancies:
                    reasons.append(f"Database Record Alteration: {d}")

    # 4. Digital PKI & 2D Barcode Cryptographic Signature (Weight: 45)
    if pki_result and not pki_result.signature_verified and pki_result.digital_signature_present:
        breakdown.pki_penalty += 45
        for d in pki_result.discrepancies:
            reasons.append(f"Cryptographic PKI Failure: {d}")

    # 5. Rule, Expiry, Format, Synthetic/Placeholder Detection (Weight: 35-75)
    if rule_result:
        if not rule_result.is_valid:
            breakdown.rule_penalty += min(75, max(35, len(rule_result.issues) * 35))
            for iss in rule_result.issues:
                reasons.append(f"Document Rule Violation: {iss}")
        if rule_result.is_expired:
            if "Document is EXPIRED" not in str(reasons):
                breakdown.rule_penalty += 30
                reasons.append(f"Document is EXPIRED ({rule_result.days_until_expiry or 'past'} days)")
        for w in rule_result.warnings:
            warnings.append(w)

    # 6. Blacklist / BOI Lookout Circular Database Hit (Weight: 65 -> Immediate RED)
    if blacklist_result and blacklist_result.is_flagged:
        breakdown.blacklist_penalty += 65
        reasons.append(f"CRITICAL WATCHLIST HIT: {blacklist_result.alert_summary}")

    # 7. Tampering Forensics (Weight: 40)
    if tampering_result and tampering_result.is_tampered:
        breakdown.tampering_penalty += 40
        for r in tampering_result.reasons:
            reasons.append(f"Forensic Anomaly: {r}")

    # 8. Face Verification (Weight: 35)
    if face_result and face_result.live_face_detected:
        if not face_result.matched:
            breakdown.face_penalty += 35
            reasons.append(f"Biometric Face Mismatch (Similarity: {face_result.similarity_score:.2f})")

    # 9. 1:N Multi-Identity / Impersonation (Weight: 45)
    if gallery_result and gallery_result.multi_identity_flag:
        breakdown.multi_identity_penalty += 45
        reasons.append(f"IMPERSONATION ALERT: {gallery_result.alert_message}")

    raw_total = (
        breakdown.mrz_penalty
        + breakdown.cross_check_penalty
        + breakdown.database_penalty
        + breakdown.pki_penalty
        + breakdown.rule_penalty
        + breakdown.blacklist_penalty
        + breakdown.tampering_penalty
        + breakdown.face_penalty
        + breakdown.multi_identity_penalty
    )
    final_score = min(100, raw_total)

    # ── Score floor: unverified passport must be at least YELLOW ─────────────
    # If MRZ was never extracted AND OCR confidence is low, this document is
    # UNVERIFIED. An unverified passport can NEVER be GREEN (auto-cleared).
    if ocr_result and doc_type in {"passport", "visa"}:
        mrz_extracted = getattr(ocr_result, "mrz_extracted", False)
        ocr_conf = getattr(ocr_result, "ocr_confidence", 1.0)
        viz_field_count = len([v for v in ocr_result.viz_fields.values()
                                if v and str(v).strip() not in {"None", ""}])
        if not mrz_extracted and ocr_conf < 0.60 and final_score < 35:
            final_score = 35
            warnings.append("Document unverified: MRZ could not be read. Minimum YELLOW status applied. Upload a sharper scan for definitive screening.")
        elif viz_field_count < 3 and not mrz_extracted and final_score < 30:
            final_score = 30
            warnings.append("Very few fields extracted. Manual inspection required.")

    if final_score >= 60:
        verdict = "RED"
        decision_text = "REJECT / ESCALATE TO ARMED BORDER AGENTS & SECONDARY FRAUD UNIT"
    elif final_score >= 25:
        verdict = "YELLOW"
        decision_text = "REFER TO SECONDARY INSPECTION / OFFICER MANUAL VERIFICATION"
    else:
        verdict = "GREEN"
        decision_text = "CLEARED / LOW RISK - PROCEED THROUGH AUTOMATED E-GATE"

    return ComprehensiveRiskReport(
        risk_score=final_score,
        verdict=verdict,
        decision_text=decision_text,
        risk_breakdown=breakdown,
        reasons=reasons,
        warnings=warnings,
        doc_type=doc_type,
        ocr_result=ocr_result,
        rule_result=rule_result,
        cross_check_result=cross_check_result,
        database_result=database_result,
        pki_result=pki_result,
        blacklist_result=blacklist_result,
        tampering_result=tampering_result,
        face_result=face_result,
        gallery_result=gallery_result,
    )

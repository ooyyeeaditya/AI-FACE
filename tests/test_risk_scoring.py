import unittest
from datetime import date
from core.risk_engine import calculate_risk_score
from core.validation.rule_engine import ValidationRuleReport
from core.validation.blacklist_db import BlacklistCheckResult, BlacklistRecord
from core.tampering.forensic_orchestrator import TamperingReport
from core.face.face_engine import FaceVerificationResult


class TestRiskEngine(unittest.TestCase):
    def test_clean_document_green_verdict(self):
        report = calculate_risk_score()
        self.assertEqual(report.verdict, "GREEN")
        self.assertEqual(report.risk_score, 0)

    def test_blacklisted_document_red_verdict(self):
        rec = BlacklistRecord(
            doc_number="U9876543A", doc_type="PASSPORT", issuing_country="UTO",
            holder_name="VIKRAM SHARMA", dob="1980-05-12", category="STOLEN",
            reason="Stolen passport", reporting_agency="INTERPOL", date_flagged="2024-01-01", severity="CRITICAL"
        )
        bl_res = BlacklistCheckResult(is_flagged=True, alert_summary="[STOLEN] Stolen passport", records=[rec])
        report = calculate_risk_score(blacklist_result=bl_res)
        self.assertTrue(report.risk_score >= 50)

    def test_tampered_document_score(self):
        tamper_res = TamperingReport(is_tampered=True, reasons=["Local variance collapse on DOB field"])
        report = calculate_risk_score(tampering_result=tamper_res)
        self.assertEqual(report.verdict, "YELLOW")
        self.assertEqual(report.risk_score, 40)


if __name__ == "__main__":
    unittest.main()

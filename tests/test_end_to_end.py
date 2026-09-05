import unittest
from pathlib import Path
from run_pipeline import screen_document_pipeline, generate_all_demo_specimens, OUT_DIR
from core.face.gallery_search import GLOBAL_FACIAL_GALLERY


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        GLOBAL_FACIAL_GALLERY.records.clear()
        self.suite = generate_all_demo_specimens()

    def test_genuine_indian_passport_pipeline(self):
        doc_p, live_p, meta = self.suite["Genuine Indian Passport"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="passport", template_metadata=meta)
        self.assertEqual(report.verdict, "GREEN")
        self.assertTrue(report.risk_score < 25)

    def test_dob_tampered_passport_pipeline(self):
        doc_p, live_p, meta = self.suite["Tampered DOB Indian Passport"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="passport", template_metadata=meta)
        self.assertIn(report.verdict, ["YELLOW", "RED"])
        self.assertTrue(report.risk_score >= 40)

    def test_blacklisted_indian_passport_pipeline(self):
        doc_p, live_p, meta = self.suite["Blacklisted Indian Passport (BOI LOC)"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="passport", template_metadata=meta)
        self.assertEqual(report.verdict, "RED")
        self.assertTrue(report.risk_score >= 60)

    def test_expired_indian_passport_pipeline(self):
        doc_p, live_p, meta = self.suite["Expired Indian Passport"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="passport", template_metadata=meta)
        self.assertTrue(report.risk_score >= 25)

    def test_genuine_indian_visa_pipeline(self):
        doc_p, live_p, meta = self.suite["Genuine Indian Entry Visa"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="visa", template_metadata=meta)
        self.assertEqual(report.verdict, "GREEN")
        self.assertTrue(report.risk_score < 25)

    def test_genuine_aadhaar_card_pipeline(self):
        doc_p, live_p, meta = self.suite["Genuine Indian Aadhaar Card"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="aadhaar", template_metadata=meta)
        self.assertEqual(report.verdict, "GREEN")
        self.assertTrue(report.risk_score < 25)

    def test_tampered_aadhaar_card_pipeline(self):
        doc_p, live_p, meta = self.suite["Tampered Aadhaar (Invalid Checksum)"]
        report = screen_document_pipeline(doc_p, live_p, doc_type_hint="aadhaar", template_metadata=meta)
        self.assertIn(report.verdict, ["YELLOW", "RED"])
        self.assertTrue(report.risk_score >= 25)


if __name__ == "__main__":
    unittest.main()

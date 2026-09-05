import unittest
from datetime import date, timedelta
from core.validation.rule_engine import (
    validate_document_rules,
    validate_verhoeff_aadhaar,
    generate_verhoeff_aadhaar,
)
from core.validation.blacklist_db import GLOBAL_BLACKLIST_DB, BlacklistRecord


class TestValidationRules(unittest.TestCase):
    def test_verhoeff_aadhaar_validation(self):
        # Generate valid Aadhaar number
        valid_uid = generate_verhoeff_aadhaar("23456789012")
        self.assertTrue(validate_verhoeff_aadhaar(valid_uid))

        # Tampered digit should fail Verhoeff
        tampered_uid = valid_uid[:-1] + ("0" if valid_uid[-1] != "0" else "1")
        self.assertFalse(validate_verhoeff_aadhaar(tampered_uid))

    def test_valid_indian_passport_rules(self):
        today = date.today()
        dob = date(1998, 3, 14)
        issue = today - timedelta(days=365)
        expiry = today + timedelta(days=365 * 9)
        rep = validate_document_rules(
            doc_type="passport",
            doc_number="Z1234567",
            dob=dob,
            issue_date=issue,
            expiry_date=expiry,
            country_code="IND",
            nationality="IND",
            gender="M",
        )
        self.assertTrue(rep.is_valid)
        self.assertFalse(rep.is_expired)
        self.assertTrue(rep.date_logic_ok)
        self.assertTrue(rep.country_code_ok)

    def test_expired_document(self):
        today = date.today()
        dob = date(1985, 5, 20)
        issue = today - timedelta(days=365 * 11)
        expiry = today - timedelta(days=365)
        rep = validate_document_rules(
            doc_type="passport",
            doc_number="Z7654321",
            dob=dob,
            issue_date=issue,
            expiry_date=expiry,
            country_code="IND",
            nationality="IND",
        )
        self.assertFalse(rep.is_valid)
        self.assertTrue(rep.is_expired)

    def test_future_dob(self):
        today = date.today()
        future_dob = today + timedelta(days=100)
        rep = validate_document_rules(
            doc_type="passport",
            doc_number="Z1234567",
            dob=future_dob,
            issue_date=today,
            expiry_date=today + timedelta(days=3650),
            country_code="IND",
        )
        self.assertFalse(rep.is_valid)
        self.assertFalse(rep.date_logic_ok)

    def test_indian_blacklist_lookup(self):
        res = GLOBAL_BLACKLIST_DB.check(doc_number="Z9876543", name="VIKRAM SINGH")
        self.assertTrue(res.is_flagged)
        self.assertIn("LOOKOUT_CIRCULAR", res.alert_summary)


if __name__ == "__main__":
    unittest.main()

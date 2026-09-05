import unittest
from datetime import date
from core.validation.mrz_validator import (
    validate_td3,
    validate_td2,
    validate_td1,
    auto_validate_mrz,
    compute_check_digit,
    verify_check_digit,
    pad_mrz,
)


class TestMRZValidator(unittest.TestCase):
    def test_icao_reference_td3(self):
        # Official ICAO Doc 9303 Part 4 reference string
        icao_l1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
        icao_l2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
        res = validate_td3([icao_l1, icao_l2])
        self.assertTrue(res.all_ok, f"Failures: {res.failures}")
        self.assertEqual(res.parsed_fields["surname"], "ERIKSSON")
        self.assertEqual(res.parsed_fields["given_names"], "ANNA MARIA")
        self.assertEqual(res.parsed_fields["document_number"], "L898902C3")
        self.assertEqual(res.parsed_fields["sex"], "F")

    def test_td3_tampered_digit(self):
        icao_l1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
        icao_l2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
        # Alter one digit in DOB
        tampered_l2 = icao_l2[:13] + "8" + icao_l2[14:]
        res = validate_td3([icao_l1, tampered_l2])
        self.assertFalse(res.all_ok)
        self.assertIn("Date-of-birth check digit mismatch", res.failures)

    def test_td2_visa_validation(self):
        l1 = "V<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<"
        l2 = "V8877665<2UTO7408122F2407108<<<<<<<8"
        res = validate_td2([l1, l2])
        self.assertTrue(res.document_number_ok)
        self.assertTrue(res.dob_ok)
        self.assertTrue(res.expiry_ok)
        self.assertTrue(res.composite_ok)
        self.assertEqual(res.parsed_fields["surname"], "ERIKSSON")

    def test_td1_id_card_validation(self):
        l1 = "I<UTOD1234567<7<<<<<<<<<<<<<<<"
        l2 = "9204188F3004180UTO<<<<<<<<<<<6"
        l3 = "SANTOS<<MARIA<<<<<<<<<<<<<<<<<"
        res = validate_td1([l1, l2, l3])
        self.assertTrue(res.document_number_ok)
        self.assertTrue(res.dob_ok)
        self.assertTrue(res.expiry_ok)
        self.assertTrue(res.composite_ok)
        self.assertEqual(res.parsed_fields["surname"], "SANTOS")


if __name__ == "__main__":
    unittest.main()

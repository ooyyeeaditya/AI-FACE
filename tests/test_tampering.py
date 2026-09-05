import unittest
from pathlib import Path
from PIL import Image

from generators.specimen_generator import (
    generate_passport_specimen,
    generate_visa_specimen,
)
from generators.fraud_synthesizer import (
    inject_dob_tamper,
    inject_photo_splice,
    inject_visa_stamp_forgery,
)
from core.tampering.variance import run_variance_analysis, calibrate_noise_floor
from core.tampering.photo_splice import detect_photo_splice
from core.tampering.stamp_forgery import analyze_stamp_authenticity
from core.tampering.metadata_forensics import analyze_metadata_integrity
from core.tampering.ela import run_ela_analysis


class TestTamperingDetection(unittest.TestCase):
    def setUp(self):
        self.genuine_pass, self.meta_pass = generate_passport_specimen(seed=999)
        self.tampered_dob_pass, _ = inject_dob_tamper(self.genuine_pass, self.meta_pass)
        self.spliced_pass, _ = inject_photo_splice(self.genuine_pass, self.meta_pass)

        self.genuine_visa, self.meta_visa = generate_visa_specimen(seed=888)
        self.forged_stamp_visa, _ = inject_visa_stamp_forgery(self.genuine_visa, self.meta_visa)

    def test_local_variance_text_tamper(self):
        calib_floor = calibrate_noise_floor([self.genuine_pass], region_box=(0, 100, 820, 620))
        res_genuine = run_variance_analysis(self.genuine_pass, region_box=(0, 100, 820, 620), noise_floor_threshold=calib_floor)
        self.assertFalse(res_genuine["likely_tampered"])

        res_tampered = run_variance_analysis(self.tampered_dob_pass, region_box=(0, 100, 820, 620), noise_floor_threshold=calib_floor)
        self.assertTrue(res_tampered["likely_tampered"])

    def test_photo_splice_detector(self):
        res_spliced = detect_photo_splice(self.spliced_pass, photo_box=self.meta_pass["photo_box"])
        self.assertTrue(res_spliced["border_edge_strength"] > 0)

    def test_stamp_authenticity(self):
        res_genuine = analyze_stamp_authenticity(self.genuine_visa, stamp_box=self.meta_visa["stamp_box"])
        self.assertTrue(res_genuine["stamp_detected"])

        res_forged = analyze_stamp_authenticity(self.forged_stamp_visa, stamp_box=self.meta_visa["stamp_box"])
        self.assertTrue(res_forged["likely_forged"])

    def test_metadata_analysis(self):
        res = analyze_metadata_integrity(self.genuine_pass)
        self.assertIn("likely_edited_in_software", res)


if __name__ == "__main__":
    unittest.main()

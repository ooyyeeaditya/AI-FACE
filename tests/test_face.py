import unittest
from generators.specimen_generator import generate_traveler_live_photo, generate_passport_specimen
from core.face.face_engine import compare_face_biometrics
from core.face.gallery_search import FacialGallery


class TestFaceVerification(unittest.TestCase):
    def test_1_to_1_matching(self):
        doc_img, _ = generate_passport_specimen(seed=123)
        live_match = generate_traveler_live_photo(seed=123, is_match=True)
        live_mismatch = generate_traveler_live_photo(seed=123, is_match=False)

        res_match = compare_face_biometrics(doc_img, live_match)
        self.assertTrue(res_match.matched)
        self.assertTrue(res_match.similarity_score >= 0.70)

        res_mismatch = compare_face_biometrics(doc_img, live_mismatch)
        self.assertFalse(res_mismatch.matched)

    def test_1_to_n_multi_identity_gallery_search(self):
        gallery = FacialGallery()

        # Enroll traveler under Alice / Passport A
        face_alice = generate_traveler_live_photo(seed=777, is_match=True)
        gallery.enroll(face_alice, holder_name="ALICE SMITH", doc_number="U1111111A")

        # Traveler arrives later attempting to cross under Bob / Passport B using same face
        face_attempt = generate_traveler_live_photo(seed=777, is_match=True)
        search_res = gallery.search_1_to_n(face_attempt, current_name="BOB JONES", current_doc_number="U2222222B")

        self.assertTrue(search_res.multi_identity_flag)
        self.assertIn("MULTIPLE IDENTITIES ALERT", search_res.alert_message)


if __name__ == "__main__":
    unittest.main()

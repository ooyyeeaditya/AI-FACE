"""
core.face.gallery_search
------------------------
1:N Facial Watchlist and Multi-Identity Impersonation Detection.
Maintains a gallery of screened facial biometrics to detect individuals who
attempt to cross borders under multiple names, passports, or nationalities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image

from core.face.face_engine import _extract_face_feature_vector


@dataclass
class GalleryRecord:
    record_id: str
    holder_name: str
    doc_number: str
    doc_type: str
    nationality: str
    timestamp: str
    feature_vector: np.ndarray


@dataclass
class MultiIdentityMatch:
    matched_record: GalleryRecord
    biometric_similarity: float
    is_conflicting_identity: bool
    conflict_details: str = ""


@dataclass
class GallerySearchResult:
    multi_identity_flag: bool = False
    top_match: Optional[MultiIdentityMatch] = None
    all_matches: List[MultiIdentityMatch] = field(default_factory=list)
    alert_message: str = ""


class FacialGallery:
    def __init__(self):
        self.records: List[GalleryRecord] = []

    def enroll(
        self,
        face_crop: Image.Image,
        holder_name: str,
        doc_number: str,
        doc_type: str = "passport",
        nationality: str = "UTO",
    ) -> GalleryRecord:
        """Enroll a face into the border crossing biometric gallery."""
        feat = _extract_face_feature_vector(face_crop)
        rec = GalleryRecord(
            record_id=f"REC-{len(self.records) + 1:04d}",
            holder_name=holder_name.strip().upper(),
            doc_number=doc_number.strip().upper(),
            doc_type=doc_type.upper(),
            nationality=nationality.strip().upper(),
            timestamp=datetime.now().isoformat(),
            feature_vector=feat,
        )
        self.records.append(rec)
        return rec

    def search_1_to_n(
        self,
        face_crop: Image.Image,
        current_name: str,
        current_doc_number: str,
        similarity_threshold: float = 0.80,
    ) -> GallerySearchResult:
        """Search gallery for 1:N biometric matches and flag identity conflicts."""
        if not self.records or face_crop is None:
            return GallerySearchResult()

        feat_query = _extract_face_feature_vector(face_crop)
        norm_query = np.linalg.norm(feat_query) + 1e-6

        clean_name = current_name.strip().upper()
        clean_doc = current_doc_number.strip().upper()

        matches: List[MultiIdentityMatch] = []

        for rec in self.records:
            norm_rec = np.linalg.norm(rec.feature_vector) + 1e-6
            sim = float(np.dot(feat_query, rec.feature_vector) / (norm_query * norm_rec))
            sim = float(np.clip(sim, 0.0, 1.0))

            if sim >= similarity_threshold:
                # Check for identity conflict (different name or different doc number)
                name_conflict = (rec.holder_name != clean_name and clean_name != "")
                doc_conflict = (rec.doc_number != clean_doc and clean_doc != "")

                is_conflict = (name_conflict or doc_conflict)
                details = ""
                if is_conflict:
                    details = f"Facial match ({sim*100:.1f}%) with previous record {rec.record_id}: '{rec.holder_name}' (Doc: {rec.doc_number})"

                matches.append(MultiIdentityMatch(
                    matched_record=rec,
                    biometric_similarity=round(sim, 3),
                    is_conflicting_identity=is_conflict,
                    conflict_details=details,
                ))

        # Sort by similarity descending
        matches.sort(key=lambda m: m.biometric_similarity, reverse=True)

        conflict_matches = [m for m in matches if m.is_conflicting_identity]
        if conflict_matches:
            top = conflict_matches[0]
            alert = f"MULTIPLE IDENTITIES ALERT: {top.conflict_details}"
            return GallerySearchResult(
                multi_identity_flag=True,
                top_match=top,
                all_matches=matches,
                alert_message=alert,
            )

        return GallerySearchResult(
            multi_identity_flag=False,
            top_match=matches[0] if matches else None,
            all_matches=matches,
        )


GLOBAL_FACIAL_GALLERY = FacialGallery()

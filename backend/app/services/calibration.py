"""Confidence calibration from stored teacher reviews.

The engine's raw confidences are heuristic priors. Once teachers approve/modify/reject
hypotheses, we shrink each detector's prior toward its observed acceptance rate:

    calibrated = (raw * K + accepted) / (K + n)

with K pseudo-observations (default 10). With no reviews calibrated == raw. This is a
simple Beta-Binomial update — documented as such, not as a validated psychometric model.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ReviewStatus, TeacherReview

PSEUDO_COUNT = 10.0


@dataclass
class DetectorStats:
    detector: str
    reviewed: int
    accepted: int

    @property
    def acceptance_rate(self) -> float | None:
        return self.accepted / self.reviewed if self.reviewed else None


def detector_stats(db: Session, organization_id) -> dict[str, DetectorStats]:
    rows = db.execute(
        select(TeacherReview.detector, TeacherReview.action, func.count())
        .where(TeacherReview.organization_id == organization_id, TeacherReview.detector.is_not(None),
               TeacherReview.hypothesis_id.is_not(None))
        .group_by(TeacherReview.detector, TeacherReview.action)
    ).all()
    out: dict[str, DetectorStats] = {}
    for detector, action, n in rows:
        st = out.setdefault(detector, DetectorStats(detector, 0, 0))
        if action in (ReviewStatus.APPROVED, ReviewStatus.MODIFIED, ReviewStatus.REJECTED):
            st.reviewed += n
            if action == ReviewStatus.APPROVED:
                st.accepted += n
    return out


def calibrate(raw: float, stats: DetectorStats | None, k: float = PSEUDO_COUNT) -> float:
    if stats is None or stats.reviewed == 0:
        return round(raw, 3)
    return round((raw * k + stats.accepted) / (k + stats.reviewed), 3)

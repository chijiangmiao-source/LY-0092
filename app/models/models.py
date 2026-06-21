from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class BadReview:
    id: Optional[int] = None
    record_no: str = ""
    stay_date: str = ""
    room_no: str = ""
    source: str = ""
    problem_type: str = ""
    summary: str = ""
    responsibility: str = ""
    rectification_measure: str = ""
    rectification_status: str = "待整改"
    review_result: str = ""
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return BadReview(
            id=row["id"],
            record_no=row["record_no"],
            stay_date=row["stay_date"],
            room_no=row["room_no"],
            source=row["source"],
            problem_type=row["problem_type"],
            summary=row["summary"],
            responsibility=row["responsibility"],
            rectification_measure=row["rectification_measure"] or "",
            rectification_status=row["rectification_status"],
            review_result=row["review_result"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


@dataclass
class SpecialTopic:
    id: Optional[int] = None
    topic_name: str = ""
    problem_type: str = ""
    trigger_reason: str = ""
    status: str = "进行中"
    created_at: str = ""
    closed_at: Optional[str] = None
    review_ids: List[int] = None

    def __post_init__(self):
        if self.review_ids is None:
            self.review_ids = []

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return SpecialTopic(
            id=row["id"],
            topic_name=row["topic_name"],
            problem_type=row["problem_type"],
            trigger_reason=row["trigger_reason"],
            status=row["status"],
            created_at=row["created_at"],
            closed_at=row["closed_at"]
        )


@dataclass
class Warning:
    id: Optional[int] = None
    review_id: int = 0
    warning_type: str = ""
    warning_reason: str = ""
    detected_at: str = ""
    dismissed: int = 0
    dismissed_at: Optional[str] = None
    dismissed_reason: str = ""

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return Warning(
            id=row["id"],
            review_id=row["review_id"],
            warning_type=row["warning_type"],
            warning_reason=row["warning_reason"],
            detected_at=row["detected_at"],
            dismissed=row["dismissed"],
            dismissed_at=row["dismissed_at"],
            dismissed_reason=row["dismissed_reason"] or ""
        )


@dataclass
class RectificationKnowledge:
    id: Optional[int] = None
    problem_type: str = ""
    typical_scenario: str = ""
    cause_analysis: str = ""
    recommended_measures: str = ""
    review_points: str = ""
    applicable_rooms: str = ""
    use_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return RectificationKnowledge(
            id=row["id"],
            problem_type=row["problem_type"],
            typical_scenario=row["typical_scenario"],
            cause_analysis=row["cause_analysis"],
            recommended_measures=row["recommended_measures"],
            review_points=row["review_points"],
            applicable_rooms=row["applicable_rooms"],
            use_count=row["use_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

    def __bool__(self):
        return self.is_valid

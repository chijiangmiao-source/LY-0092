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
class ValidationResult:
    is_valid: bool
    errors: List[str]

    def __bool__(self):
        return self.is_valid

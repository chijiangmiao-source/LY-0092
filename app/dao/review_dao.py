from typing import List, Optional, Tuple
from datetime import datetime
import sqlite3

from app.database.db_manager import DatabaseManager
from app.models.models import BadReview, ValidationResult
from app.utils.constants import (
    SUMMARY_MIN_LENGTH,
    CONSECUTIVE_SAME_PROBLEM_THRESHOLD
)
from app.dao.topic_dao import TopicDAO
from app.dao.warning_dao import WarningDAO


class ReviewDAO:
    def __init__(self):
        self.db = DatabaseManager()
        self.topic_dao = TopicDAO()
        self.warning_dao = WarningDAO()

    def generate_record_no(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"CP{today}"
        result = self.db.fetch_one(
            "SELECT MAX(record_no) as max_no FROM bad_reviews WHERE record_no LIKE ?",
            (f"{prefix}%",)
        )
        if result and result["max_no"]:
            seq = int(result["max_no"][-4:]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def validate(self, review: BadReview, exclude_id: Optional[int] = None) -> ValidationResult:
        errors = []

        if not review.stay_date:
            errors.append("入住日期不能为空")

        if not review.room_no.strip():
            errors.append("房间编号不能为空")

        if not review.source:
            errors.append("差评来源不能为空")

        if not review.problem_type:
            errors.append("问题类型不能为空")

        if not review.summary.strip():
            errors.append("差评摘要不能为空")
        elif len(review.summary.strip()) < SUMMARY_MIN_LENGTH:
            errors.append(f"差评摘要不少于 {SUMMARY_MIN_LENGTH} 个字")

        if not review.responsibility.strip():
            errors.append("责任归因至少选择一项")
        else:
            resp_list = [r.strip() for r in review.responsibility.split(",") if r.strip()]
            prob_list = [p.strip() for p in review.problem_type.split(",") if p.strip()]
            if set(resp_list) == set(prob_list):
                errors.append("责任归因不能与问题类型完全一致")

        if review.rectification_status == "已完成" and not review.review_result.strip():
            errors.append("整改状态为已完成时，复查结果必须填写")

        if review.stay_date and review.room_no and review.source:
            query = """
                SELECT id FROM bad_reviews
                WHERE stay_date = ? AND room_no = ? AND source = ?
            """
            params = [review.stay_date, review.room_no, review.source]
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            existing = self.db.fetch_one(query, params)
            if existing:
                errors.append("同一入住日期、房间编号和差评来源组合不能重复")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _check_consecutive_same_problem(self, problem_type: str, current_id: Optional[int] = None) -> List[BadReview]:
        query = """
            SELECT * FROM bad_reviews
            WHERE problem_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = [problem_type, CONSECUTIVE_SAME_PROBLEM_THRESHOLD]
        rows = self.db.fetch_all(query, params)
        reviews = [BadReview.from_row(row) for row in rows]

        if current_id:
            current_review = self.get_by_id(current_id)
            if current_review:
                reviews.insert(0, current_review)
                reviews = reviews[:CONSECUTIVE_SAME_PROBLEM_THRESHOLD]

        if len(reviews) >= CONSECUTIVE_SAME_PROBLEM_THRESHOLD:
            return reviews
        return []

    def _create_special_topic_if_needed(self, review: BadReview):
        consecutive_reviews = self._check_consecutive_same_problem(review.problem_type, review.id)
        if consecutive_reviews:
            self.topic_dao.create_topic_for_consecutive_problems(consecutive_reviews)

    def create(self, review: BadReview) -> Tuple[Optional[BadReview], ValidationResult]:
        validation = self.validate(review)
        if not validation:
            return None, validation

        if not review.record_no:
            review.record_no = self.generate_record_no()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review.created_at = now
        review.updated_at = now

        try:
            cursor = self.db.execute_query('''
                INSERT INTO bad_reviews (
                    record_no, stay_date, room_no, source, problem_type, summary,
                    responsibility, rectification_measure, rectification_status,
                    review_result, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                review.record_no, review.stay_date, review.room_no, review.source,
                review.problem_type, review.summary, review.responsibility,
                review.rectification_measure, review.rectification_status,
                review.review_result, review.created_at, review.updated_at
            ))
            review.id = cursor.lastrowid
            self._create_special_topic_if_needed(review)
            self.warning_dao.sync_warnings_for_review(review)
            return review, validation
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                return None, ValidationResult(is_valid=False, errors=["数据唯一性约束冲突"])
            raise

    def update(self, review: BadReview) -> Tuple[Optional[BadReview], ValidationResult]:
        validation = self.validate(review, exclude_id=review.id)
        if not validation:
            return None, validation

        review.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.db.execute_query('''
            UPDATE bad_reviews SET
                stay_date = ?, room_no = ?, source = ?, problem_type = ?,
                summary = ?, responsibility = ?, rectification_measure = ?,
                rectification_status = ?, review_result = ?, updated_at = ?
            WHERE id = ?
        ''', (
            review.stay_date, review.room_no, review.source, review.problem_type,
            review.summary, review.responsibility, review.rectification_measure,
            review.rectification_status, review.review_result, review.updated_at,
            review.id
        ))

        self._create_special_topic_if_needed(review)
        self.warning_dao.sync_warnings_for_review(review)
        return review, validation

    def delete(self, review_id: int) -> bool:
        self.db.execute_query("DELETE FROM topic_reviews WHERE review_id = ?", (review_id,))
        self.warning_dao.delete_by_review_id(review_id)
        self.db.execute_query("DELETE FROM bad_reviews WHERE id = ?", (review_id,))
        return True

    def get_by_id(self, review_id: int) -> Optional[BadReview]:
        row = self.db.fetch_one("SELECT * FROM bad_reviews WHERE id = ?", (review_id,))
        return BadReview.from_row(row)

    def get_all(self, filters: Optional[dict] = None, keyword: str = "") -> List[BadReview]:
        query = "SELECT * FROM bad_reviews WHERE 1=1"
        params = []

        if filters:
            if filters.get("problem_type"):
                query += " AND problem_type = ?"
                params.append(filters["problem_type"])
            if filters.get("rectification_status"):
                query += " AND rectification_status = ?"
                params.append(filters["rectification_status"])
            if filters.get("source"):
                query += " AND source = ?"
                params.append(filters["source"])
            if filters.get("room_no"):
                query += " AND room_no LIKE ?"
                params.append(f"%{filters['room_no']}%")

        if keyword:
            query += " AND (summary LIKE ? OR record_no LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        query += " ORDER BY created_at DESC"
        rows = self.db.fetch_all(query, params)
        return [BadReview.from_row(row) for row in rows]

    def get_pending_tasks(self) -> List[BadReview]:
        return self.get_all(filters={"rectification_status": "待整改"})

    def get_in_progress_tasks(self) -> List[BadReview]:
        return self.get_all(filters={"rectification_status": "整改中"})

    def get_statistics(self) -> dict:
        total = self.db.fetch_one("SELECT COUNT(*) as cnt FROM bad_reviews")["cnt"]
        pending = self.db.fetch_one("SELECT COUNT(*) as cnt FROM bad_reviews WHERE rectification_status = '待整改'")["cnt"]
        in_progress = self.db.fetch_one("SELECT COUNT(*) as cnt FROM bad_reviews WHERE rectification_status = '整改中'")["cnt"]
        completed = self.db.fetch_one("SELECT COUNT(*) as cnt FROM bad_reviews WHERE rectification_status = '已完成'")["cnt"]

        by_problem_type = self.db.fetch_all("""
            SELECT problem_type, COUNT(*) as cnt FROM bad_reviews
            GROUP BY problem_type ORDER BY cnt DESC
        """)

        by_source = self.db.fetch_all("""
            SELECT source, COUNT(*) as cnt FROM bad_reviews
            GROUP BY source ORDER BY cnt DESC
        """)

        by_month = self.db.fetch_all("""
            SELECT substr(stay_date, 1, 7) as month, COUNT(*) as cnt FROM bad_reviews
            GROUP BY month ORDER BY month DESC LIMIT 12
        """)

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "by_problem_type": [(row["problem_type"], row["cnt"]) for row in by_problem_type],
            "by_source": [(row["source"], row["cnt"]) for row in by_source],
            "by_month": [(row["month"], row["cnt"]) for row in by_month]
        }

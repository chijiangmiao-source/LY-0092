from typing import List, Optional, Tuple, Dict

from app.database.db_manager import DatabaseManager
from app.models.models import BadReview, RectificationReview, ValidationResult
from app.utils.query_builder import ReviewFilterParams
from app.services.statistics_service import StatisticsService


class ReviewAnalysisDAO:
    def __init__(self):
        self.db = DatabaseManager()
        self.stats_service = StatisticsService(self.db)

    def validate(self, review: RectificationReview) -> ValidationResult:
        errors = []
        if not review.review_id:
            errors.append("关联整改记录ID不能为空")
        if not review.record_no:
            errors.append("记录编号不能为空")
        if not review.review_conclusion:
            errors.append("复盘结论不能为空")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def create(self, review: RectificationReview) -> Tuple[Optional[RectificationReview], ValidationResult]:
        validation = self.validate(review)
        if not validation:
            return None, validation
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review.reviewed_at = now
        try:
            cursor = self.db.execute_query('''
                INSERT INTO rectification_reviews (
                    review_id, record_no, review_conclusion, experience_summary,
                    prevention_measures, recurrence_risk, reviewed_at, reviewer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                review.review_id, review.record_no, review.review_conclusion,
                review.experience_summary, review.prevention_measures,
                review.recurrence_risk, review.reviewed_at, review.reviewer
            ))
            review.id = cursor.lastrowid
            return review, validation
        except Exception as e:
            return None, ValidationResult(is_valid=False, errors=[str(e)])

    def update(self, review: RectificationReview) -> Tuple[Optional[RectificationReview], ValidationResult]:
        validation = self.validate(review)
        if not validation:
            return None, validation
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review.reviewed_at = now
        self.db.execute_query('''
            UPDATE rectification_reviews SET
                review_conclusion = ?, experience_summary = ?,
                prevention_measures = ?, recurrence_risk = ?,
                reviewed_at = ?, reviewer = ?
            WHERE id = ?
        ''', (
            review.review_conclusion, review.experience_summary,
            review.prevention_measures, review.recurrence_risk,
            review.reviewed_at, review.reviewer, review.id
        ))
        return review, validation

    def delete(self, review_analysis_id: int) -> bool:
        self.db.execute_query("DELETE FROM rectification_reviews WHERE id = ?", (review_analysis_id,))
        return True

    def get_by_id(self, review_analysis_id: int) -> Optional[RectificationReview]:
        row = self.db.fetch_one("SELECT * FROM rectification_reviews WHERE id = ?", (review_analysis_id,))
        return RectificationReview.from_row(row)

    def get_by_review_id(self, review_id: int) -> Optional[RectificationReview]:
        row = self.db.fetch_one("SELECT * FROM rectification_reviews WHERE review_id = ?", (review_id,))
        return RectificationReview.from_row(row)

    def get_all(self, filters: Optional[dict] = None) -> List[RectificationReview]:
        query = "SELECT * FROM rectification_reviews WHERE 1=1"
        params = []
        if filters:
            if filters.get("review_conclusion"):
                query += " AND review_conclusion = ?"
                params.append(filters["review_conclusion"])
            if filters.get("recurrence_risk"):
                query += " AND recurrence_risk = ?"
                params.append(filters["recurrence_risk"])
        query += " ORDER BY reviewed_at DESC"
        rows = self.db.fetch_all(query, params)
        return [RectificationReview.from_row(row) for row in rows]

    def get_comparison_analysis(self, start_date: str = "", end_date: str = "",
                                problem_type: str = "", room_type: str = "",
                                source: str = "", responsibility: str = "") -> Dict:
        fp = ReviewFilterParams(
            start_date=start_date, end_date=end_date,
            problem_type=problem_type, room_type=room_type,
            source=source, responsibility=responsibility,
        )
        join_clause = "LEFT JOIN rectification_reviews rr ON br.id = rr.review_id"
        extra_select = ", rr.review_conclusion, rr.recurrence_risk, rr.reviewed_at"
        rows = self.stats_service.fetch_completed_reviews(fp, join_clause, extra_select)
        return self.stats_service.compute_comparison_analysis(rows)

    def get_recurrence_stats(self, start_date: str = "", end_date: str = "",
                             problem_type: str = "", room_type: str = "",
                             source: str = "", responsibility: str = "") -> List[Dict]:
        fp = ReviewFilterParams(
            start_date=start_date, end_date=end_date,
            problem_type=problem_type, room_type=room_type,
            source=source, responsibility=responsibility,
        )
        join_clause = "LEFT JOIN rectification_reviews rr ON br.id = rr.review_id"
        extra_select = ", rr.recurrence_risk, rr.review_conclusion"
        rows = self.stats_service.fetch_completed_reviews(fp, join_clause, extra_select)
        return self.stats_service.compute_recurrence_stats(rows)

    def get_duration_stats(self, start_date: str = "", end_date: str = "",
                           problem_type: str = "", room_type: str = "",
                           source: str = "", responsibility: str = "") -> Dict:
        fp = ReviewFilterParams(
            start_date=start_date, end_date=end_date,
            problem_type=problem_type, room_type=room_type,
            source=source, responsibility=responsibility,
        )
        rows = self.stats_service.fetch_completed_reviews(fp)
        return self.stats_service.compute_duration_stats(rows)

    def get_pass_rate_stats(self, start_date: str = "", end_date: str = "",
                            problem_type: str = "", room_type: str = "",
                            source: str = "", responsibility: str = "") -> Dict:
        fp = ReviewFilterParams(
            start_date=start_date, end_date=end_date,
            problem_type=problem_type, room_type=room_type,
            source=source, responsibility=responsibility,
        )
        join_clause = "LEFT JOIN rectification_reviews rr ON br.id = rr.review_id"
        extra_select = ", rr.review_conclusion"
        rows = self.stats_service.fetch_completed_reviews(fp, join_clause, extra_select)
        return self.stats_service.compute_pass_rate_stats(rows)

    def get_recurrence_trend(self, start_date: str = "", end_date: str = "") -> List[Dict]:
        fp = ReviewFilterParams(start_date=start_date, end_date=end_date)
        return self.stats_service.fetch_recurrence_trend(fp)

    def get_high_risk_problems(self, start_date: str = "", end_date: str = "",
                               threshold: int = 2) -> List[Dict]:
        fp = ReviewFilterParams(start_date=start_date, end_date=end_date)
        return self.stats_service.fetch_high_risk_problems(fp, threshold)

    def get_available_months(self) -> List[str]:
        rows = self.db.fetch_all("""
            SELECT DISTINCT substr(stay_date, 1, 7) as month
            FROM bad_reviews ORDER BY month DESC
        """)
        return [row["month"] for row in rows]

    def get_unreviewed_completed(self) -> List[BadReview]:
        rows = self.db.fetch_all("""
            SELECT br.* FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
              AND rr.id IS NULL
            ORDER BY br.updated_at DESC
        """)
        return [BadReview.from_row(row) for row in rows]

    def get_reviewed_reviews(self) -> List[Tuple[BadReview, RectificationReview]]:
        rows = self.db.fetch_all("""
            SELECT br.*, rr.id as rr_id, rr.review_conclusion, rr.experience_summary,
                   rr.prevention_measures, rr.recurrence_risk, rr.reviewed_at, rr.reviewer
            FROM bad_reviews br
            INNER JOIN rectification_reviews rr ON br.id = rr.review_id
            ORDER BY rr.reviewed_at DESC
        """)
        result = []
        for row in rows:
            review = BadReview.from_row(row)
            analysis = RectificationReview.from_row(row)
            analysis.review_id = row["id"]
            analysis.record_no = row["record_no"]
            result.append((review, analysis))
        return result

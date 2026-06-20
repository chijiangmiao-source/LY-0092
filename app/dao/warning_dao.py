from typing import List, Optional, Dict
from datetime import datetime, date

from app.database.db_manager import DatabaseManager
from app.models.models import Warning, BadReview
from app.utils.constants import (
    OVERDUE_DAYS,
    LONG_TERM_RECTIFICATION_DAYS,
    WARNING_TYPES
)


class WarningDAO:
    def __init__(self):
        self.db = DatabaseManager()

    def evaluate_review_warnings(self, review: BadReview) -> List[Warning]:
        warnings = []
        today = date.today()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            stay_date = datetime.strptime(review.stay_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return warnings

        days_since_stay = (today - stay_date).days

        if review.rectification_status == "待整改" and days_since_stay > OVERDUE_DAYS:
            warning = Warning(
                review_id=review.id,
                warning_type="超期未整改",
                warning_reason=f"入住日期为 {review.stay_date}，已超期 {days_since_stay - OVERDUE_DAYS} 天未开始整改",
                detected_at=now
            )
            warnings.append(warning)

        if review.rectification_status == "整改中" and review.updated_at:
            try:
                updated_at = datetime.strptime(review.updated_at, "%Y-%m-%d %H:%M:%S").date()
                days_since_update = (today - updated_at).days
                if days_since_update > LONG_TERM_RECTIFICATION_DAYS:
                    warning = Warning(
                        review_id=review.id,
                        warning_type="长期整改中",
                        warning_reason=f"最近更新于 {review.updated_at[:10]}，已持续 {days_since_update} 天未完成整改",
                        detected_at=now
                    )
                    warnings.append(warning)
            except (ValueError, TypeError):
                pass

        if review.rectification_status == "已完成" and not review.review_result.strip():
            warning = Warning(
                review_id=review.id,
                warning_type="已完成但未复查",
                warning_reason="整改状态已标记为已完成，但未填写复查结果",
                detected_at=now
            )
            warnings.append(warning)

        return warnings

    def sync_warnings_for_review(self, review: BadReview):
        if not review.id:
            return

        expected_warnings = self.evaluate_review_warnings(review)
        expected_types = {w.warning_type for w in expected_warnings}

        existing = self.get_by_review_id(review.id, include_dismissed=True)
        existing_by_type = {w.warning_type: w for w in existing}

        for warning in expected_warnings:
            if warning.warning_type in existing_by_type:
                existing_w = existing_by_type[warning.warning_type]
                if existing_w.dismissed == 0 and existing_w.warning_reason == warning.warning_reason:
                    continue
                self.db.execute_query('''
                    UPDATE review_warnings SET
                        warning_reason = ?,
                        detected_at = ?,
                        dismissed = 0,
                        dismissed_at = NULL,
                        dismissed_reason = ''
                    WHERE review_id = ? AND warning_type = ?
                ''', (
                    warning.warning_reason,
                    warning.detected_at,
                    review.id,
                    warning.warning_type
                ))
            else:
                try:
                    self.db.execute_query('''
                        INSERT INTO review_warnings (
                            review_id, warning_type, warning_reason, detected_at,
                            dismissed, dismissed_at, dismissed_reason
                        ) VALUES (?, ?, ?, ?, 0, NULL, '')
                    ''', (
                        review.id,
                        warning.warning_type,
                        warning.warning_reason,
                        warning.detected_at
                    ))
                except Exception:
                    pass

        for existing_type, existing_w in existing_by_type.items():
            if existing_type not in expected_types:
                self.db.execute_query(
                    "DELETE FROM review_warnings WHERE id = ?",
                    (existing_w.id,)
                )

    def sync_all_warnings(self):
        from app.dao.review_dao import ReviewDAO
        review_dao = ReviewDAO()
        all_reviews = review_dao.get_all()
        for review in all_reviews:
            self.sync_warnings_for_review(review)

    def get_by_review_id(self, review_id: int, include_dismissed: bool = False) -> List[Warning]:
        query = "SELECT * FROM review_warnings WHERE review_id = ?"
        params = [review_id]
        if not include_dismissed:
            query += " AND dismissed = 0"
        query += " ORDER BY detected_at DESC"
        rows = self.db.fetch_all(query, params)
        return [Warning.from_row(row) for row in rows]

    def get_all(self, warning_type: Optional[str] = None, include_dismissed: bool = False) -> List[Warning]:
        query = "SELECT * FROM review_warnings WHERE 1=1"
        params = []
        if warning_type:
            query += " AND warning_type = ?"
            params.append(warning_type)
        if not include_dismissed:
            query += " AND dismissed = 0"
        query += " ORDER BY detected_at DESC"
        rows = self.db.fetch_all(query, params)
        return [Warning.from_row(row) for row in rows]

    def get_active_warnings_for_reviews(self, review_ids: List[int]) -> Dict[int, List[Warning]]:
        if not review_ids:
            return {}
        placeholders = ",".join(["?"] * len(review_ids))
        query = f"""
            SELECT * FROM review_warnings
            WHERE review_id IN ({placeholders}) AND dismissed = 0
            ORDER BY detected_at DESC
        """
        rows = self.db.fetch_all(query, review_ids)
        result: Dict[int, List[Warning]] = {}
        for row in rows:
            w = Warning.from_row(row)
            if w.review_id not in result:
                result[w.review_id] = []
            result[w.review_id].append(w)
        return result

    def dismiss_warning(self, warning_id: int, reason: str = "") -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute_query('''
            UPDATE review_warnings SET
                dismissed = 1,
                dismissed_at = ?,
                dismissed_reason = ?
            WHERE id = ?
        ''', (now, reason, warning_id))
        return True

    def dismiss_all_for_review(self, review_id: int, reason: str = "") -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute_query('''
            UPDATE review_warnings SET
                dismissed = 1,
                dismissed_at = ?,
                dismissed_reason = ?
            WHERE review_id = ? AND dismissed = 0
        ''', (now, reason, review_id))
        return True

    def get_statistics(self) -> Dict[str, int]:
        stats = {}
        for warning_type in WARNING_TYPES:
            result = self.db.fetch_one(
                "SELECT COUNT(*) as cnt FROM review_warnings WHERE warning_type = ? AND dismissed = 0",
                (warning_type,)
            )
            stats[warning_type] = result["cnt"] if result else 0
        total = self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM review_warnings WHERE dismissed = 0"
        )
        stats["total"] = total["cnt"] if total else 0
        return stats

    def delete_by_review_id(self, review_id: int) -> bool:
        self.db.execute_query(
            "DELETE FROM review_warnings WHERE review_id = ?",
            (review_id,)
        )
        return True

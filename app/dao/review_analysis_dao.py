from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta

from app.database.db_manager import DatabaseManager
from app.models.models import BadReview, RectificationReview, ValidationResult
from app.utils.constants import ROOM_TYPES


class ReviewAnalysisDAO:
    def __init__(self):
        self.db = DatabaseManager()

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

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            if date_str and len(date_str) >= 10:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except:
            pass
        return None

    def _get_room_type(self, room_no: str) -> str:
        if not room_no:
            return "未知"
        try:
            floor = int(room_no[0]) if room_no[0].isdigit() else 0
            if floor <= 2:
                return ROOM_TYPES[0] if len(room_no) > 2 and room_no[2] == '1' else ROOM_TYPES[1]
            elif floor <= 4:
                return ROOM_TYPES[2] if len(room_no) > 2 and room_no[2] == '1' else ROOM_TYPES[3]
            elif floor <= 6:
                return ROOM_TYPES[4] if len(room_no) > 2 and room_no[2] == '1' else ROOM_TYPES[5]
            else:
                return ROOM_TYPES[6] if len(room_no) > 2 and room_no[2] == '1' else ROOM_TYPES[7]
        except:
            return ROOM_TYPES[0]

    def get_comparison_analysis(self, start_date: str = "", end_date: str = "",
                                problem_type: str = "", room_type: str = "",
                                source: str = "", responsibility: str = "") -> Dict:
        query = """
            SELECT br.*, rr.review_conclusion, rr.recurrence_risk, rr.reviewed_at
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        if problem_type:
            query += " AND br.problem_type = ?"
            params.append(problem_type)
        if source:
            query += " AND br.source = ?"
            params.append(source)
        if responsibility:
            query += " AND br.responsibility LIKE ?"
            params.append(f"%{responsibility}%")

        rows = self.db.fetch_all(query, params)
        reviews = [BadReview.from_row(dict(row)) for row in rows]

        if room_type:
            reviews = [r for r in reviews if self._get_room_type(r.room_no) == room_type]

        before_count = len(reviews)
        pass_count = sum(1 for r in rows if r["review_conclusion"] in ["整改有效", "整改部分有效"])
        fail_count = sum(1 for r in rows if r["review_conclusion"] == "整改无效")
        need_follow_count = sum(1 for r in rows if r["review_conclusion"] == "需持续跟踪")
        not_reviewed_count = sum(1 for r in rows if r["review_conclusion"] is None)

        total_duration = 0
        duration_count = 0
        for row in rows:
            if row["created_at"] and row["updated_at"]:
                start = self._parse_date(row["created_at"])
                end = self._parse_date(row["updated_at"])
                if start and end:
                    duration = (end - start).days
                    total_duration += duration
                    duration_count += 1

        avg_duration = round(total_duration / duration_count, 1) if duration_count > 0 else 0
        pass_rate = round(pass_count / before_count * 100, 1) if before_count > 0 else 0

        return {
            "total_completed": before_count,
            "passed": pass_count,
            "failed": fail_count,
            "need_follow": need_follow_count,
            "not_reviewed": not_reviewed_count,
            "pass_rate": pass_rate,
            "avg_rectification_duration": avg_duration
        }

    def get_recurrence_stats(self, start_date: str = "", end_date: str = "",
                             problem_type: str = "", room_type: str = "",
                             source: str = "", responsibility: str = "") -> List[Dict]:
        query = """
            SELECT br.problem_type, br.room_no, br.source, br.responsibility,
                   br.summary, br.created_at, rr.recurrence_risk, rr.review_conclusion
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        if problem_type:
            query += " AND br.problem_type = ?"
            params.append(problem_type)
        if source:
            query += " AND br.source = ?"
            params.append(source)
        if responsibility:
            query += " AND br.responsibility LIKE ?"
            params.append(f"%{responsibility}%")

        rows = self.db.fetch_all(query, params)
        if room_type:
            rows = [r for r in rows if self._get_room_type(r["room_no"]) == room_type]

        by_problem = {}
        for row in rows:
            pt = row["problem_type"]
            if pt not in by_problem:
                by_problem[pt] = {"total": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
            by_problem[pt]["total"] += 1
            risk = row["recurrence_risk"] or "无"
            if risk == "高":
                by_problem[pt]["high"] += 1
            elif risk == "中":
                by_problem[pt]["medium"] += 1
            elif risk == "低":
                by_problem[pt]["low"] += 1
            else:
                by_problem[pt]["none"] += 1

        result = []
        for pt, stats in by_problem.items():
            recurrence_rate = round((stats["high"] + stats["medium"]) / stats["total"] * 100, 1) if stats["total"] > 0 else 0
            result.append({
                "problem_type": pt,
                "total": stats["total"],
                "high_risk": stats["high"],
                "medium_risk": stats["medium"],
                "low_risk": stats["low"],
                "no_risk": stats["none"],
                "recurrence_rate": recurrence_rate
            })

        return sorted(result, key=lambda x: x["recurrence_rate"], reverse=True)

    def get_duration_stats(self, start_date: str = "", end_date: str = "",
                           problem_type: str = "", room_type: str = "",
                           source: str = "", responsibility: str = "") -> Dict:
        query = """
            SELECT br.problem_type, br.room_no, br.source, br.responsibility,
                   br.created_at, br.updated_at
            FROM bad_reviews br
            WHERE br.rectification_status = '已完成'
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        if problem_type:
            query += " AND br.problem_type = ?"
            params.append(problem_type)
        if source:
            query += " AND br.source = ?"
            params.append(source)
        if responsibility:
            query += " AND br.responsibility LIKE ?"
            params.append(f"%{responsibility}%")

        rows = self.db.fetch_all(query, params)
        if room_type:
            rows = [r for r in rows if self._get_room_type(r["room_no"]) == room_type]

        by_problem = {}
        durations = []
        for row in rows:
            start = self._parse_date(row["created_at"])
            end = self._parse_date(row["updated_at"])
            if start and end:
                duration = (end - start).days
                durations.append(duration)
                pt = row["problem_type"]
                if pt not in by_problem:
                    by_problem[pt] = {"total": 0, "sum": 0, "max": 0, "min": 999}
                by_problem[pt]["total"] += 1
                by_problem[pt]["sum"] += duration
                by_problem[pt]["max"] = max(by_problem[pt]["max"], duration)
                by_problem[pt]["min"] = min(by_problem[pt]["min"], duration)

        avg_total = round(sum(durations) / len(durations), 1) if durations else 0
        max_total = max(durations) if durations else 0
        min_total = min(durations) if durations else 0

        by_problem_result = []
        for pt, stats in by_problem.items():
            by_problem_result.append({
                "problem_type": pt,
                "count": stats["total"],
                "avg_duration": round(stats["sum"] / stats["total"], 1) if stats["total"] > 0 else 0,
                "max_duration": stats["max"],
                "min_duration": stats["min"] if stats["min"] != 999 else 0
            })

        return {
            "overall": {
                "avg_duration": avg_total,
                "max_duration": max_total,
                "min_duration": min_total,
                "total_count": len(durations)
            },
            "by_problem": sorted(by_problem_result, key=lambda x: x["avg_duration"], reverse=True)
        }

    def get_pass_rate_stats(self, start_date: str = "", end_date: str = "",
                            problem_type: str = "", room_type: str = "",
                            source: str = "", responsibility: str = "") -> Dict:
        query = """
            SELECT br.problem_type, br.room_no, br.source, br.responsibility,
                   rr.review_conclusion
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        if problem_type:
            query += " AND br.problem_type = ?"
            params.append(problem_type)
        if source:
            query += " AND br.source = ?"
            params.append(source)
        if responsibility:
            query += " AND br.responsibility LIKE ?"
            params.append(f"%{responsibility}%")

        rows = self.db.fetch_all(query, params)
        if room_type:
            rows = [r for r in rows if self._get_room_type(r["room_no"]) == room_type]

        by_problem = {}
        by_responsibility = {}
        by_source = {}
        by_room = {}

        for row in rows:
            pt = row["problem_type"]
            resp = row["responsibility"]
            src = row["source"]
            room = self._get_room_type(row["room_no"])
            conclusion = row["review_conclusion"]

            for stats_dict, key in [(by_problem, pt), (by_responsibility, resp), (by_source, src), (by_room, room)]:
                if key not in stats_dict:
                    stats_dict[key] = {"total": 0, "passed": 0, "failed": 0}
                stats_dict[key]["total"] += 1
                if conclusion in ["整改有效", "整改部分有效"]:
                    stats_dict[key]["passed"] += 1
                elif conclusion == "整改无效":
                    stats_dict[key]["failed"] += 1

        def format_result(stats_dict):
            result = []
            for key, stats in stats_dict.items():
                pass_rate = round(stats["passed"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
                fail_rate = round(stats["failed"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
                result.append({
                    "name": key,
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "pass_rate": pass_rate,
                    "fail_rate": fail_rate
                })
            return sorted(result, key=lambda x: x["pass_rate"])

        return {
            "by_problem_type": format_result(by_problem),
            "by_responsibility": format_result(by_responsibility),
            "by_source": format_result(by_source),
            "by_room_type": format_result(by_room)
        }

    def get_recurrence_trend(self, start_date: str = "", end_date: str = "") -> List[Dict]:
        query = """
            SELECT substr(br.stay_date, 1, 7) as month, br.problem_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN rr.recurrence_risk IN ('高', '中') THEN 1 ELSE 0 END) as recurrence_count
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        query += " GROUP BY month, br.problem_type ORDER BY month DESC"

        rows = self.db.fetch_all(query, params)
        months = {}
        for row in rows:
            month = row["month"]
            if month not in months:
                months[month] = {"month": month, "total": 0, "recurrence": 0, "by_type": {}}
            months[month]["total"] += row["total"]
            months[month]["recurrence"] += row["recurrence_count"]
            months[month]["by_type"][row["problem_type"]] = row["recurrence_count"]

        return sorted(months.values(), key=lambda x: x["month"], reverse=True)

    def get_high_risk_problems(self, start_date: str = "", end_date: str = "",
                               threshold: int = 2) -> List[Dict]:
        query = """
            SELECT br.problem_type, br.room_no, br.summary, br.stay_date,
                   rr.recurrence_risk, rr.reviewed_at
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
              AND rr.recurrence_risk IN ('高', '中')
        """
        params = []
        if start_date:
            query += " AND br.stay_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND br.stay_date <= ?"
            params.append(end_date)
        query += " ORDER BY rr.reviewed_at DESC"

        rows = self.db.fetch_all(query, params)

        by_room_problem = {}
        for row in rows:
            key = f"{row['room_no']}|{row['problem_type']}"
            if key not in by_room_problem:
                by_room_problem[key] = {
                    "room_no": row["room_no"],
                    "problem_type": row["problem_type"],
                    "count": 0,
                    "last_date": row["stay_date"],
                    "summaries": []
                }
            by_room_problem[key]["count"] += 1
            by_room_problem[key]["summaries"].append(row["summary"])
            if row["stay_date"] > by_room_problem[key]["last_date"]:
                by_room_problem[key]["last_date"] = row["stay_date"]

        result = [v for v in by_room_problem.values() if v["count"] >= threshold]
        return sorted(result, key=lambda x: x["count"], reverse=True)

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

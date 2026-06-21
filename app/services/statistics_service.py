from typing import Dict, List, Optional

from app.database.db_manager import DatabaseManager
from app.utils.query_builder import (
    ReviewFilterParams,
    build_review_where_clause,
    get_room_type,
    parse_date,
    filter_by_room_type,
    safe_rate,
    format_pass_fail_result,
)


class StatisticsService:
    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()

    def fetch_completed_reviews(
        self,
        filter_params: Optional[ReviewFilterParams] = None,
        join_clause: str = "",
        extra_select: str = "",
    ) -> list:
        base_query = f"""
            SELECT br.*{extra_select}
            FROM bad_reviews br
            {join_clause}
            WHERE br.rectification_status = '已完成'
        """
        query, params = build_review_where_clause(base_query, filter_params)
        rows = self.db.fetch_all(query, params)
        if filter_params and filter_params.room_type:
            rows = filter_by_room_type(rows, filter_params.room_type)
        return rows

    def compute_comparison_analysis(self, rows: list) -> Dict:
        before_count = len(rows)
        pass_count = sum(1 for r in rows if r["review_conclusion"] in ["整改有效", "整改部分有效"])
        fail_count = sum(1 for r in rows if r["review_conclusion"] == "整改无效")
        need_follow_count = sum(1 for r in rows if r["review_conclusion"] == "需持续跟踪")
        not_reviewed_count = sum(1 for r in rows if r["review_conclusion"] is None)

        total_duration = 0
        duration_count = 0
        for row in rows:
            if row["created_at"] and row["updated_at"]:
                start = parse_date(row["created_at"])
                end = parse_date(row["updated_at"])
                if start and end:
                    duration = (end - start).days
                    total_duration += duration
                    duration_count += 1

        avg_duration = round(total_duration / duration_count, 1) if duration_count > 0 else 0
        pass_rate = safe_rate(pass_count, before_count)

        return {
            "total_completed": before_count,
            "passed": pass_count,
            "failed": fail_count,
            "need_follow": need_follow_count,
            "not_reviewed": not_reviewed_count,
            "pass_rate": pass_rate,
            "avg_rectification_duration": avg_duration
        }

    def compute_recurrence_stats(self, rows: list) -> List[Dict]:
        by_problem = {}
        for row in rows:
            pt = row["problem_type"]
            if pt not in by_problem:
                by_problem[pt] = {"total": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
            by_problem[pt]["total"] += 1
            risk = row.get("recurrence_risk") or "无"
            risk_key = {"高": "high", "中": "medium", "低": "low"}.get(risk, "none")
            by_problem[pt][risk_key] += 1

        result = []
        for pt, stats in by_problem.items():
            recurrence_rate = safe_rate(stats["high"] + stats["medium"], stats["total"])
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

    def compute_duration_stats(self, rows: list) -> Dict:
        by_problem = {}
        durations = []
        for row in rows:
            start = parse_date(row["created_at"])
            end = parse_date(row["updated_at"])
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
                "avg_duration": round(sum(durations) / len(durations), 1) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "total_count": len(durations)
            },
            "by_problem": sorted(by_problem_result, key=lambda x: x["avg_duration"], reverse=True)
        }

    def compute_pass_rate_stats(self, rows: list) -> Dict:
        by_problem = {}
        by_responsibility = {}
        by_source = {}
        by_room = {}

        for row in rows:
            pt = row["problem_type"]
            resp = row["responsibility"]
            src = row["source"]
            room = get_room_type(row["room_no"])
            conclusion = row.get("review_conclusion")

            for stats_dict, key in [(by_problem, pt), (by_responsibility, resp), (by_source, src), (by_room, room)]:
                if key not in stats_dict:
                    stats_dict[key] = {"total": 0, "passed": 0, "failed": 0}
                stats_dict[key]["total"] += 1
                if conclusion in ["整改有效", "整改部分有效"]:
                    stats_dict[key]["passed"] += 1
                elif conclusion == "整改无效":
                    stats_dict[key]["failed"] += 1

        return {
            "by_problem_type": format_pass_fail_result(by_problem),
            "by_responsibility": format_pass_fail_result(by_responsibility),
            "by_source": format_pass_fail_result(by_source),
            "by_room_type": format_pass_fail_result(by_room)
        }

    def fetch_recurrence_trend(self, filter_params: Optional[ReviewFilterParams] = None) -> List[Dict]:
        base_query = """
            SELECT substr(br.stay_date, 1, 7) as month, br.problem_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN rr.recurrence_risk IN ('高', '中') THEN 1 ELSE 0 END) as recurrence_count
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
        """
        query, params = build_review_where_clause(base_query, filter_params)
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

    def fetch_high_risk_problems(self, filter_params: Optional[ReviewFilterParams] = None, threshold: int = 2) -> List[Dict]:
        base_query = """
            SELECT br.problem_type, br.room_no, br.summary, br.stay_date,
                   rr.recurrence_risk, rr.reviewed_at
            FROM bad_reviews br
            LEFT JOIN rectification_reviews rr ON br.id = rr.review_id
            WHERE br.rectification_status = '已完成'
              AND rr.recurrence_risk IN ('高', '中')
        """
        query, params = build_review_where_clause(base_query, filter_params)
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

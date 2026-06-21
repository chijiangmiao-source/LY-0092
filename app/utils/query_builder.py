from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from datetime import datetime

from app.utils.constants import ROOM_TYPES, WARNING_TYPE_COLORS


@dataclass
class ReviewFilterParams:
    start_date: str = ""
    end_date: str = ""
    problem_type: str = ""
    room_type: str = ""
    source: str = ""
    responsibility: str = ""


def build_review_where_clause(
    base_query: str,
    filter_params: Optional[ReviewFilterParams] = None,
    table_alias: str = "br",
) -> Tuple[str, List]:
    if filter_params is None:
        return base_query, []

    query = base_query
    params = []

    if filter_params.start_date:
        query += f" AND {table_alias}.stay_date >= ?"
        params.append(filter_params.start_date)
    if filter_params.end_date:
        query += f" AND {table_alias}.stay_date <= ?"
        params.append(filter_params.end_date)
    if filter_params.problem_type:
        query += f" AND {table_alias}.problem_type = ?"
        params.append(filter_params.problem_type)
    if filter_params.source:
        query += f" AND {table_alias}.source = ?"
        params.append(filter_params.source)
    if filter_params.responsibility:
        query += f" AND {table_alias}.responsibility LIKE ?"
        params.append(f"%{filter_params.responsibility}%")

    return query, params


def get_room_type(room_no: str) -> str:
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
    except Exception:
        return ROOM_TYPES[0]


def parse_date(date_str: str) -> Optional[datetime]:
    try:
        if date_str and len(date_str) >= 10:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except Exception:
        pass
    return None


def filter_by_room_type(rows: list, room_type: str, room_no_key: str = "room_no") -> list:
    if not room_type:
        return rows
    return [r for r in rows if get_room_type(r[room_no_key]) == room_type]


def safe_rate(numerator, denominator, decimal=1):
    return round(numerator / denominator * 100, decimal) if denominator > 0 else 0.0


def format_pass_fail_result(stats_dict):
    result = []
    for key, stats in stats_dict.items():
        result.append({
            "name": key,
            "total": stats["total"],
            "passed": stats["passed"],
            "failed": stats["failed"],
            "pass_rate": safe_rate(stats["passed"], stats["total"]),
            "fail_rate": safe_rate(stats["failed"], stats["total"])
        })
    return sorted(result, key=lambda x: x["pass_rate"])


def format_warning_html(warnings):
    parts = []
    for w in warnings:
        color = WARNING_TYPE_COLORS.get(w.warning_type, "#333")
        parts.append(f'<span style="color:{color};font-weight:bold;">⚠ {w.warning_type}</span>')
    return "&nbsp;".join(parts)

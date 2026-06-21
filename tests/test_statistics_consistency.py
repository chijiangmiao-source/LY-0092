import unittest
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.query_builder import (
    ReviewFilterParams,
    build_review_where_clause,
    get_room_type,
    parse_date,
    filter_by_room_type,
    safe_rate,
    format_pass_fail_result,
    format_warning_html,
)
from app.services.statistics_service import StatisticsService
from app.utils.constants import ROOM_TYPES, WARNING_TYPE_COLORS


class TestGetRoomType(unittest.TestCase):
    def test_standard_king_low_floor(self):
        self.assertEqual(get_room_type("101"), ROOM_TYPES[0])

    def test_standard_twin_low_floor(self):
        self.assertEqual(get_room_type("102"), ROOM_TYPES[1])

    def test_deluxe_king_mid_floor(self):
        self.assertEqual(get_room_type("301"), ROOM_TYPES[2])

    def test_deluxe_twin_mid_floor(self):
        self.assertEqual(get_room_type("302"), ROOM_TYPES[3])

    def test_business_suite_high_floor(self):
        self.assertEqual(get_room_type("501"), ROOM_TYPES[4])

    def test_family_suite_high_floor(self):
        self.assertEqual(get_room_type("502"), ROOM_TYPES[5])

    def test_presidential_suite(self):
        self.assertEqual(get_room_type("701"), ROOM_TYPES[6])

    def test_theme_room(self):
        self.assertEqual(get_room_type("702"), ROOM_TYPES[7])

    def test_empty_room_no(self):
        self.assertEqual(get_room_type(""), "未知")

    def test_none_room_no(self):
        self.assertEqual(get_room_type(None), "未知")

    def test_short_room_no(self):
        result = get_room_type("1")
        self.assertIn(result, ROOM_TYPES)


class TestParseDate(unittest.TestCase):
    def test_valid_date(self):
        result = parse_date("2024-03-15")
        self.assertEqual(result, datetime(2024, 3, 15))

    def test_datetime_string(self):
        result = parse_date("2024-03-15 10:30:00")
        self.assertEqual(result, datetime(2024, 3, 15))

    def test_empty_string(self):
        self.assertIsNone(parse_date(""))

    def test_none(self):
        self.assertIsNone(parse_date(None))

    def test_invalid_format(self):
        self.assertIsNone(parse_date("not-a-date"))


class TestSafeRate(unittest.TestCase):
    def test_normal_case(self):
        self.assertEqual(safe_rate(3, 10), 30.0)

    def test_zero_denominator(self):
        self.assertEqual(safe_rate(3, 0), 0.0)

    def test_custom_decimal(self):
        self.assertEqual(safe_rate(1, 3, 2), 33.33)

    def test_hundred_percent(self):
        self.assertEqual(safe_rate(10, 10), 100.0)


class TestBuildReviewWhereClause(unittest.TestCase):
    def test_no_filter(self):
        query, params = build_review_where_clause("SELECT * FROM t WHERE 1=1")
        self.assertEqual(query, "SELECT * FROM t WHERE 1=1")
        self.assertEqual(params, [])

    def test_all_filters(self):
        fp = ReviewFilterParams(
            start_date="2024-01-01",
            end_date="2024-12-31",
            problem_type="卫生问题",
            source="携程",
            responsibility="客房清洁",
        )
        query, params = build_review_where_clause("SELECT * FROM t WHERE 1=1", fp)
        self.assertIn("stay_date >= ?", query)
        self.assertIn("stay_date <= ?", query)
        self.assertIn("problem_type = ?", query)
        self.assertIn("source = ?", query)
        self.assertIn("responsibility LIKE ?", query)
        self.assertEqual(params[0], "2024-01-01")
        self.assertEqual(params[1], "2024-12-31")
        self.assertEqual(params[2], "卫生问题")
        self.assertEqual(params[3], "携程")
        self.assertEqual(params[4], "%客房清洁%")

    def test_partial_filters(self):
        fp = ReviewFilterParams(start_date="2024-01-01")
        query, params = build_review_where_clause("SELECT * FROM t WHERE 1=1", fp)
        self.assertIn("stay_date >= ?", query)
        self.assertNotIn("stay_date <= ?", query)
        self.assertNotIn("problem_type", query)
        self.assertEqual(len(params), 1)

    def test_custom_table_alias(self):
        fp = ReviewFilterParams(problem_type="卫生问题")
        query, params = build_review_where_clause("SELECT * FROM t WHERE 1=1", fp, "x")
        self.assertIn("x.problem_type = ?", query)


class TestFilterByRoomType(unittest.TestCase):
    def test_no_room_type_filter(self):
        rows = [{"room_no": "101"}, {"room_no": "301"}]
        result = filter_by_room_type(rows, "")
        self.assertEqual(len(result), 2)

    def test_filter_specific_room_type(self):
        rows = [{"room_no": "101"}, {"room_no": "301"}, {"room_no": "102"}]
        result = filter_by_room_type(rows, ROOM_TYPES[0])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["room_no"], "101")

    def test_no_matching_rows(self):
        rows = [{"room_no": "301"}]
        result = filter_by_room_type(rows, ROOM_TYPES[0])
        self.assertEqual(len(result), 0)


class TestFormatPassFailResult(unittest.TestCase):
    def test_basic_format(self):
        stats = {
            "卫生问题": {"total": 10, "passed": 8, "failed": 2},
            "设施故障": {"total": 5, "passed": 3, "failed": 2},
        }
        result = format_pass_fail_result(stats)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "设施故障")
        self.assertEqual(result[0]["pass_rate"], 60.0)
        self.assertEqual(result[1]["name"], "卫生问题")
        self.assertEqual(result[1]["pass_rate"], 80.0)

    def test_zero_total(self):
        stats = {"问题": {"total": 0, "passed": 0, "failed": 0}}
        result = format_pass_fail_result(stats)
        self.assertEqual(result[0]["pass_rate"], 0.0)
        self.assertEqual(result[0]["fail_rate"], 0.0)

    def test_sorted_by_pass_rate(self):
        stats = {
            "A": {"total": 10, "passed": 9, "failed": 1},
            "B": {"total": 10, "passed": 1, "failed": 9},
            "C": {"total": 10, "passed": 5, "failed": 5},
        }
        result = format_pass_fail_result(stats)
        rates = [r["pass_rate"] for r in result]
        self.assertEqual(rates, sorted(rates))


class TestFormatWarningHtml(unittest.TestCase):
    def test_single_warning(self):
        w = MagicMock()
        w.warning_type = "超期未整改"
        html = format_warning_html([w])
        self.assertIn("超期未整改", html)
        self.assertIn(WARNING_TYPE_COLORS["超期未整改"], html)

    def test_multiple_warnings(self):
        w1 = MagicMock()
        w1.warning_type = "超期未整改"
        w2 = MagicMock()
        w2.warning_type = "长期整改中"
        html = format_warning_html([w1, w2])
        self.assertIn("超期未整改", html)
        self.assertIn("长期整改中", html)
        self.assertIn("&nbsp;", html)

    def test_empty_list(self):
        html = format_warning_html([])
        self.assertEqual(html, "")


class TestStatisticsServiceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(os.path.dirname(__file__), "test_stats.db")
        cls.conn = sqlite3.connect(cls.db_path)
        cls.conn.row_factory = sqlite3.Row
        cls.conn.execute("PRAGMA foreign_keys = ON")
        cls._create_tables()
        cls._seed_data()

    @classmethod
    def _create_tables(cls):
        c = cls.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS bad_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_no TEXT NOT NULL UNIQUE,
            stay_date TEXT NOT NULL,
            room_no TEXT NOT NULL,
            source TEXT NOT NULL,
            problem_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            responsibility TEXT NOT NULL,
            rectification_measure TEXT,
            rectification_status TEXT NOT NULL DEFAULT '待整改',
            review_result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stay_date, room_no, source)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS rectification_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            record_no TEXT NOT NULL,
            review_conclusion TEXT NOT NULL,
            experience_summary TEXT,
            prevention_measures TEXT,
            recurrence_risk TEXT NOT NULL DEFAULT '低',
            reviewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reviewer TEXT,
            FOREIGN KEY(review_id) REFERENCES bad_reviews(id) ON DELETE CASCADE,
            UNIQUE(review_id)
        )''')
        cls.conn.commit()

    @classmethod
    def _seed_data(cls):
        c = cls.conn.cursor()
        base_date = datetime(2024, 6, 1)
        for i in range(10):
            stay = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            created = (base_date + timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
            updated = (base_date + timedelta(days=i + 3)).strftime("%Y-%m-%d %H:%M:%S")
            room_no = f"{(i % 7) + 1}0{1 + (i % 2)}"
            problem = ["卫生问题", "设施故障", "服务态度", "噪音干扰"][i % 4]
            source = ["携程", "美团"][i % 2]
            resp = ["客房清洁", "工程维修"][i % 2]
            status = "已完成" if i < 8 else "整改中"
            c.execute(
                "INSERT OR IGNORE INTO bad_reviews "
                "(record_no, stay_date, room_no, source, problem_type, summary, responsibility, "
                "rectification_status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (f"CP2024060{i:02d}", stay, room_no, source, problem,
                 f"差评摘要{i}" * 2, resp, status, created, updated)
            )
        cls.conn.commit()

        conclusions = ["整改有效", "整改部分有效", "整改无效", "需持续跟踪", "整改有效",
                        "整改部分有效", "整改无效", "整改有效"]
        risks = ["低", "中", "高", "低", "低", "中", "高", "低"]
        for i in range(8):
            review_id = i + 1
            c.execute(
                "INSERT OR IGNORE INTO rectification_reviews "
                "(review_id, record_no, review_conclusion, recurrence_risk, reviewed_at, reviewer) "
                "VALUES (?,?,?,?,?,?)",
                (review_id, f"CP2024060{i:02d}", conclusions[i], risks[i],
                 "2024-06-15 10:00:00", "测试员")
            )
        cls.conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.mock_db = MagicMock()
        self.service = StatisticsService(self.mock_db)

    def test_compute_comparison_analysis(self):
        rows = [
            {"review_conclusion": "整改有效", "recurrence_risk": "低",
             "created_at": "2024-06-01 10:00:00", "updated_at": "2024-06-04 10:00:00"},
            {"review_conclusion": "整改无效", "recurrence_risk": "高",
             "created_at": "2024-06-02 10:00:00", "updated_at": "2024-06-05 10:00:00"},
            {"review_conclusion": None, "recurrence_risk": None,
             "created_at": "2024-06-03 10:00:00", "updated_at": "2024-06-06 10:00:00"},
        ]
        result = self.service.compute_comparison_analysis(rows)
        self.assertEqual(result["total_completed"], 3)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["not_reviewed"], 1)
        self.assertEqual(result["avg_rectification_duration"], 3.0)
        self.assertAlmostEqual(result["pass_rate"], 33.3, places=1)

    def test_compute_recurrence_stats(self):
        rows = [
            {"problem_type": "卫生问题", "recurrence_risk": "高"},
            {"problem_type": "卫生问题", "recurrence_risk": "中"},
            {"problem_type": "卫生问题", "recurrence_risk": "低"},
            {"problem_type": "设施故障", "recurrence_risk": "低"},
        ]
        result = self.service.compute_recurrence_stats(rows)
        self.assertEqual(len(result), 2)
        hygiene = next(r for r in result if r["problem_type"] == "卫生问题")
        self.assertEqual(hygiene["total"], 3)
        self.assertEqual(hygiene["high_risk"], 1)
        self.assertEqual(hygiene["medium_risk"], 1)
        self.assertEqual(hygiene["low_risk"], 1)
        self.assertAlmostEqual(hygiene["recurrence_rate"], 66.7, places=1)

    def test_compute_recurrence_stats_null_risk(self):
        rows = [
            {"problem_type": "卫生问题", "recurrence_risk": None},
        ]
        result = self.service.compute_recurrence_stats(rows)
        self.assertEqual(result[0]["no_risk"], 1)

    def test_compute_duration_stats(self):
        rows = [
            {"problem_type": "卫生问题", "created_at": "2024-06-01 10:00:00",
             "updated_at": "2024-06-04 10:00:00"},
            {"problem_type": "卫生问题", "created_at": "2024-06-01 10:00:00",
             "updated_at": "2024-06-11 10:00:00"},
            {"problem_type": "设施故障", "created_at": "2024-06-02 10:00:00",
             "updated_at": "2024-06-05 10:00:00"},
        ]
        result = self.service.compute_duration_stats(rows)
        self.assertEqual(result["overall"]["total_count"], 3)
        self.assertAlmostEqual(result["overall"]["avg_duration"], 5.3, places=1)
        self.assertEqual(result["overall"]["max_duration"], 10)
        self.assertEqual(result["overall"]["min_duration"], 3)

        hygiene = next(r for r in result["by_problem"] if r["problem_type"] == "卫生问题")
        self.assertEqual(hygiene["count"], 2)
        self.assertAlmostEqual(hygiene["avg_duration"], 6.5, places=1)
        self.assertEqual(hygiene["max_duration"], 10)
        self.assertEqual(hygiene["min_duration"], 3)

    def test_compute_pass_rate_stats(self):
        rows = [
            {"problem_type": "卫生问题", "room_no": "101", "source": "携程",
             "responsibility": "客房清洁", "review_conclusion": "整改有效"},
            {"problem_type": "卫生问题", "room_no": "301", "source": "美团",
             "responsibility": "客房清洁", "review_conclusion": "整改无效"},
            {"problem_type": "设施故障", "room_no": "101", "source": "携程",
             "responsibility": "工程维修", "review_conclusion": "整改有效"},
        ]
        result = self.service.compute_pass_rate_stats(rows)
        self.assertIn("by_problem_type", result)
        self.assertIn("by_responsibility", result)
        self.assertIn("by_source", result)
        self.assertIn("by_room_type", result)

        hygiene = next(r for r in result["by_problem_type"] if r["name"] == "卫生问题")
        self.assertEqual(hygiene["total"], 2)
        self.assertEqual(hygiene["passed"], 1)
        self.assertEqual(hygiene["failed"], 1)
        self.assertEqual(hygiene["pass_rate"], 50.0)

    def test_fetch_completed_reviews_with_filter(self):
        captured_query = []
        def mock_fetch_all(query, params=None):
            captured_query.append((query, params))
            return []
        self.mock_db.fetch_all = mock_fetch_all

        fp = ReviewFilterParams(
            start_date="2024-01-01",
            end_date="2024-12-31",
            problem_type="卫生问题",
        )
        self.service.fetch_completed_reviews(fp)
        query, params = captured_query[0]
        self.assertIn("stay_date >= ?", query)
        self.assertIn("stay_date <= ?", query)
        self.assertIn("problem_type = ?", query)
        self.assertIn("rectification_status = '已完成'", query)
        self.assertEqual(params, ["2024-01-01", "2024-12-31", "卫生问题"])

    def test_fetch_completed_reviews_with_join(self):
        captured_query = []
        def mock_fetch_all(query, params=None):
            captured_query.append((query, params))
            return []
        self.mock_db.fetch_all = mock_fetch_all

        fp = ReviewFilterParams()
        self.service.fetch_completed_reviews(
            fp,
            join_clause="LEFT JOIN rectification_reviews rr ON br.id = rr.review_id",
            extra_select=", rr.review_conclusion",
        )
        query, _ = captured_query[0]
        self.assertIn("LEFT JOIN rectification_reviews", query)
        self.assertIn("rr.review_conclusion", query)

    def test_room_type_filtering(self):
        self.mock_db.fetch_all = MagicMock(return_value=[
            {"room_no": "101", "problem_type": "卫生问题"},
            {"room_no": "301", "problem_type": "设施故障"},
        ])
        fp = ReviewFilterParams(room_type=ROOM_TYPES[0])
        rows = self.service.fetch_completed_reviews(fp)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["room_no"], "101")

    def test_comparison_analysis_empty_data(self):
        result = self.service.compute_comparison_analysis([])
        self.assertEqual(result["total_completed"], 0)
        self.assertEqual(result["pass_rate"], 0.0)
        self.assertEqual(result["avg_rectification_duration"], 0)

    def test_duration_stats_empty_data(self):
        result = self.service.compute_duration_stats([])
        self.assertEqual(result["overall"]["total_count"], 0)
        self.assertEqual(result["overall"]["avg_duration"], 0)
        self.assertEqual(result["by_problem"], [])

    def test_recurrence_stats_empty_data(self):
        result = self.service.compute_recurrence_stats([])
        self.assertEqual(result, [])

    def test_pass_rate_stats_empty_data(self):
        result = self.service.compute_pass_rate_stats([])
        self.assertEqual(result["by_problem_type"], [])
        self.assertEqual(result["by_responsibility"], [])


class TestReviewFilterParamsDataclass(unittest.TestCase):
    def test_default_values(self):
        fp = ReviewFilterParams()
        self.assertEqual(fp.start_date, "")
        self.assertEqual(fp.end_date, "")
        self.assertEqual(fp.problem_type, "")
        self.assertEqual(fp.room_type, "")
        self.assertEqual(fp.source, "")
        self.assertEqual(fp.responsibility, "")

    def test_custom_values(self):
        fp = ReviewFilterParams(
            start_date="2024-01-01",
            end_date="2024-12-31",
            problem_type="卫生问题",
        )
        self.assertEqual(fp.start_date, "2024-01-01")
        self.assertEqual(fp.problem_type, "卫生问题")


if __name__ == "__main__":
    unittest.main()

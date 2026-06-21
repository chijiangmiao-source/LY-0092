from typing import List, Optional, Tuple
from datetime import datetime

from app.database.db_manager import DatabaseManager
from app.models.models import RectificationKnowledge, ValidationResult


class KnowledgeDAO:
    def __init__(self):
        self.db = DatabaseManager()

    def validate(self, knowledge: RectificationKnowledge, exclude_id: Optional[int] = None) -> ValidationResult:
        errors = []

        if not knowledge.problem_type:
            errors.append("问题类型不能为空")

        if not knowledge.typical_scenario.strip():
            errors.append("典型场景不能为空")

        if not knowledge.cause_analysis.strip():
            errors.append("原因分析不能为空")

        if not knowledge.recommended_measures.strip():
            errors.append("推荐整改措施不能为空")

        if not knowledge.review_points.strip():
            errors.append("复查要点不能为空")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def create(self, knowledge: RectificationKnowledge) -> Tuple[Optional[RectificationKnowledge], ValidationResult]:
        validation = self.validate(knowledge)
        if not validation:
            return None, validation

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        knowledge.created_at = now
        knowledge.updated_at = now

        cursor = self.db.execute_query('''
            INSERT INTO rectification_knowledge (
                problem_type, typical_scenario, cause_analysis,
                recommended_measures, review_points, applicable_rooms,
                use_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            knowledge.problem_type, knowledge.typical_scenario,
            knowledge.cause_analysis, knowledge.recommended_measures,
            knowledge.review_points, knowledge.applicable_rooms,
            knowledge.use_count, knowledge.created_at, knowledge.updated_at
        ))
        knowledge.id = cursor.lastrowid
        return knowledge, validation

    def update(self, knowledge: RectificationKnowledge) -> Tuple[Optional[RectificationKnowledge], ValidationResult]:
        validation = self.validate(knowledge, exclude_id=knowledge.id)
        if not validation:
            return None, validation

        knowledge.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.db.execute_query('''
            UPDATE rectification_knowledge SET
                problem_type = ?, typical_scenario = ?, cause_analysis = ?,
                recommended_measures = ?, review_points = ?, applicable_rooms = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            knowledge.problem_type, knowledge.typical_scenario,
            knowledge.cause_analysis, knowledge.recommended_measures,
            knowledge.review_points, knowledge.applicable_rooms,
            knowledge.updated_at, knowledge.id
        ))

        return knowledge, validation

    def delete(self, knowledge_id: int) -> bool:
        self.db.execute_query("DELETE FROM rectification_knowledge WHERE id = ?", (knowledge_id,))
        return True

    def get_by_id(self, knowledge_id: int) -> Optional[RectificationKnowledge]:
        row = self.db.fetch_one("SELECT * FROM rectification_knowledge WHERE id = ?", (knowledge_id,))
        return RectificationKnowledge.from_row(row)

    def get_by_problem_type(self, problem_type: str) -> List[RectificationKnowledge]:
        rows = self.db.fetch_all(
            "SELECT * FROM rectification_knowledge WHERE problem_type = ? ORDER BY use_count DESC, created_at DESC",
            (problem_type,)
        )
        return [RectificationKnowledge.from_row(row) for row in rows]

    def get_all(self, problem_type: str = "", keyword: str = "") -> List[RectificationKnowledge]:
        query = "SELECT * FROM rectification_knowledge WHERE 1=1"
        params = []

        if problem_type:
            query += " AND problem_type = ?"
            params.append(problem_type)

        if keyword:
            query += " AND (typical_scenario LIKE ? OR cause_analysis LIKE ? OR recommended_measures LIKE ? OR review_points LIKE ?)"
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern, keyword_pattern])

        query += " ORDER BY use_count DESC, created_at DESC"
        rows = self.db.fetch_all(query, params)
        return [RectificationKnowledge.from_row(row) for row in rows]

    def increment_use_count(self, knowledge_id: int) -> None:
        self.db.execute_query(
            "UPDATE rectification_knowledge SET use_count = use_count + 1, updated_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), knowledge_id)
        )

    def get_statistics(self) -> dict:
        total = self.db.fetch_one("SELECT COUNT(*) as cnt FROM rectification_knowledge")["cnt"]
        by_problem_type = self.db.fetch_all("""
            SELECT problem_type, COUNT(*) as cnt, SUM(use_count) as total_uses
            FROM rectification_knowledge
            GROUP BY problem_type ORDER BY cnt DESC
        """)
        most_used = self.db.fetch_all("""
            SELECT * FROM rectification_knowledge
            ORDER BY use_count DESC LIMIT 5
        """)

        return {
            "total": total,
            "by_problem_type": [
                {"problem_type": row["problem_type"], "count": row["cnt"], "total_uses": row["total_uses"]}
                for row in by_problem_type
            ],
            "most_used": [RectificationKnowledge.from_row(row) for row in most_used]
        }

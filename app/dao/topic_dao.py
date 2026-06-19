from typing import List, Optional
from datetime import datetime

from app.database.db_manager import DatabaseManager
from app.models.models import SpecialTopic, BadReview
from app.utils.constants import CONSECUTIVE_SAME_PROBLEM_THRESHOLD


class TopicDAO:
    def __init__(self):
        self.db = DatabaseManager()

    def create_topic_for_consecutive_problems(self, reviews: List[BadReview]) -> Optional[SpecialTopic]:
        if len(reviews) < CONSECUTIVE_SAME_PROBLEM_THRESHOLD:
            return None

        problem_type = reviews[0].problem_type

        existing = self.db.fetch_one("""
            SELECT * FROM special_topics
            WHERE problem_type = ? AND status = '进行中'
            ORDER BY created_at DESC LIMIT 1
        """, (problem_type,))

        if existing:
            topic = SpecialTopic.from_row(existing)
            for review in reviews:
                self._add_review_to_topic(topic.id, review.id)
            return topic

        topic = SpecialTopic(
            topic_name=f"{problem_type}专项整改",
            problem_type=problem_type,
            trigger_reason=f"连续出现{CONSECUTIVE_SAME_PROBLEM_THRESHOLD}条同类问题",
            status="进行中",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        cursor = self.db.execute_query('''
            INSERT INTO special_topics (topic_name, problem_type, trigger_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (topic.topic_name, topic.problem_type, topic.trigger_reason, topic.status, topic.created_at))

        topic.id = cursor.lastrowid

        for review in reviews:
            self._add_review_to_topic(topic.id, review.id)
            topic.review_ids.append(review.id)

        return topic

    def _add_review_to_topic(self, topic_id: int, review_id: int):
        self.db.execute_query('''
            INSERT OR IGNORE INTO topic_reviews (topic_id, review_id)
            VALUES (?, ?)
        ''', (topic_id, review_id))

    def get_all(self, status: Optional[str] = None) -> List[SpecialTopic]:
        query = "SELECT * FROM special_topics"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        rows = self.db.fetch_all(query, params)
        topics = [SpecialTopic.from_row(row) for row in rows]

        for topic in topics:
            topic.review_ids = self._get_topic_review_ids(topic.id)

        return topics

    def _get_topic_review_ids(self, topic_id: int) -> List[int]:
        rows = self.db.fetch_all("""
            SELECT review_id FROM topic_reviews WHERE topic_id = ?
        """, (topic_id,))
        return [row["review_id"] for row in rows]

    def get_topic_reviews(self, topic_id: int) -> List[BadReview]:
        rows = self.db.fetch_all("""
            SELECT br.* FROM bad_reviews br
            INNER JOIN topic_reviews tr ON br.id = tr.review_id
            WHERE tr.topic_id = ?
            ORDER BY br.created_at DESC
        """, (topic_id,))
        return [BadReview.from_row(row) for row in rows]

    def close_topic(self, topic_id: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute_query("""
            UPDATE special_topics SET status = '已关闭', closed_at = ? WHERE id = ?
        """, (now, topic_id))
        return True

    def reopen_topic(self, topic_id: int) -> bool:
        self.db.execute_query("""
            UPDATE special_topics SET status = '进行中', closed_at = NULL WHERE id = ?
        """, (topic_id,))
        return True

    def delete(self, topic_id: int) -> bool:
        self.db.execute_query("DELETE FROM topic_reviews WHERE topic_id = ?", (topic_id,))
        self.db.execute_query("DELETE FROM special_topics WHERE id = ?", (topic_id,))
        return True

    def get_by_id(self, topic_id: int) -> Optional[SpecialTopic]:
        row = self.db.fetch_one("SELECT * FROM special_topics WHERE id = ?", (topic_id,))
        if not row:
            return None
        topic = SpecialTopic.from_row(row)
        topic.review_ids = self._get_topic_review_ids(topic.id)
        return topic

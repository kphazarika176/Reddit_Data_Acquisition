from typing import List, Dict, Any
from src.models.reddit import QAPair
from src.logger import get_logger

logger = get_logger(__name__)


class QADetector:
    """Detects Question-Answer pairs from comments, even without nested reply tree."""

    @staticmethod
    def extract_qa_pairs(post_id: str, comment_tree_or_list: List[Dict[str, Any]] or List[Any]) -> List[QAPair]:
        qa_pairs = []

        # First flatten all comments (in case we still get a tree or object list)
        comments_flat = []
        def flatten(nodes):
            for node in nodes:
                item = node.to_dict() if hasattr(node, 'to_dict') else node
                comments_flat.append(item)
                if isinstance(item, dict) and 'replies' in item:
                    flatten(item['replies'])
        flatten(comment_tree_or_list)

        # Sort by score descending so we get best possible answers first
        comments_sorted = sorted(
            [c for c in comments_flat if c.get('body', '').strip() not in ('[deleted]', '[removed]', '')],
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        # Find all comments that contain a question mark (potential questions)
        question_comments = [c for c in comments_sorted if '?' in c.get('body', '')]

        # Track used answers so the same comment cannot be assigned to multiple questions
        used_answer_ids = set()

        # For each question, find the best possible answer:
        for question_c in question_comments:
            # Find comments that aren't the question itself, not already used as answer, not a question themselves, and not deleted/removed
            possible_answers = [
                c for c in comments_sorted
                if c.get('comment_id') != question_c.get('comment_id')
                and c.get('comment_id') not in used_answer_ids
                and '?' not in c.get('body', '')
                and c.get('body', '').strip() not in ('[deleted]', '[removed]', '')
            ]

            # Take the highest-scoring comment as the answer
            if possible_answers:
                best_answer = possible_answers[0]
                used_answer_ids.add(best_answer.get('comment_id'))
                qa_pairs.append(QAPair(
                    post_id=post_id,
                    question_comment_id=question_c.get('comment_id'),
                    answer_comment_id=best_answer.get('comment_id'),
                    question=question_c.get('body', ''),
                    answer=best_answer.get('body', '')
                ))

        logger.info(f"Detected {len(qa_pairs)} valid Q&A pairs in post {post_id}.")
        return qa_pairs


import html
from typing import List, Dict, Any
from src.models.reddit import QAPair
from src.logger import get_logger

logger = get_logger(__name__)


def is_valid_comment_text(text: str) -> bool:
    """Check if comment body is valid and not a deletion/removal placeholder."""
    if not text:
        return False
    clean = html.unescape(str(text)).strip().lower()
    if not clean or clean in ('[deleted]', '[removed]', '[ removed by reddit ]'):
        return False
    if clean.startswith('[deleted') or clean.startswith('[removed'):
        return False
    return True


class QADetector:
    """Detects Question-Answer pairs from comments, even without nested reply tree."""

    @staticmethod
    def is_question(comment_or_text: Any) -> bool:
        """
        Determines if a comment is primarily a genuine question.

        Heuristics applied:
        1. Decodes HTML entities (e.g., &#39; -> ').
        2. Requires a question mark '?' to be present.
        3. Rejects long comments (>60 words or >350 chars) containing embedded questions.
        4. Accepts text ending with '?' (ignoring trailing quotes, parens, brackets).
        5. Accepts text where '?' is near the end (allowing short sign-offs like 'Thanks').
        """
        if isinstance(comment_or_text, dict):
            text = comment_or_text.get('body', '')
        elif hasattr(comment_or_text, 'body'):
            text = getattr(comment_or_text, 'body', '')
        elif isinstance(comment_or_text, str):
            text = comment_or_text
        else:
            text = str(comment_or_text) if comment_or_text else ''

        if not is_valid_comment_text(text):
            return False

        # Decode HTML entities (e.g., &#39; -> ', &quot; -> ")
        text = html.unescape(text).strip()

        # Must contain at least one question mark
        if '?' not in text:
            return False

        words = text.split()
        word_count = len(words)
        char_count = len(text)

        # Reject long paragraphs, rants, or discussions containing embedded rhetorical questions
        if word_count > 60 or char_count > 350:
            return False

        # Check if text ends with '?' (ignoring trailing quotes, parens, brackets)
        cleaned_end = text.rstrip(' "\')}]')
        if cleaned_end.endswith('?'):
            return True

        # Check if question mark is near the end of the text (allowing short trailing sign-offs)
        qmark_pos = text.rfind('?')
        trailing_chars = len(text) - (qmark_pos + 1)
        if trailing_chars <= 25:
            return True

        return False

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
            [c for c in comments_flat if is_valid_comment_text(c.get('body', ''))],
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        # Find all comments that are genuine questions using is_question helper
        question_comments = [c for c in comments_sorted if QADetector.is_question(c)]

        # Track used answers so the same comment cannot be assigned to multiple questions
        used_answer_ids = set()

        # For each question, find the best contextually matching answer:
        for question_c in question_comments:
            q_id = question_c.get('comment_id')
            q_parent = question_c.get('parent_id')

            # Priority 1: Direct replies (candidate comment parent_id is this question's comment_id)
            direct_replies = [
                c for c in comments_sorted
                if c.get('parent_id') == q_id
                and c.get('comment_id') not in used_answer_ids
                and not QADetector.is_question(c)
            ]

            # Priority 2: Thread Sibling replies (candidate shares the same parent comment)
            sibling_replies = [
                c for c in comments_sorted
                if c.get('parent_id') == q_parent
                and c.get('comment_id') != q_id
                and c.get('comment_id') not in used_answer_ids
                and not QADetector.is_question(c)
            ] if q_parent and q_parent != post_id else []

            # Priority 3: Fallback top-scoring available answer in post
            fallback_replies = [
                c for c in comments_sorted
                if c.get('comment_id') != q_id
                and c.get('comment_id') not in used_answer_ids
                and not QADetector.is_question(c)
            ]

            best_answer = None
            if direct_replies:
                best_answer = direct_replies[0]
            elif sibling_replies:
                best_answer = sibling_replies[0]
            elif fallback_replies:
                best_answer = fallback_replies[0]

            if best_answer:
                used_answer_ids.add(best_answer.get('comment_id'))

                question_text = html.unescape(question_c.get('body', '')).strip()
                answer_text = html.unescape(best_answer.get('body', '')).strip()

                qa_pairs.append(QAPair(
                    post_id=post_id,
                    question_comment_id=q_id,
                    answer_comment_id=best_answer.get('comment_id'),
                    question=question_text,
                    answer=answer_text
                ))

        logger.info(f"Detected {len(qa_pairs)} valid Q&A pairs in post {post_id}.")
        return qa_pairs


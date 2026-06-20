from typing import List, Dict, Any
from src.models.reddit import QAPair
from src.logger import get_logger

logger = get_logger(__name__)

class QADetector:
    """Detects Question-Answer pairs within a comment tree."""
    
    @staticmethod
    def extract_qa_pairs(news_id: str, post_id: str, comment_tree: List[Dict[str, Any]]) -> List[QAPair]:
        qa_pairs = []
        
        def traverse(nodes: List[Dict[str, Any]]):
            for node in nodes:
                body = node.get('body', '').strip()
                replies = node.get('replies', [])
                
                # Simple heuristic: If it ends with a question mark and has replies
                if body.endswith('?') and replies:
                    # Find the highest scored reply to act as the answer
                    best_reply = max(replies, key=lambda x: x.get('score', 0))
                    
                    # Avoid deleted comments
                    if best_reply.get('body') not in ('[deleted]', '[removed]'):
                        qa_pairs.append(QAPair(
                            news_id=news_id,
                            post_id=post_id,
                            question_comment_id=node.get('comment_id'),
                            answer_comment_id=best_reply.get('comment_id'),
                            question=body,
                            answer=best_reply.get('body', '')
                        ))
                
                # Recursively check replies
                traverse(replies)
                
        traverse(comment_tree)
        logger.info(f"Detected {len(qa_pairs)} valid Q&A pairs in post {post_id}.")
        return qa_pairs

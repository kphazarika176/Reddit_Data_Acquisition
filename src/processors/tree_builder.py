from typing import List, Dict, Any
from src.models.reddit import RedditComment
from src.logger import get_logger

logger = get_logger(__name__)

class CommentTreeBuilder:
    """Builds a recursive tree structure from a flat list of comments."""
    
    @staticmethod
    def build_tree(comments: List[RedditComment], root_id: str) -> List[Dict[str, Any]]:
        # Create a lookup map: parent_id -> list of child comments
        children_map = {}
        for comment in comments:
            parent = comment.parent_id
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(comment)
            
        def build_node(comment: RedditComment, depth: int) -> Dict[str, Any]:
            comment.depth = depth
            node = comment.to_dict()
            
            # Recursively find children
            child_comments = children_map.get(comment.comment_id, [])
            # Sort children by score descending for better thread readability
            child_comments.sort(key=lambda x: x.score, reverse=True)
            
            node['replies'] = [build_node(child, depth + 1) for child in child_comments]
            return node
            
        # The root level comments are those whose parent is the post_id
        root_comments = children_map.get(root_id, [])
        root_comments.sort(key=lambda x: x.score, reverse=True)
        
        tree = [build_node(c, 0) for c in root_comments]
        
        logger.info(f"Built comment tree with {len(root_comments)} top-level comments.")
        return tree

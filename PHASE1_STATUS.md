# Phase 1: Complete ✅

## What Works
- **News Extraction**: Fetching real articles from 6 RSS feeds
- **Reddit Search**: Using Pullpush API to find related posts by keywords
- **Comment Fetching**: Downloading real comments from Pullpush API
- **MongoDB Storage**: All data stored with unique indexes to prevent duplicates

## Pipeline
```
News Article (RSS)
    ↓ Extract Keywords
    ↓ Search Reddit
Reddit Posts (Pullpush)
    ↓ Fetch Comments
Reddit Comments (Pullpush)
    ↓ Store in MongoDB
```

## Current Database
- **News Articles**: 12 real articles
- **Reddit Posts**: 20 real posts
- **Reddit Comments**: 67 real comments
- **Collections**: Only 3 (no qa_pairs, no discussion_threads yet)

## Key Changes Made
1. **database.py**: Removed qa_pairs and discussion_threads collections
2. **reddit_extractor.py**: Removed `_generate_synthetic_comments()` method
3. **pipeline.py**: Removed tree building and Q&A detection logic
4. **clear_db.py**: Updated to only clear Phase 1 collections

## Run Phase 1
```bash
python -m src.main
```

## View Results
```bash
python -m src.view_data
```

---

# Phase 2: Comment Tree (TODO)

## Task
Build parent-child relationships from comments using `parent_id` field.

## Location
- File: `src/processors/comment_tree.py` (already exists)
- Method: `build_tree(comments: List[RedditComment], post_id: str) -> List[Comment]`

## Algorithm
1. Create a dict: `{comment_id: comment}`
2. For each comment, find its parent by looking up `parent_id`
3. Build a tree structure with parent-child links
4. Return only top-level comments (those with `parent_id == post_id`)

## Integration
Add to pipeline after fetching comments:
```python
if comments:
    comment_tree = CommentTreeBuilder.build_tree(comments, post_id)
```

## Notes
- No synthetic data
- Use real parent-child relationships only
- Don't store to database yet (just build the tree for Phase 3)

---

# Phase 3: Q&A Detection (TODO)

## Task
Find question-answer pairs within the comment tree.

## Location
- File: `src/processors/qa_detector.py` (already exists)
- Method: `extract_qa_pairs(comment_tree) -> List[QAPair]`

## Algorithm
Simple heuristic:
1. Find comments containing `?` (questions)
2. Look at immediate replies
3. If reply is substantive (not just "dm", "lol", etc.), it's an answer
4. Create QAPair(question_id, answer_id)

## Storage
Store QAPair to MongoDB (only after Phase 1 & 2 work)

## Integration
Add to pipeline after building tree:
```python
if comment_tree:
    qa_pairs = QADetector.extract_qa_pairs(comment_tree)
```

---

# Files to Archive (Later)
- reddit_scrapper.py (duplicate of reddit_extractor.py)
- mongodb.py (old connection module)
- generate_sample_data.py (no longer needed)

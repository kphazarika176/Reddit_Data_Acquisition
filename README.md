# Reddit Content Acquisition Pipeline

A clean, modular ETL pipeline that collects Reddit discussions using the Apify Reddit Scraper Lite actor, stores raw data in MongoDB, and generates structured Question-Answer (Q&A) pairs using heuristic-based processing.

---

## Features

- **Apify-powered Reddit scraping** using the `trudax/reddit-scraper-lite` actor.
- **Modular ETL architecture** separating extraction, storage, processing, and viewing.
- **MongoDB storage** for posts, comments, and generated Q&A pairs.
- **Duplicate prevention** using unique MongoDB indexes.
- **Heuristic-based Q&A generation** that works even when nested Reddit reply chains are unavailable.
- **Interactive CLI** for ingestion, processing, viewing data, and database management.

---

# Architecture

```text
            Apify Reddit Scraper
                    │
                    ▼
          Fetch Posts & Comments
                    │
                    ▼
          Normalize Raw Data
                    │
                    ▼
              MongoDB Storage
      ┌─────────────┼─────────────┐
      │             │             │
 reddit_posts  reddit_comments  qa_pairs
                    │
                    ▼
          Q&A Generation Module
                    │
                    ▼
         Heuristic Q&A Detection
```

---

# Database Structure

```
reddit_news_db
│
├── reddit_posts
│   ├── post_id
│   ├── subreddit
│   ├── title
│   ├── body
│   ├── author
│   ├── score
│   ├── url
│   ├── created_utc
│   └── num_comments
│
├── reddit_comments
│   ├── comment_id
│   ├── post_id
│   ├── parent_id
│   ├── body
│   ├── author
│   ├── score
│   ├── depth
│   └── created_utc
│
└── qa_pairs
    ├── post_id
    ├── question_comment_id
    ├── answer_comment_id
    ├── question
    └── answer
```

---

# Project Structure

```
src/
│
├── extractors/
│   └── apify_extractor.py
│
├── processors/
│   ├── tree_builder.py
│   └── qa_detector.py
│
├── models/
│   └── reddit.py
│
├── apify_pipeline.py
├── qa_generator.py
├── database.py
├── config.py
├── logger.py
├── view_data.py
└── main.py
```

---

# Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd "REDDIT CONTENT ACQUISITION"
```

## 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD

```cmd
.venv\Scripts\activate.bat
```

Linux / macOS

```bash
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create a `.env` file:

```ini
MONGO_URI=your_mongodb_connection_string
DB_NAME=reddit_news_db

APIFY_API_TOKEN=your_apify_token
APIFY_ACTOR_ID=trudax/reddit-scraper-lite
```

---

# Running the Project

```bash
python -m src.main
```

---

# CLI Options

1. Fresh Apify Ingestion
   - Clears existing collections
   - Downloads fresh Reddit posts and comments

2. Update Existing Database
   - Downloads only new content
   - Existing records are skipped automatically

3. Generate Q&A Pairs
   - Processes stored comments
   - Generates heuristic-based Q&A pairs

4. View Stored Data
   - Displays collection statistics
   - Shows sample documents

5. Delete Database
   - Clears all collections

6. Exit

---

# Q&A Detection Strategy

The project generates Q&A pairs using a heuristic approach rather than relying entirely on Reddit reply chains.

For each post:

1. Collect all comments.
2. Identify comments containing a question (`?`).
3. Rank comments by score.
4. Pair each detected question with the highest-scoring valid non-question comment.
5. Ignore deleted or removed comments.

This approach allows Q&A generation even when the scraper does not preserve complete reply relationships.

---

# Technologies Used

- Python 3
- MongoDB
- PyMongo
- Apify API
- dotenv
- Requests

---

# Notes

- MongoDB unique indexes prevent duplicate records.
- Apify handles Reddit scraping without requiring Reddit API credentials.
- The pipeline is modular, making it easy to replace the scraper or improve the Q&A detection algorithm in the future.
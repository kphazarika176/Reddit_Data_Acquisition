# Reddit Content Acquisition Pipeline

A clean, modular ETL pipeline that collects Reddit discussions using the Apify Reddit Scraper Lite actor, stores raw data in a local **SQLite** database, generates structured Question-Answer (Q&A) pairs using heuristic-based processing, and exports processed data to formatted Excel workbooks.

---

## Key Features

- **Apify-powered Reddit Scraping**: Reliable data extraction using the `trudax/reddit-scraper-lite` actor.
- **SQLite Storage Engine**: Lightweight relational database storage for posts, comments, and Q&A pairs using primary keys, foreign key constraints, and indexes.
- **Duplicate Prevention**: Uses SQLite primary keys together with `INSERT OR IGNORE` to prevent duplicate records during repeated ingestion runs.
- **Heuristic-based Q&A Detection**:
  - Processes flat comment lists directly to ensure comments with broken parent chains are not dropped.
  - Prevents the same comment from being reused as an answer across multiple questions.
  - Excludes comments that are themselves questions (`?`) from being assigned as answers.
- **Excel Export Utility**: Exports normalized SQLite tables (`posts`, `comments`, `qa_pairs`) into separate worksheets in a formatted `.xlsx` workbook using `openpyxl`.
- **Interactive CLI**: Menu-driven interface for running fresh ingestions, incremental updates, Q&A generation, viewing database statistics, exporting to Excel, and clearing data.

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
                 SQLite Database
         (data/reddit_news.db)
       ┌───────────┼───────────┐
       │           │           │
     posts     comments     qa_pairs
       │           │           │
       └─────┬─────┘           │
             ▼                 │
     Q&A Generator             │
   (Heuristic Detection)       │
             │                 │
             └────────┬────────┘
                      ▼
             Export to Excel (.xlsx)
```

---

# Database Schema

```text
data/reddit_news.db
│
├── posts
│   ├── post_id      (TEXT, PRIMARY KEY)
│   ├── subreddit    (TEXT)
│   ├── title        (TEXT)
│   ├── body         (TEXT)
│   ├── author       (TEXT)
│   ├── score        (INTEGER)
│   ├── url          (TEXT)
│   ├── created_utc  (TEXT)
│   └── num_comments (INTEGER)
│
├── comments
│   ├── comment_id   (TEXT, PRIMARY KEY)
│   ├── post_id      (TEXT, NOT NULL, FOREIGN KEY -> posts.post_id)
│   ├── parent_id    (TEXT)
│   ├── body         (TEXT)
│   ├── author       (TEXT)
│   ├── score        (INTEGER)
│   ├── depth        (INTEGER)
│   └── created_utc  (TEXT)
│
├── qa_pairs
│   ├── question_comment_id (TEXT, NOT NULL)
│   ├── answer_comment_id   (TEXT, NOT NULL)
│   ├── post_id             (TEXT, NOT NULL, FOREIGN KEY -> posts.post_id)
│   ├── question            (TEXT)
│   ├── answer              (TEXT)
│   ├── score_signal        (INTEGER, DEFAULT 0)
│   └── PRIMARY KEY (question_comment_id, answer_comment_id)
│
└── Indexes
    ├── idx_comments_post   (comments.post_id)
    └── idx_qa_post         (qa_pairs.post_id)
```

---

# Project Structure

```text
.
├── data/                      # SQLite database files
├── logs/                      # Application log outputs
├── src/
│   ├── extractors/
│   │   └── apify_extractor.py # Apify API client and record normalizers
│   ├── models/
│   │   └── reddit.py          # Data models (RedditPost, RedditComment, QAPair)
│   ├── processors/
│   │   ├── qa_detector.py     # Heuristic Q&A detection algorithm
│   │   └── tree_builder.py    # Legacy utility (not used by the current Q&A pipeline)
│   ├── apify_pipeline.py      # Full & update ingestion pipelines
│   ├── config.py              # Environment configuration loader
│   ├── database.py            # SQLite DatabaseManager wrapper
│   ├── excel_exporter.py      # OpenPyXL Excel export utility
│   ├── logger.py              # Logging setup
│   ├── main.py                # CLI application entry point
│   ├── qa_generator.py        # Q&A pair extraction runner
│   └── view_data.py           # Database inspector and CLI viewer
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
└── README.md
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/kphazarika176/Reddit_Data_Acquisition.git
cd Reddit_Data_Acquisition
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv
```

**Activate Environment:**

- **Windows PowerShell:**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows CMD:**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root:

```ini
APIFY_API_TOKEN=your_apify_api_token_here
APIFY_ACTOR_ID=trudax/reddit-scraper-lite
SQLITE_DB_PATH=data/reddit_news.db
```

---

# Running the Application

Launch the interactive CLI:

```bash
python -m src.main
```

---

# CLI Options

```text
====== Reddit Data Acquisition ======
1. Apify Ingestion (Fresh)              # Clears database and fetches fresh posts & comments
2. Apify Ingestion (Update)             # Fetches new content; skips existing records automatically
3. Generate Q&A Pairs (from raw data)   # Processes flat comment list into high-quality Q&A pairs
4. View Stored Data                     # Displays record counts and sample posts/comments/Q&As
5. Export to Excel                      # Generates a formatted .xlsx report for all database tables
6. Delete Database                      # Clears all tables in the SQLite database
7. Exit
```

---

# Q&A Detection Strategy

The pipeline extracts Question-Answer pairs from raw Reddit discussions using a refined heuristic algorithm:

1. **Flat Comment Processing**: Processes the flat list of comments directly in `QADetector`, avoiding reliance on reconstructed reply trees and preserving comments even if parent chains are broken.
2. **Question Identification**: Filters all non-deleted/non-removed comments containing question marks (`?`).
3. **Answer Selection & Ranking**: Ranks candidate answer comments by Reddit score (highest first).
4. **Duplicate Prevention**: Tracks used answers so no single comment is assigned as an answer to multiple questions.
5. **Question Exclusion**: Excludes comments that are themselves questions from being selected as answers.

---

# Technologies Used

- **Language**: Python 3.10+
- **Database**: SQLite 3 (`sqlite3`)
- **Scraping Engine**: Apify API (`requests`) / `trudax/reddit-scraper-lite`
- **Data Export**: `openpyxl`
- **Configuration**: `python-dotenv`

---

# Notes

- Excel exports contain separate worksheets for posts, comments, and generated Q&A pairs.
- `qa_pairs` uses a composite primary key consisting of `question_comment_id` and `answer_comment_id`.
- SQLite uses `INSERT OR IGNORE` together with primary key constraints to prevent duplicate records during repeated ingestion runs.
- Database indexes on `comments(post_id)` and `qa_pairs(post_id)` improve lookup and retrieval performance.
- The pipeline does not require official Reddit API credentials, relying instead on the Apify Reddit Scraper Lite actor.
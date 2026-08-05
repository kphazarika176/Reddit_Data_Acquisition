# Reddit Content Acquisition & NLP Enrichment Pipeline

A modular, self-contained ETL & NLP pipeline that collects Reddit discussions using the top-rated **Apify Reddit Scraper** (`harshmaur/reddit-scraper`), stores normalized data in a local **SQLite** database, generates tiered Question-Answer (Q&A) pairs with reliability tagging, enriches content with VADER sentiment analysis & keyword/entity extraction, and exports processed datasets into professionally styled Excel workbooks.

---

## Key Features

- **Apify-Powered Scraping (`harshmaur/reddit-scraper`)**: Highly reliable, keyless scraping supporting full subreddit crawling, keyword search, date range filtering, and deep nested comment reply threads (140+ output fields).
- **Relational SQLite Database Engine**: Stores posts, comments, Q&A pairs, and system migration metadata using primary keys, foreign key constraints, indexes, and single-pass migration flags (`db_metadata`).
- **Single-Pass Cleaning Migration**: Performs HTML entity unescaping and submission boilerplate cleaning once during migration setup (`html_cleaned_v1`), avoiding expensive per-startup full table scans.
- **Tiered Q&A Detection with Reliability Metadata**:
  - Matches questions to answers using a 3-tier hierarchy: **Direct Replies** (`verified_direct_reply`, 0.95 confidence), **Thread Siblings** (`unverified_thread_sibling`, 0.70 confidence), and **Fallback Top-Score** (`unverified_fallback`, 0.40 confidence).
  - Prevents comment reuse across multiple questions and excludes sub-questions from answer candidates.
- **NLP Enrichment Layer**:
  - **VADER Sentiment Analysis**: Computes compound sentiment scores (-1.0 to +1.0) and assigns `positive`, `neutral`, or `negative` labels to post and comment bodies.
  - **Keyword & Proper Noun Entity Extraction**: Automatically extracts top meaningful terms and capitalized proper noun entities (e.g., product names, locations, organizations).
- **Preserved Engagement Metrics**: Preserves `score` (net upvotes), `depth` (thread nesting level), `num_comments`, and `score_signal` in both SQLite and Excel exports.
- **Professional Excel Exporter**: Generates structured `.xlsx` workbooks with separate worksheets (*Reddit Posts*, *Reddit Comments*, *Q&A Pairs*) using `openpyxl`.
- **Interactive CLI**: 9-choice menu interface for running fresh ingestions, incremental updates, Q&A generation, NLP enrichment, database viewing, Excel export, force re-cleaning, and database resets.

---

# Architecture & Detailed Pipeline Flow

> For a complete visual flowchart, sequence diagrams, and stage-by-stage data lifecycle documentation, see **[flow.md](flow.md)**.

```text
               Apify Reddit Scraper
             (harshmaur/reddit-scraper)
                         │
                         ▼
              Fetch Posts & Nested Comments
                         │
                         ▼
              Normalize Raw Data & Hierarchy
                         │
                         ▼
                  SQLite Database
               (data/reddit_news.db)
       ┌───────────┼───────────┼───────────┐
       │           │           │           │
     posts     comments     qa_pairs   db_metadata
       │           │           │           │
       └─────┬─────┘           │           │
             ▼                 │           │
     Q&A Generator             │           │
  (3-Tier Reliability)         │           │
             │                 │           │
             └────────┬────────┘           │
                      ▼                    │
            NLP Enrichment Layer           │
        (VADER & Entity Extraction)        │
                      │                    │
                      └─────────┬──────────┘
                                ▼
                     Export to Excel (.xlsx)
```

---

# Database Schema

```text
data/reddit_news.db
│
├── posts
│   ├── post_id         (TEXT, PRIMARY KEY)
│   ├── subreddit       (TEXT)
│   ├── title           (TEXT)
│   ├── body            (TEXT)
│   ├── author          (TEXT)
│   ├── score           (INTEGER)  -- Net Upvotes (Upvotes - Downvotes)
│   ├── url             (TEXT)
│   ├── created_utc     (TEXT)
│   ├── num_comments    (INTEGER)
│   ├── sentiment_score (REAL)     -- VADER Compound Score (-1.0 to 1.0)
│   ├── sentiment_label (TEXT)     -- positive / neutral / negative
│   └── keywords        (TEXT)     -- Comma-separated top keywords & entities
│
├── comments
│   ├── comment_id      (TEXT, PRIMARY KEY)
│   ├── post_id         (TEXT, NOT NULL, FOREIGN KEY -> posts.post_id)
│   ├── parent_id       (TEXT)     -- t3_... for post, t1_... for parent comment
│   ├── body            (TEXT)
│   ├── author          (TEXT)
│   ├── score           (INTEGER)  -- Net Upvotes
│   ├── depth           (INTEGER)  -- 0 (Top-Level), 1 (Direct Reply), 2+ (Sub-Reply)
│   ├── created_utc     (TEXT)
│   ├── sentiment_score (REAL)
│   ├── sentiment_label (TEXT)
│   └── keywords        (TEXT)
│
├── qa_pairs
│   ├── question_comment_id (TEXT, NOT NULL)
│   ├── answer_comment_id   (TEXT, NOT NULL)
│   ├── post_id             (TEXT, NOT NULL, FOREIGN KEY -> posts.post_id)
│   ├── question            (TEXT)
│   ├── answer              (TEXT)
│   ├── score_signal        (INTEGER, DEFAULT 0)
│   ├── match_type          (TEXT) -- direct_reply / thread_sibling / fallback_top_score
│   ├── verification_status (TEXT) -- verified_direct_reply / unverified_fallback
│   ├── confidence_score    (REAL) -- 0.40 to 0.95 confidence weight
│   └── PRIMARY KEY (question_comment_id, answer_comment_id)
│
├── db_metadata
│   ├── key        (TEXT, PRIMARY KEY) -- e.g. 'html_cleaned_v1'
│   ├── value      (TEXT)
│   └── updated_at (TEXT)
│
└── Indexes
    ├── idx_comments_post (comments.post_id)
    └── idx_qa_post       (qa_pairs.post_id)
```

---

# Data Field Explanations

### **`score` (Net Upvotes)**
* **Definition**: The net number of votes received by a post or comment (`score = Upvotes - Downvotes`).
* **Usage**: Indicates community agreement and relevance. High-scoring comments are prioritized by the Q&A Detector as candidate answers.

### **`depth` (Thread Nesting Level)**
* **Definition**: The position of a comment within the nested discussion tree:
  * **`depth = 0`**: **Top-Level Comment** (direct response to the post, `parent_id` starts with `t3_`).
  * **`depth = 1`**: **First-Level Reply** (direct response to a top-level comment, `parent_id` starts with `t1_`).
  * **`depth = 2, 3...`**: **Sub-Replies** (nested replies deeper in the thread chain).
* **Usage**: Used by `QADetector` to tag direct answer replies (`match_type: direct_reply`) with maximum confidence (0.95).

---

# Project Structure

```text
.
├── data/                      # SQLite database storage (reddit_news.db)
├── logs/                      # Log file outputs
├── src/
│   ├── extractors/
│   │   └── apify_extractor.py # Apify client (supports harshmaur & trudax actors, IPv4 fallback)
│   ├── models/
│   │   ├── __init__.py
│   │   └── reddit.py          # Dataclasses (RedditPost, RedditComment, QAPair)
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── nlp_enrichment.py  # VADER sentiment analysis & keyword/entity extraction
│   │   └── qa_detector.py     # 3-Tier heuristic Q&A pairing & reliability tagging
│   ├── apify_pipeline.py      # Ingestion pipeline manager
│   ├── config.py              # Environment configuration loader
│   ├── database.py            # SQLite DatabaseManager with migration tracking
│   ├── excel_exporter.py      # Styled Excel export utility (.xlsx)
│   ├── logger.py              # Application logging setup
│   ├── main.py                # Interactive CLI menu (Choices 1-9)
│   ├── qa_generator.py        # Q&A extraction runner
│   └── view_data.py           # Database statistics inspector
├── .env                       # Environment credentials and settings
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

## 2. Create & Activate Virtual Environment

```bash
python -m venv .venv
```

* **Windows PowerShell:** `.venv\Scripts\Activate.ps1`
* **Windows CMD:** `.venv\Scripts\activate.bat`
* **Linux / macOS:** `source .venv/bin/activate`

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create or update `.env` in the root directory:

```ini
APIFY_API_TOKEN=your_apify_token_here
APIFY_ACTOR_ID=harshmaur~reddit-scraper
SQLITE_DB_PATH=data/reddit_news.db
```

---

# Running the Application

Launch the interactive CLI menu:

```bash
python -m src.main
```

### CLI Menu Options

```text
====== Reddit Data Acquisition ======
1. Apify Ingestion (Fresh)                # Clears database & ingests fresh posts/comments
2. Apify Ingestion (Update)               # Appends new content; skips duplicates via primary keys
3. Generate Q&A Pairs (from raw data)     # Runs 3-tier Q&A pairing with reliability tagging
4. Run NLP Enrichment (Sentiment & Words) # Executes VADER sentiment analysis & entity extraction
5. View Stored Data                       # Displays database counts, scores, sentiment & sample Q&As
6. Export to Excel                        # Generates formatted workbook (Reddit Posts, Comments, Q&As)
7. Force Re-Clean Data (HTML & Tags)      # Manually re-runs HTML unescaping & submission cleaning
8. Delete Database                        # Resets database tables to empty state
9. Exit
```

---

# Q&A Detection Strategy

The pipeline extracts Question-Answer pairs using a 3-tier hierarchical matching strategy:

1. **Question Extraction**: Filters all comments containing question marks (`?`).
2. **Priority 1 (Direct Replies)**: Matches a question comment directly to comments where `parent_id == question_comment_id`. Tagged as `match_type: direct_reply`, `status: verified_direct_reply`, `confidence: 0.95`.
3. **Priority 2 (Thread Siblings)**: Matches to comments sharing the same parent in a discussion branch. Tagged as `match_type: thread_sibling`, `status: unverified_thread_sibling`, `confidence: 0.70`.
4. **Priority 3 (Fallback Top-Score)**: Matches to the highest-scoring available non-question comment in the post. Tagged as `match_type: fallback_top_score`, `status: unverified_fallback`, `confidence: 0.40`.
5. **Deduplication**: Prevents answer reuse across multiple questions and excludes sub-questions from answer selection.

---

# Technologies Used

- **Language**: Python 3.10+
- **Database**: SQLite 3 (`sqlite3`)
- **Scraping Engine**: Apify API (`requests`) / `harshmaur/reddit-scraper` (with IPv4 fallback resolution)
- **NLP Layer**: `vaderSentiment` (Sentiment Intensity Analyzer) + Regex Keyphrase/Entity Extractor
- **Data Export**: `openpyxl`
- **Configuration**: `python-dotenv`
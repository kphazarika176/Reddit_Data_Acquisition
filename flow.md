# Reddit Content Acquisition & NLP Enrichment Pipeline - Project Flow

This document provides a comprehensive end-to-end overview of the **Reddit Content Acquisition, Q&A Extraction, and NLP Enrichment** system architecture, data lifecycle, and internal execution flow.

---

## High-Level Architecture Flowchart

```mermaid
flowchart TD
    subgraph Execution ["1. Application Entry & CLI Menu"]
        A["main.py Entry Point"] --> B["Initialize DatabaseManager"]
        B --> C{"Check Migration Flag\n(db_metadata)"}
        C -- "Not Executed" --> D["Run One-Time Migration\n(clean_existing_data)"]
        D --> E["Insert Flag 'html_cleaned_v1'"]
        C -- "Already Executed" --> F["Skip Per-Run Scan"]
        E --> F
        F --> G["Display Interactive CLI Menu (1-9)"]
    end

    subgraph Ingestion ["2. Data Ingestion (Apify Scraper)"]
        G -- "Choice 1 or 2" --> H["ApifyIngestionPipeline"]
        H --> I["ApifyExtractor (harshmaur/reddit-scraper)"]
        I --> J["Enforce IPv4 Socket Override\n(allowed_gai_family)"]
        J --> K["Execute Apify Actor Run\n(startUrls / subredditUrls)"]
        K --> L["Fetch Raw Dataset Items (JSON)"]
    end

    subgraph Ingestion_Process ["3. Data Cleaning & SQLite Ingestion"]
        L --> M["Normalize Post & Comment Records"]
        M --> N["Strip HTML Entities & Submission Boilerplate"]
        N --> O["Insert into SQLite (posts, comments)"]
        O --> P["Enforce Primary Keys & IGNORE Duplicates"]
    end

    subgraph QA_Engine ["4. Tiered Q&A Generation"]
        G -- "Choice 3" --> Q["QAGenerator / QADetector"]
        Q --> R["Identify Question Comments (?)"]
        R --> S{"Find Candidate Answer"}
        S -- "Direct Reply (parent_id == question_id)" --> T["Tier 1: direct_reply\n(verified, 0.95 confidence)"]
        S -- "Thread Sibling (same parent)" --> U["Tier 2: thread_sibling\n(unverified, 0.70 confidence)"]
        S -- "Top-Scoring Comment in Post" --> V["Tier 3: fallback_top_score\n(unverified, 0.40 confidence)"]
        T --> W["Save QAPair into SQLite (qa_pairs)"]
        U --> W
        V --> W
    end

    subgraph NLP_Engine ["5. NLP Enrichment Layer"]
        G -- "Choice 4" --> X["NLPEnricher"]
        X --> Y["Calculate VADER Polarity Scores\n(compound score)"]
        Y --> Z["Assign Sentiment Label\n(positive / neutral / negative)"]
        X --> AA["Extract Keyphrases & Capitalized Entities"]
        Z --> AB["Update posts & comments in SQLite"]
        AA --> AB
    end

    subgraph Export ["6. Reporting & Export"]
        G -- "Choice 5" --> AC["View Stored Data Summary"]
        G -- "Choice 6" --> AD["Export to Excel (openpyxl)"]
        AD --> AE["Worksheet 1: Reddit Posts"]
        AD --> AF["Worksheet 2: Reddit Comments"]
        AD --> AG["Worksheet 3: Q&A Pairs"]
        AE --> AH["reddit_data_export.xlsx"]
        AF --> AH
        AG --> AH
    end
```

---

## Detailed Data Lifecycle & Processing Stages

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as main.py (CLI)
    participant DB as DatabaseManager (SQLite)
    participant Extractor as ApifyExtractor
    participant QA as QADetector
    participant NLP as NLPEnricher
    participant Excel as ExcelExporter

    User->>CLI: Launch Application (python -m src.main)
    CLI->>DB: Instantiate DatabaseManager()
    DB->>DB: Query db_metadata for 'html_cleaned_v1'
    alt Migration Not Found
        DB->>DB: Run clean_existing_data() full scan
        DB->>DB: Set 'html_cleaned_v1' = 'true'
    else Migration Found
        DB->>DB: Skip table scan (Instant Startup)
    end
    DB-->>CLI: Schema & Migration Ready

    User->>CLI: Select Choice 1/2 (Apify Ingestion)
    CLI->>Extractor: fetch_subreddit_data(subreddit, limit)
    Extractor->>Extractor: Force IPv4 Socket (socket.AF_INET)
    Extractor->>Apify API: POST /v2/acts/harshmaur~reddit-scraper/runs
    Apify API-->>Extractor: Run ID & Dataset ID
    Extractor->>DB: Insert normalized Posts & Comments (INSERT OR IGNORE)
    DB-->>CLI: Ingestion Summary

    User->>CLI: Select Choice 3 (Generate Q&A Pairs)
    CLI->>QA: run_for_all_posts()
    QA->>DB: Fetch comments for post
    QA->>QA: Filter question comments & match answers (Direct -> Sibling -> Fallback)
    QA->>DB: Insert QAPair with match_type, verification_status & confidence_score
    DB-->>CLI: Q&A Generation Summary

    User->>CLI: Select Choice 4 (Run NLP Enrichment)
    CLI->>NLP: enrich_database()
    NLP->>DB: Fetch posts & comments
    NLP->>NLP: Compute VADER sentiment + Extract keywords & proper noun entities
    NLP->>DB: Update sentiment_score, sentiment_label, keywords
    DB-->>CLI: NLP Enrichment Summary

    User->>CLI: Select Choice 6 (Export to Excel)
    CLI->>Excel: export_to_excel("reddit_data_export.xlsx")
    Excel->>DB: Fetch posts, comments & qa_pairs
    Excel->>Excel: Format sheets (Reddit Posts, Comments, Q&A Pairs) with engagement & NLP metrics
    Excel-->>User: Saved reddit_data_export.xlsx
```

---

## Detailed Step-by-Step Pipeline Description

### Phase 1: Application Entry & Migration Check
1. **Entry Point**: The user starts `python -m src.main`.
2. **`DatabaseManager` Setup**: Initializes the SQLite database file (`data/reddit_news.db`).
3. **Migration Check**: Queries table `db_metadata` for key `'html_cleaned_v1'`:
   - If missing: Executes `clean_existing_data()` once, unescaping HTML entities and stripping Reddit RSS taglines across pre-existing data, then sets key `'html_cleaned_v1' = 'true'`.
   - If present: Skips the table scan instantly, ensuring zero performance overhead on application startup.

---

### Phase 2: Ingestion & Raw Data Extraction
1. **Actor Configuration**: Connects to Apify using `APIFY_API_TOKEN` and `APIFY_ACTOR_ID` (default: `harshmaur/reddit-scraper`).
2. **Windows Network Resilience**: Applies an automatic socket patch (`urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET`) to force IPv4 DNS resolution, eliminating Windows IPv6 `getaddrinfo` timeouts (`Errno 11002`).
3. **Payload Dispatch**: Submits run configurations (`startUrls`, `maxPostsCount`, `crawlCommentsPerPost: True`, `maxCommentsPerPost`).
4. **Dataset Retrieval**: Fetches JSON items output by the actor.

---

### Phase 3: Text Cleaning & Normalization
1. **Field Mapping**: Maps raw JSON fields (`id`, `parsedId`, `title`, `body`, `authorName`, `upVotes`, `commentsCount`, `postUrl`, `createdAt`) into structured dataclasses (`RedditPost`, `RedditComment`).
2. **Text Normalization**:
   - Decodes HTML entities (e.g. `&#39;` → `'`, `&quot;` → `"`).
   - Strips Reddit RSS submission taglines (e.g. `submitted by /u/user [link] [comments]`).

---

### Phase 4: SQLite Database Ingestion & Deduplication
1. **Post Ingestion**: Executes `INSERT OR IGNORE INTO posts` using `post_id` as Primary Key.
2. **Comment Ingestion**: Executes `INSERT OR IGNORE INTO comments` using `comment_id` as Primary Key. Preserves relational foreign key `post_id`, parent link `parent_id` (`t1_` for comments, `t3_` for posts), engagement `score` (net upvotes), and thread `depth`.

---

### Phase 5: Tiered Q&A Generation & Reliability Tagging
1. **Question Isolation**: Identifies all comments containing question marks (`?`).
2. **3-Tier Answer Matching**:
   - **Tier 1 (`direct_reply`)**: Candidate comment `parent_id` matches the question comment `comment_id`. Assigned `verification_status: verified_direct_reply` and `confidence_score: 0.95`.
   - **Tier 2 (`thread_sibling`)**: Candidate comment shares the same `parent_id` within the discussion branch. Assigned `verification_status: unverified_thread_sibling` and `confidence_score: 0.70`.
   - **Tier 3 (`fallback_top_score`)**: Highest-scoring non-question comment available in the post. Assigned `verification_status: unverified_fallback` and `confidence_score: 0.40`.
3. **Deduplication & Sub-question Filter**: Ensures used answers are never assigned to multiple questions, and prevents questions from answering other questions.
4. **Storage**: Saves pairings into `qa_pairs` with composite primary key `(question_comment_id, answer_comment_id)`.

---

### Phase 6: Natural Language Processing (NLP Enrichment)
1. **VADER Sentiment Analysis**: Computes compound polarity score `[-1.0 to +1.0]` using `vaderSentiment` (with fallback lexicon support):
   - `compound >= 0.05`: `"positive"`
   - `compound <= -0.05`: `"negative"`
   - Otherwise: `"neutral"`
2. **Keyword & Proper Noun Entity Extraction**:
   - Cleans stopwords and computes word frequency rankings.
   - Extracts capitalized proper noun entities (e.g., product names, places, organizations).
3. **Database Update**: Stores `sentiment_score`, `sentiment_label`, and `keywords` into `posts` and `comments` tables.

---

### Phase 7: Reporting & Professional Excel Export
1. **Console Data Inspector (Option 5)**: Displays total counts, sample posts/comments with scores and sentiment labels, and sample Q&A pairs with match tiers and confidence ratings.
2. **Formatted Excel Export (Option 6)**: Builds `reddit_data_export.xlsx` using `openpyxl` containing 3 formatted tabs:
   - **Reddit Posts**: `post_id`, `subreddit`, `title`, `body`, `author`, `score`, `num_comments`, `sentiment_label`, `sentiment_score`, `keywords`, `url`, `created_utc`.
   - **Reddit Comments**: `comment_id`, `post_id`, `parent_id`, `author`, `body`, `score`, `depth`, `sentiment_label`, `sentiment_score`, `keywords`, `created_utc`.
   - **Q&A Pairs**: `question_comment_id`, `answer_comment_id`, `post_id`, `question`, `answer`, `score_signal`, `match_type`, `verification_status`, `confidence_score`.

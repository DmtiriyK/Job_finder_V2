# Intelligent German Remote Job Finder - Implementation Plan

## 📋 Executive Summary

**Цель**: Автоматическая система поиска remote/hybrid вакансий в Германии для Full Stack Platform Engineer позиций с ML-based matching и intelligent scoring.

**Ключевые возможности**:
- 🔍 Парсинг 9 источников вакансий (RemoteOK, WeWorkRemotely, StepStone, XING, GitHub Jobs, StackOverflow, Adzuna, Indeed, HackerNews)
- 🧠 Умный scoring на основе твоих критериев (remote priority, tech stack, contract type, urgency keywords)
- 🤖 TF-IDF similarity matching с твоим профилем
- 📊 Автоматическая запись топ 10-20 вакансий в Google Sheets
- ⚡ GitHub Actions (1x/день в 09:00 Berlin time)
- 🎯 90-95% точность отбора релевантных вакансий

**Технологический стек**:
- **Язык**: Python 3.11+
- **Scraping**: BeautifulSoup4 + Playwright (гибридный подход)
- **NLP**: FlashText (keyword extraction) + scikit-learn (TF-IDF) + optional spaCy (advanced mode)
- **Storage**: Google Sheets (gspread)
- **Deployment**: GitHub Actions (daily cron job)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Cron)                     │
│                   Runs daily at 09:00 CET                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│                    (Orchestrator)                            │
└──┬────────────┬────────────┬────────────┬──────────────┬───┘
   │            │            │            │              │
   ▼            ▼            ▼            ▼              ▼
┌──────┐   ┌────────┐   ┌─────────┐  ┌────────┐   ┌─────────┐
│ 9    │   │ Tech   │   │ Scoring │  │ TF-IDF │   │ Google  │
│Scrap-│──▶│Extract-│──▶│ Engine  │──│ Match  │──▶│ Sheets  │
│ ers  │   │ or     │   │ (5 comp)│  │        │   │         │
└──────┘   └────────┘   └─────────┘  └────────┘   └─────────┘
    │           │             │            │
    │           │             │            │
    ▼           ▼             ▼            ▼
┌─────────────────────────────────────────────────┐
│         Cache Layer (joblib + diskcache)        │
│  - Vectorizer models                            │
│  - Scraped jobs (24h TTL)                       │
│  - Tech extraction results                      │
└─────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
job_finder/
├── config/
│   ├── scoring_rules.yaml       # Scoring criteria & weights
│   ├── tech_dictionary.json     # 500+ tech terms for FlashText
│   ├── profile.yaml             # Your YAML profile (skills, preferences)
│   └── settings.py              # Python config loader
│
├── scrapers/
│   ├── __init__.py
│   ├── base.py                  # BaseScraper (abstract class)
│   ├── remoteok.py              # RemoteOK RSS feed
│   ├── weworkremotely.py        # WeWorkRemotely HTML
│   ├── stepstone.py             # StepStone (HTML + Playwright if needed)
│   ├── xing.py                  # XING jobs (HTML)
│   ├── github_jobs.py           # GitHub Jobs (API/HTML)
│   ├── stackoverflow.py         # Stack Overflow Jobs (RSS + HTML)
│   ├── adzuna.py                # Adzuna API (250 calls/month limit)
│   ├── indeed.py                # Indeed API
│   └── hackernews.py            # HackerNews "Who's Hiring" (Algolia API)
│
├── extractors/
│   ├── __init__.py
│   ├── tech_extractor.py        # FlashText + regex for tech keywords
│   └── ner_extractor.py         # Optional spaCy NER (full mode only)
│
├── matchers/
│   ├── __init__.py
│   └── tfidf_matcher.py         # TF-IDF similarity with your profile
│
├── scorers/
│   ├── __init__.py
│   ├── base.py                  # ScoreComponent (abstract)
│   ├── components/
│   │   ├── __init__.py
│   │   ├── tfidf_component.py      # 40% weight - CV similarity
│   │   ├── tech_stack_component.py # 30% weight - Tech match scoring
│   │   ├── remote_component.py     # 15% weight - Remote type scoring
│   │   ├── keyword_component.py    # 10% weight - Urgency & keywords
│   │   └── contract_component.py   # 5% weight - Contract type scoring
│   └── aggregator.py            # Aggregates all components → final score
│
├── processors/
│   ├── __init__.py
│   ├── deduplicator.py          # Remove duplicates (title+company similarity)
│   └── filter.py                # Pre-filter (location, tech roles, date)
│
├── integrations/
│   ├── __init__.py
│   └── google_sheets.py         # Google Sheets API via gspread
│
├── models/
│   ├── __init__.py
│   ├── job.py                   # Pydantic Job model
│   └── profile.py               # Pydantic Profile model (from YAML)
│
├── cache/
│   ├── __init__.py
│   └── manager.py               # Cache manager (joblib + diskcache)
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Structured logging
│   └── rate_limiter.py          # Rate limiting for scrapers
│
├── tests/
│   ├── test_scrapers.py
│   ├── test_extractors.py
│   ├── test_scorers.py
│   └── test_integration.py
│
├── .github/
│   └── workflows/
│       └── daily_scraper.yml    # GitHub Actions workflow
│
├── main.py                      # Main orchestration script
├── requirements-light.txt       # Dependencies for GitHub Actions
├── requirements-full.txt        # Dependencies with spaCy (local dev)
├── .env.example                 # Environment variables template
├── .gitignore
├── README.md
└── IMPLEMENTATION_PLAN.md       # This file
```

---

## 🎯 Scoring System Architecture

### Scoring Components & Weights

Total score = 100 points (weighted sum of normalized components)

| Component | Max Points | Raw Score Range | Normalization |
|-----------|------------|-----------------|---------------|
| **TF-IDF Similarity** | 40 | 0.0-1.0 | `score * 40` |
| **Tech Stack Match** | 30 | -∞ to +∞ | `min(sum, 30)` (cap) |
| **Remote Type** | 15 | -3 to +5 | `((raw+3)/8)*15` |
| **Keywords** | 10 | -∞ to +∞ | `max(0, min(sum, 10))` |
| **Contract Type** | 5 | -5 to +2 | `((raw+5)/7)*5` |

**Normalization Formula**:
```python
final_score = sum(component.normalized_score for all components)
# Result: 0-100 points
```

**Example Calculation**:
```
TF-IDF: 0.75 similarity → 30 points (0.75 * 40)
Tech: React(+5) + Docker(+4) + .NET(+5) = 14 points
Remote: Full remote (+5 raw) → 15 points (((5+3)/8)*15)
Keywords: sofort(+2) → 2 points
Contract: Freiberuflich (+2 raw) → 5 points (((2+5)/7)*5)
---
Total: 30 + 14 + 15 + 2 + 5 = 66 points
```

### Detailed Scoring Rules

#### 1. Tech Stack Component (30 points max)

Based on `config/scoring_rules.yaml`:

**High Priority (+3 to +5 points each)**:
- C# → +5
- .NET, .NET Core → +5
- React → +5
- TypeScript → +4
- Docker → +4
- Microservices → +4
- REST API, API Integration → +4
- AWS → +3
- Azure → +3
- PostgreSQL, MySQL → +3
- CI/CD → +3

**Medium Priority (+1 to +2 points each)**:
- Node.js → +2
- Kubernetes → +2
- Next.js → +2
- Event-driven → +2
- GraphQL → +1
- NoSQL → +1
- Redis → +1
- RabbitMQ → +1
- Clean Architecture, DDD, SOLID → +1

**Negative (-3 points each)**:
- SAP → -3
- ABAP → -3
- JSF → -3
- COBOL → -3

#### 2. Remote Component (15 points max)

Detection patterns + scoring:

| Remote Type | Score | Patterns |
|-------------|-------|----------|
| 100% Remote | +5 | `100% remote`, `fully remote`, `remote innerhalb Deutschland` |
| Hybrid 1 day/week | +3 | `1 Tag/Woche`, `hybrid 1 day` |
| Hybrid 2 days/week | 0 | `2 Tage/Woche` (neutral) |
| Onsite required | -3 | `vor Ort`, `Standortpflicht`, `onsite only`, `zwingend vor Ort` |

#### 3. Keyword Component (10 points max)

**Urgency Keywords (+2 each)**:
- sofort
- asap
- kurzfristig
- Projektstart
- dringend

**Positive Keywords (+1 each)**:
- wachsendes Team
- remote-first
- flexible Arbeitszeiten

**Negative Keywords (-2 to -5)**:
- "vor Ort" → -2
- "Onsite only" → -5
- "3-5 Tage vor Ort" → -3

#### 4. Contract Component (5 points max)

| Contract Type | Score |
|---------------|-------|
| Freiberuflich | +2 |
| Contract, Projektvertrag | +2 |
| Unbefristet | +1 |
| Festanstellung | +1 |
| Befristet | 0 |
| Praktikum | -5 |

#### 5. TF-IDF Component (40 points max)

- Cosine similarity between job description and your `profile.yaml` text
- Normalized to 0-40 points scale
- Uses scikit-learn `TfidfVectorizer` with:
  - `max_features=5000`
  - `ngram_range=(1, 2)` for bigrams ("machine learning")
  - Lowercase normalization

---

## 📊 Data Models (Pydantic)

### Job Model

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Optional

class Job(BaseModel):
    id: str                          # Unique ID (hash of URL + title)
    title: str
    company: str
    location: str
    remote_type: str                 # "Full Remote", "Hybrid", "Onsite"
    contract_type: Optional[str]     # "Freiberuflich", "Festanstellung", etc.
    url: HttpUrl
    description: str
    posted_date: datetime
    source: str                      # "RemoteOK", "StepStone", etc.
    tech_stack: List[str] = []       # Extracted tech keywords
    score: Optional[float] = None    # Final score (0-100)
    score_breakdown: Optional[dict] = None  # Per-component scores
```

### Profile Model

```python
class Skill(BaseModel):
    name: str
    experience_years: Optional[int]
    proficiency: Optional[str]  # "Expert", "Advanced", "Intermediate"

class Profile(BaseModel):
    name: str
    roles: List[str]
    skills: dict  # {languages: [], frameworks: [], tools: [], concepts: []}
    preferences: dict
    profile_text: str  # For TF-IDF matching
```

---

## 🔧 Implementation Details

### Phase 1: Core Infrastructure (Days 1-2)

#### 1.1 Project Setup
- [x] Create project structure
- [ ] Initialize git repository
- [ ] Setup virtual environment
- [ ] Create `requirements-light.txt` and `requirements-full.txt`
- [ ] Create `.env.example`

#### 1.2 Configuration System
- [ ] Implement `config/settings.py` (loads YAML configs)
- [ ] Create `config/scoring_rules.yaml` (detailed scoring rules)
- [ ] Create `config/tech_dictionary.json` (500+ tech terms)
- [ ] Create `config/profile.yaml.example` (template for user profile)

#### 1.3 Data Models
- [ ] Implement `models/job.py` (Pydantic Job model)
- [ ] Implement `models/profile.py` (Pydantic Profile model)
- [ ] Add validation and serialization methods

#### 1.4 Utilities
- [ ] Implement `utils/logger.py` (structured logging with JSON support)
- [ ] Implement `utils/rate_limiter.py` (async rate limiting for scrapers)
- [ ] Implement `cache/manager.py` (joblib + diskcache wrapper)

### Phase 2: Scrapers Implementation (Days 3-5)

#### 2.1 Base Scraper
- [ ] Implement `scrapers/base.py`:
  - `BaseScraper` abstract class
  - Methods: `async def fetch_jobs()`, `normalize_job()`, `handle_errors()`
  - Rate limiting integration (async-compatible)
  - User-Agent rotation
  - Retry logic (exponential backoff)
  - Use `httpx.AsyncClient` for async HTTP requests (or `requests` with `asyncio.to_thread()` for sync scrapers)

#### 2.2 Individual Scrapers

**Priority 1 (Simple, fast, reliable)**:
- [ ] `scrapers/remoteok.py` - RSS feed parsing (feedparser)
- [ ] `scrapers/weworkremotely.py` - HTML scraping (BS4)
- [ ] `scrapers/hackernews.py` - Algolia API for "Who's Hiring"

**Priority 2 (API-based)**:
- [ ] `scrapers/adzuna.py` - Free API (250 calls/month limit handling)
- [ ] `scrapers/indeed.py` - Free API
- [ ] `scrapers/stackoverflow.py` - RSS feed + HTML fallback

**Priority 3 (Complex, may require JS rendering)**:
- [ ] `scrapers/stepstone.py` - HTML + optional Playwright
- [ ] `scrapers/xing.py` - HTML + optional Playwright
- [ ] `scrapers/github_jobs.py` - API/HTML hybrid

**Scraper Requirements**:
- Return unified `List[Job]` models
- Handle pagination
- Respect rate limits (1-3 seconds between requests)
- Log statistics (jobs found, errors, duration)
- Support keywords: ["Full Stack", "Platform Engineer", "Backend", ".NET", "React"]
- Support location: ["Germany", "Deutschland", "Remote"]

### Phase 3: NLP & Extraction (Days 6-7)

#### 3.1 Tech Stack Extractor
- [ ] Implement `extractors/tech_extractor.py`:
  - Load `tech_dictionary.json` (C#, .NET, React, Docker, Kubernetes, etc.)
  - FlashText `KeywordProcessor` for O(n) extraction
  - Custom regex for edge cases: `C#`, `.NET`, `C++`
  - Case-insensitive normalization
  - Return: `Set[str]` of extracted tech terms

**Tech Dictionary Structure** (`tech_dictionary.json`):
```json
{
  "languages": ["C#", "Python", "TypeScript", "JavaScript", "Go", "Java", "C++"],
  "frameworks": [".NET", ".NET Core", "ASP.NET", "React", "Next.js", "Node.js"],
  "tools": ["Docker", "Kubernetes", "Git", "Jenkins", "GitLab CI"],
  "cloud": ["AWS", "Azure", "GCP"],
  "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis"],
  "concepts": ["Microservices", "REST API", "GraphQL", "CI/CD", "Event-driven"]
}
```

#### 3.2 NER Extractor (Optional, Full Mode)
- [ ] Implement `extractors/ner_extractor.py`:
  - Load spaCy `de_core_news_sm`
  - Custom EntityRuler for tech patterns
  - Context-aware extraction ("5 years Python" vs casual mention)
  - Only enabled when `USE_ADVANCED_NLP=true`

#### 3.3 TF-IDF Matcher
- [ ] Implement `matchers/tfidf_matcher.py`:
  - Initialize scikit-learn `TfidfVectorizer`:
    ```python
    TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        lowercase=True,
        token_pattern=r'(?u)\b\w+\b'
    )
    ```
  - Load `profile_text` from `profile.yaml`
  - Method: `calculate_similarity(job_description: str) -> float`
  - Return: cosine similarity score (0-1)
  - Cache fitted vectorizer with joblib

### Phase 4: Scoring Engine (Days 8-10)

#### 4.1 Base Components
- [ ] Implement `scorers/base.py`:
  ```python
  class ScoreComponent(ABC):
      @abstractmethod
      def calculate(self, job: Job, profile: Profile) -> ScoreResult:
          pass
  
  @dataclass
  class ScoreResult:
      score: float
      max_score: float
      explanation: str
      details: dict
  ```

#### 4.2 Individual Scoring Components

**Important**: Each component must normalize its score to 0-max_score range.

- [ ] `scorers/components/tfidf_component.py`:
  - Calculate TF-IDF similarity via `TfidfMatcher` (returns 0-1)
  - Normalize to 0-40 points: `score = similarity * 40`
  - Explanation: "CV similarity: 0.85 → 34/40 points"

- [ ] `scorers/components/tech_stack_component.py`:
  - Extract tech from job via `TechExtractor`
  - Match against `scoring_rules.yaml` tech terms
  - Calculate sum of matched tech scores
  - **Cap at 30 points max** (if sum exceeds 30, return 30)
  - Explanation: "Matched: React (+5), Docker (+4), SAP (-3) = 6/30 points"

- [ ] `scorers/components/remote_component.py`:
  - Regex patterns for remote type detection
  - Raw score: -3 to +5 based on rules
  - **Normalize to 0-15**: `normalized = ((raw + 3) / 8) * 15`
    - Raw -3 (onsite) → 0 points
    - Raw +5 (full remote) → 15 points
  - Explanation: "100% Remote detected (+5 raw) → 15/15 points"

- [ ] `scorers/components/keyword_component.py`:
  - Match urgency keywords (sofort, asap)
  - Match positive/negative keywords
  - Sum scores, **cap at 10 points** (can go negative, floor at 0)
  - Explanation: "Found: 'sofort' (+2), 'vor Ort' (-2) = 0/10 points"

- [ ] `scorers/components/contract_component.py`:
  - Extract contract type via regex
  - Raw score: -5 to +2 based on rules
  - **Normalize to 0-5**: `normalized = ((raw + 5) / 7) * 5`
    - Raw -5 (Praktikum) → 0 points
    - Raw +2 (Freiberuflich) → 5 points
  - Explanation: "Contract type: Freiberuflich (+2 raw) → 5/5 points"

#### 4.3 Score Aggregator
- [ ] Implement `scorers/aggregator.py`:
  - Load all 5 components
  - Execute each: `component.calculate(job, profile)`
  - **Verify normalization**: Each component returns score in 0-max_score range
  - Final score: `sum(component.normalized_score)` (should be 0-100)
  - Return `ScoreResult` with:
    - `score: float` (0-100)
    - `breakdown: dict` (per-component scores with raw + normalized)
    - `explanation: str` (human-readable summary)

**Example ScoreResult**:
```python
ScoreResult(
    score=66.0,
    breakdown={
        "tfidf": {"raw": 0.75, "normalized": 30.0, "max": 40},
        "tech_stack": {"raw": 14, "normalized": 14.0, "max": 30},
        "remote": {"raw": 5, "normalized": 15.0, "max": 15},
        "keywords": {"raw": 2, "normalized": 2.0, "max": 10},
        "contract": {"raw": 2, "normalized": 5.0, "max": 5}
    },
    explanation="Score: 66/100. High match: Full remote (15/15), CV similarity (30/40). Tech: React, Docker, .NET (14/30)."
)

### Phase 5: Processing Pipeline (Days 11-12)

#### 5.1 Pre-filtering
- [ ] Implement `processors/filter.py`:
  - Location filter: Germany, Deutschland, Remote
  - Role title filter: match against primary/secondary keywords
  - Date filter: posted within last 7 days
  - Remove jobs with < 50 characters description

#### 5.2 Deduplication
- [ ] Implement `processors/deduplicator.py`:
  - Calculate title + company similarity (fuzzy matching)
  - Threshold: 85% similarity → duplicate
  - Keep job with higher score
  - Algorithm: TF-IDF cosine similarity or Levenshtein distance

### Phase 6: Google Sheets Integration (Day 13)

- [ ] Implement `integrations/google_sheets.py`:
  - Setup Google Service Account authentication
  - Use `gspread` library
  - Methods:
    - `create_or_get_sheet()` - Get or create spreadsheet
    - `write_jobs(jobs: List[Job])` - Write jobs to sheet
    - `apply_formatting()` - Color coding based on score
  
**Sheet Structure**:
```
| Date Found | Title | Company | Location | Remote | Contract | Tech Stack | Score | Breakdown | URL | Source | Applied? | Notes |
```

**Color Coding**:
- Score > 80: Green background
- Score 60-80: Yellow background
- Score < 60: White background

**Conditional Formatting**:
- Applied? column: Checkbox
- Sort by: Score DESC, then Date DESC

### Phase 7: Main Orchestration (Day 14)

- [ ] Implement `main.py`:
  1. Load configs (`scoring_rules.yaml`, `profile.yaml`, `settings.py`)
  2. Initialize all 9 scrapers
  3. Run scrapers in parallel (`asyncio.gather()`)
  4. Collect results → unified `List[Job]`
  5. Pre-filter jobs (location, roles, date)
  6. Extract tech stack for each job
  7. Deduplicate jobs
  8. Score each job via `ScoreAggregator`
  9. Sort by score DESC
  10. Select top 10-20 jobs
  11. Write to Google Sheets
  12. Log statistics

**Logging Output**:
```
[INFO] Starting job scraper at 2026-02-16 09:00:00
[INFO] Initializing 9 scrapers...
[INFO] Scraping completed: 487 jobs found
[INFO] Pre-filtering: 487 → 234 jobs (Germany, tech roles, last 7 days)
[INFO] Tech extraction: 234 jobs processed
[INFO] Deduplication: 234 → 189 jobs
[INFO] Scoring: 189 jobs scored
[INFO] Top 20 jobs selected (score range: 72-94)
[INFO] Writing to Google Sheets...
[INFO] Success! 20 jobs written to sheet "Job Finder - 2026-02-16"
```

### Phase 8: GitHub Actions Setup (Day 15)

- [ ] Create `.github/workflows/daily_scraper.yml`:
  ```yaml
  name: Daily Job Scraper
  on:
    schedule:
      - cron: '0 8 * * *'  # 09:00 CET (winter) / 10:00 CEST (summer)
    workflow_dispatch:      # Allow manual trigger
  
  jobs:
    scrape:
      runs-on: ubuntu-latest
      timeout-minutes: 15
      
      steps:
        - uses: actions/checkout@v4
        
        - name: Setup Python
          uses: actions/setup-python@v5
          with:
            python-version: '3.11'
            cache: 'pip'
        
        - name: Cache NLP models
          uses: actions/cache@v4
          with:
            path: |
              ~/.cache/pip
              ~/.cache/sklearn
            key: ${{ runner.os }}-nlp-${{ hashFiles('requirements-light.txt') }}
        
        - name: Install dependencies
          run: |
            pip install -r requirements-light.txt
            playwright install chromium --with-deps
        
        - name: Run scraper
          env:
            GOOGLE_SHEETS_CREDENTIALS: ${{ secrets.GOOGLE_SHEETS_CREDENTIALS }}
            USE_ADVANCED_NLP: false  # Lightweight mode
          run: python main.py
        
        - name: Upload logs
          if: always()
          uses: actions/upload-artifact@v4
          with:
            name: scraper-logs-${{ github.run_number }}
            path: logs/
            retention-days: 7
  ```

- [ ] Setup GitHub Secrets:
  - `GOOGLE_SHEETS_CREDENTIALS`: JSON service account key

### Phase 9: Testing (Days 16-17)

#### 9.1 Unit Tests
- [ ] `tests/test_scrapers.py`:
  - Test each scraper with mocked responses
  - Verify Job model validation
  - Test error handling and retry logic

- [ ] `tests/test_extractors.py`:
  - Test tech extraction with sample job descriptions
  - Verify regex patterns (C#, .NET, C++)
  - Test edge cases

- [ ] `tests/test_scorers.py`:
  - Test each scoring component independently
  - **Test normalization**: Verify raw scores → normalized scores correctly
  - Test edge cases:
    - Remote: raw -3 → 0 points, raw +5 → 15 points
    - Tech: sum > 30 → capped at 30
    - Keywords: negative sum → floored at 0
    - Contract: raw -5 → 0 points, raw +2 → 5 points
  - Test aggregator weighted sum (should always be 0-100)
  - Verify score breakdowns are accurate

#### 9.2 Integration Tests
- [ ] `tests/test_integration.py`:
  - End-to-end test with mock scrapers
  - Verify full pipeline: scrape → extract → score → write
  - Test Google Sheets integration (use test sheet)

#### 9.3 Manual Testing
- [ ] Local run: `python main.py`
- [ ] Verify Google Sheets output
- [ ] Review top 20 jobs manually (should be relevant)
- [ ] Check score explanations (should be clear)

### Phase 10: Documentation & Deployment (Day 18)

#### 10.1 Documentation
- [ ] Update `README.md`:
  - Project overview
  - Setup instructions (Google Sheets API, Service Account)
  - Local development guide
  - How to customize `scoring_rules.yaml` and `profile.yaml`
  - Troubleshooting section

- [ ] Create setup guides:
  - `docs/GOOGLE_SHEETS_SETUP.md` - Step-by-step Google API setup
  - `docs/CUSTOMIZATION.md` - How to adjust scoring rules
  - `docs/ADDING_SCRAPERS.md` - How to add new job sources

#### 10.2 Configuration Templates
- [ ] Create `config/profile.yaml.example`
- [ ] Create `.env.example`
- [ ] Add inline comments to `scoring_rules.yaml`

#### 10.3 Deployment
- [ ] Push to GitHub
- [ ] Add secrets to GitHub repository
- [ ] Trigger manual workflow run
- [ ] Verify first successful run
- [ ] Monitor daily runs for 3 days

---

## 📦 Dependencies

### requirements-light.txt (GitHub Actions)
```txt
# Core dependencies
beautifulsoup4==4.12.3
lxml==5.1.0
requests==2.31.0
httpx==0.26.0  # Async HTTP client for parallel scraping
playwright==1.41.0

# NLP & Text Processing (lightweight)
flashtext==2.7
scikit-learn==1.4.0

# Data Processing
pandas==2.2.0
numpy==1.26.3
pydantic==2.6.0

# Utilities
joblib==1.3.2
pyyaml==6.0.1
python-dotenv==1.0.0
diskcache==5.6.3

# Google Sheets
gspread==6.0.0
google-auth==2.27.0

# Scraping helpers
feedparser==6.0.10
```

### requirements-full.txt (Local Development)
```txt
-r requirements-light.txt

# Advanced NLP (optional)
spacy==3.7.2
de-core-news-sm @ https://github.com/explosion/spacy-models/releases/download/de_core_news_sm-3.7.0/de_core_news_sm-3.7.0-py3-none-any.whl

# Development tools
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0
black==24.1.0
flake8==7.0.0
mypy==1.8.0
```

---

## ⚙️ Configuration Files

### config/scoring_rules.yaml

```yaml
# Scoring configuration - Max points per component
# Total = 100 points (sum of all max_points)
scoring:
  max_points:
    tfidf_similarity: 40
    tech_stack: 30
    remote_type: 15
    keywords: 10
    contract_type: 5

# Tech stack scoring rules
tech_stack:
  high_priority:
    - {term: "C#", score: 5}
    - {term: ".NET", score: 5}
    - {term: ".NET Core", score: 5}
    - {term: "ASP.NET", score: 5}
    - {term: "React", score: 5}
    - {term: "TypeScript", score: 4}
    - {term: "Docker", score: 4}
    - {term: "Microservices", score: 4}
    - {term: "REST API", score: 4}
    - {term: "API Integration", score: 4}
    - {term: "OAuth", score: 3}
    - {term: "AWS", score: 3}
    - {term: "Azure", score: 3}
    - {term: "CI/CD", score: 3}
    - {term: "PostgreSQL", score: 3}
    - {term: "MySQL", score: 3}
    - {term: "Git", score: 2}
  
  medium_priority:
    - {term: "Node.js", score: 2}
    - {term: "Next.js", score: 2}
    - {term: "Kubernetes", score: 2}
    - {term: "Event-driven", score: 2}
    - {term: "NoSQL", score: 1}
    - {term: "GraphQL", score: 1}
    - {term: "Redis", score: 1}
    - {term: "RabbitMQ", score: 1}
    - {term: "Clean Architecture", score: 1}
    - {term: "DDD", score: 1}
    - {term: "SOLID", score: 1}
    - {term: "Testing", score: 1}
    - {term: "xUnit", score: 1}
    - {term: "Jest", score: 1}
  
  negative:
    - {term: "SAP", score: -3}
    - {term: "ABAP", score: -3}
    - {term: "JSF", score: -3}
    - {term: "COBOL", score: -3}

# Remote type scoring
remote:
  patterns:
    full_remote:
      score: 5
      patterns:
        - "100% remote"
        - "fully remote"
        - "remote innerhalb Deutschland"
        - "remote innerhalb Deutschlands"
        - "vollständig remote"
        - "komplett remote"
    
    hybrid_1day:
      score: 3
      patterns:
        - "1 Tag.*Woche"
        - "1 day.*week"
        - "hybrid.*1.*Tag"
        - "ein Tag.*Büro"
    
    hybrid_2days:
      score: 0
      patterns:
        - "2 Tage.*Woche"
        - "2 days.*week"
    
    onsite_required:
      score: -3
      patterns:
        - "vor Ort"
        - "Standortpflicht"
        - "onsite only"
        - "zwingend vor Ort"
        - "3-5 Tage.*vor Ort"

# Keywords scoring
keywords:
  urgency:
    - {term: "sofort", score: 2}
    - {term: "asap", score: 2}
    - {term: "kurzfristig", score: 2}
    - {term: "Projektstart", score: 2}
    - {term: "dringend", score: 1}
  
  positive:
    - {term: "wachsendes Team", score: 1}
    - {term: "remote-first", score: 2}
    - {term: "flexible Arbeitszeiten", score: 1}
    - {term: "moderne Technologien", score: 1}
  
  negative:
    - {term: "vor Ort", score: -2}
    - {term: "Onsite only", score: -5}
    - {term: "3-5 Tage vor Ort", score: -3}

# Contract type scoring
contract:
  types:
    - {name: "Freiberuflich", score: 2}
    - {name: "Contract", score: 2}
    - {name: "Projektvertrag", score: 2}
    - {name: "Interim", score: 2}
    - {name: "Unbefristet", score: 1}
    - {name: "Festanstellung", score: 1}
    - {name: "Befristet", score: 0}
    - {name: "Praktikum", score: -5}
    - {name: "Junior", score: -2}

# Filtering rules (pre-scoring)
filters:
  locations:
    include:
      - "Germany"
      - "Deutschland"
      - "Remote"
      - "Berlin"
      - "München"
      - "Hamburg"
      - "Frankfurt"
      - "Köln"
  
  min_description_length: 50
  max_job_age_days: 7
  
  role_keywords:
    primary:
      - "Fullstack Developer"
      - "Full-Stack Engineer"
      - "Software Engineer"
      - "Backend Developer"
      - "Platform Engineer"
      - "Web Developer"
    
    secondary:
      - "Cloud Engineer"
      - "Application Developer"
      - ".NET Developer"
      - "React Developer"
      - "API Developer"
      - "Systems Engineer"
```

### config/profile.yaml.example

```yaml
# Example profile - copy to profile.yaml and customize

name: "Your Name"

roles:
  - "Fullstack Developer"
  - "Full-Stack Engineer"
  - "Platform Engineer"
  - "Backend Developer"
  - "Software Engineer"

skills:
  languages:
    - {name: "C#", experience_years: 5, proficiency: "Expert"}
    - {name: "Python", experience_years: 4, proficiency: "Advanced"}
    - {name: "TypeScript", experience_years: 3, proficiency: "Advanced"}
    - {name: "JavaScript", experience_years: 4, proficiency: "Advanced"}
  
  frameworks:
    - {name: ".NET Core", experience_years: 5}
    - {name: "ASP.NET", experience_years: 4}
    - {name: "React", experience_years: 3}
    - {name: "Next.js", experience_years: 2}
  
  tools:
    - {name: "Docker", experience_years: 4}
    - {name: "AWS", experience_years: 3}
    - {name: "Azure", experience_years: 2}
    - {name: "PostgreSQL", experience_years: 4}
    - {name: "Git", experience_years: 6}
    - {name: "CI/CD", experience_years: 4}
  
  concepts:
    - "Microservices"
    - "REST API"
    - "Event-driven architecture"
    - "OAuth / Auth"
    - "API Integration"
    - "Clean Architecture"
    - "SOLID"

preferences:
  remote: "100% preferred"
  contract_types:
    - "Freiberuflich"
    - "Contract"
    - "Festanstellung"
  locations:
    - "Germany"
  
  min_score: 60  # Minimum score to show in results

# Profile text for TF-IDF matching
# This should be a natural language description of your skills and experience
profile_text: |
  Full Stack Platform Engineer with 5+ years of professional experience in building
  modern web applications and cloud-native systems. Expert in C# and .NET Core ecosystem,
  with strong proficiency in React and TypeScript for frontend development.
  
  Specialized in designing and implementing microservices architectures using Docker
  and Kubernetes. Extensive experience with REST API development, OAuth authentication,
  and API integration patterns. Proficient with cloud platforms including AWS and Azure.
  
  Strong background in database design and optimization with PostgreSQL and MySQL.
  Experienced in implementing CI/CD pipelines using GitLab CI, GitHub Actions, and Jenkins.
  
  Advocate for clean code principles, SOLID design patterns, and test-driven development.
  Familiar with event-driven architectures, message queues (RabbitMQ, Redis), and
  distributed systems patterns.
  
  Looking for challenging remote or hybrid positions in Germany where I can contribute
  to building scalable, maintainable systems using modern technologies.
```

---

## 🚀 Deployment & Usage

### Local Development

1. **Setup**:
   ```bash
   cd job_finder
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements-full.txt
   ```

2. **Configure**:
   ```bash
   cp config/profile.yaml.example config/profile.yaml
   # Edit profile.yaml with your details
   
   cp .env.example .env
   # Add Google Sheets credentials path
   ```

3. **Run**:
   ```bash
   # Full mode (with spaCy)
   export USE_ADVANCED_NLP=true
   python main.py
   
   # Lightweight mode
   export USE_ADVANCED_NLP=false
   python main.py
   ```

### GitHub Actions Deployment

1. **Setup Google Service Account**:
   - Follow `docs/GOOGLE_SHEETS_SETUP.md`
   - Download JSON credentials

2. **Add GitHub Secret**:
   - Go to repository → Settings → Secrets → Actions
   - Add secret: `GOOGLE_SHEETS_CREDENTIALS` = JSON content

3. **Trigger**:
   - Automatic: Runs daily at 09:00 CET
   - Manual: Actions tab → Daily Job Scraper → Run workflow

---

## 📈 Performance Expectations

### GitHub Actions (Lightweight Mode)

| Metric | Expected Value |
|--------|----------------|
| Cold start time | ~45 seconds |
| Scraping duration | ~2-3 minutes |
| Processing & scoring | ~30 seconds |
| Total runtime | ~4-5 minutes |
| Memory usage | ~500MB |
| Jobs processed | 200-500 |
| Top results | 10-20 |

### Local Development (Full Mode)

| Metric | Expected Value |
|--------|----------------|
| Cold start time | ~60 seconds (first run) |
| Scraping duration | ~2-3 minutes |
| Processing & scoring | ~45 seconds |
| Total runtime | ~5-6 minutes |
| Memory usage | ~800MB |
| Accuracy | 95%+ |

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Scrapes 9 job sources successfully
- ✅ Extracts 200-500 jobs per run
- ✅ Filters to 50-100 relevant jobs (Germany, tech roles, recent)
- ✅ Scores all jobs with explanations
- ✅ Selects top 10-20 jobs (score > 60)
- ✅ Writes to Google Sheets with formatting
- ✅ Runs daily without manual intervention

### Quality Requirements
- ✅ 90%+ of top 10 jobs are relevant (manual review)
- ✅ Score explanations are clear and accurate
- ✅ No duplicate jobs in results
- ✅ All links are valid and accessible
- ✅ Tech stack extraction accuracy > 85%

### Technical Requirements
- ✅ GitHub Actions runtime < 10 minutes
- ✅ No crashes or unhandled errors
- ✅ Proper error logging and notifications
- ✅ Respects rate limits (no bans from job sites)
- ✅ Code coverage > 80%

---

## 🐛 Known Limitations & Future Improvements

### Current Limitations
1. **Rate Limiting**: Some sites may block after frequent requests
2. **Job Age**: Not all sources provide accurate posting dates
3. **Remote Detection**: Regex-based, may miss edge cases
4. **Tech Extraction**: Requires dictionary updates for new technologies
5. **Language**: Optimized for German + English mix, other languages not supported
6. **Cron Schedule & Timezones**: GitHub Actions runs in UTC. Current cron `'0 8 * * *'` = 09:00 CET (winter) but 10:00 CEST (summer). For consistent 09:00 local time regardless of DST, consider using dynamic scheduling or accepting the 1-hour shift in summer.

### Future Improvements (Phase 2)
1. **Recruiter Search**:
   - Extract recruiter contacts from job descriptions
   - Search GitHub/Twitter for tech recruiters in Germany
   - Score recruiters by relevance

2. **Machine Learning**:
   - Train custom classifier on your application history
   - Use embeddings (BERT) for better semantic matching
   - Active learning: improve scoring based on your feedback

3. **Auto-Apply**:
   - Template generation for cover letters
   - Automatic form filling (with approval)
   - Track application status

4. **Advanced Features**:
   - Salary range extraction
   - Company research (size, funding, tech stack)
   - Duplicate tracking across runs (mark as "seen")
   - Email/Slack notifications for high-score jobs

5. **Analytics Dashboard**:
   - Visualize trends (most common tech stacks, locations)
   - Track application success rate
   - Historical score distributions

---

## 📚 References & Resources

### Documentation
- [BeautifulSoup4 Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Playwright Python](https://playwright.dev/python/)
- [scikit-learn TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [gspread Documentation](https://docs.gspread.org/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)

### Job Sites API/RSS
- [RemoteOK RSS](https://remoteok.com/remote-dev-jobs.rss)
- [WeWorkRemotely RSS](https://weworkremotely.com/remote-jobs.rss)
- [Adzuna API](https://developer.adzuna.com/)
- [HackerNews Algolia](https://hn.algolia.com/api)

---

## ✅ Checklist for Implementation

Use this checklist to track progress:

### Phase 1: Infrastructure
- [ ] Project structure created
- [ ] Requirements files created
- [ ] Configuration system implemented
- [ ] Data models (Pydantic) implemented
- [ ] Utilities (logger, rate limiter, cache) implemented

### Phase 2: Scrapers
- [ ] Base scraper implemented
- [ ] 3 simple scrapers (RemoteOK, WWR, HackerNews)
- [ ] 3 API scrapers (Adzuna, Indeed, StackOverflow)
- [ ] 3 complex scrapers (StepStone, XING, GitHub Jobs)

### Phase 3: NLP
- [ ] Tech dictionary created (500+ terms)
- [ ] Tech extractor implemented (FlashText + regex)
- [ ] TF-IDF matcher implemented
- [ ] Optional NER extractor (spaCy)

### Phase 4: Scoring
- [ ] Base scoring components
- [ ] TF-IDF component
- [ ] Tech stack component
- [ ] Remote component
- [ ] Keywords component
- [ ] Contract component
- [ ] Score aggregator

### Phase 5: Processing
- [ ] Pre-filtering implemented
- [ ] Deduplication implemented

### Phase 6: Integration
- [ ] Google Sheets API setup
- [ ] Write jobs to sheet
- [ ] Apply formatting and color coding

### Phase 7: Orchestration
- [ ] Main.py implemented
- [ ] Parallel scraping
- [ ] Full pipeline working

### Phase 8: CI/CD
- [ ] GitHub Actions workflow created
- [ ] Secrets configured
- [ ] Caching configured

### Phase 9: Testing
- [ ] Unit tests for scrapers
- [ ] Unit tests for extractors
- [ ] Unit tests for scorers
- [ ] Integration test
- [ ] Manual testing

### Phase 10: Documentation
- [ ] README.md completed
- [ ] Google Sheets setup guide
- [ ] Customization guide
- [ ] Configuration templates

---

## 🎉 Ready to Start!

This implementation plan provides a complete roadmap for building your intelligent job finder. Follow the phases sequentially, and you'll have a working system in ~2-3 weeks.

**Next immediate step**: Wait for your `profile.yaml` content to start implementation.

Good luck! 🚀

# 🔌 Adding New Scrapers

This guide explains how to add new job sources (scrapers) to Job Finder.

---

## Table of Contents

- [Overview](#overview)
- [BaseScraper Architecture](#basescraper-architecture)
- [Scraper Types](#scraper-types)
- [Step-by-Step Guide](#step-by-step-guide)
- [Testing Your Scraper](#testing-your-scraper)
- [Integration](#integration)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

### What is a Scraper?

A scraper fetches job listings from a specific source (website, RSS feed, API) and converts them into standardized `Job` objects.

### Current Scrapers (9)

1. **RemoteOK** - RSS feed
2. **We Work Remotely** - RSS feed
3. **HackerNews** - HTML scraping
4. **Adzuna** - JSON API
5. **Indeed** - Playwright (dynamic HTML)
6. **StepStone** - Playwright
7. **XING** - Playwright
8. **StackOverflow** - JSON API
9. **GitHub Jobs** - JSON API (deprecated but still works)

### Architecture

```
scrapers/
├── base.py                 # BaseScraper (abstract class)
├── remoteok.py             # RSS example
├── adzuna.py               # JSON API example
├── indeed.py               # Playwright example
└── your_new_scraper.py     # Your implementation
```

---

## BaseScraper Architecture

### Abstract Base Class

Location: `scrapers/base.py`

```python
from abc import ABC, abstractmethod
from typing import List
from models.job import Job

class BaseScraper(ABC):
    """Base class for all job scrapers."""
    
    def __init__(self, rate_limiter=None, cache=None):
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def scrape(self) -> List[Job]:
        """Fetch and parse jobs. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return scraper name (e.g., 'RemoteOK')."""
        pass
    
    def _create_job(self, **kwargs) -> Job:
        """Helper to create Job with validation."""
        try:
            return Job(**kwargs)
        except ValidationError as e:
            self.logger.error(f"Invalid job data: {e}")
            return None
```

### Required Methods

1. **`scrape()`** - Fetch jobs, return `List[Job]`
2. **`get_source_name()`** - Return scraper name (string)

### Optional Helpers

- `_create_job(**kwargs)` - Create validated Job object
- `rate_limiter.wait()` - Respect rate limits
- `cache.get(key)` / `cache.set(key, value)` - Cache results

---

## Scraper Types

### 1. RSS Feed Scraper

**Use when**: Source provides RSS/Atom feed

**Libraries**: `feedparser`, `httpx`

**Example**: RemoteOK, We Work Remotely

**Template**:

```python
import feedparser
import httpx
from scrapers.base import BaseScraper
from models.job import Job

class MyRSSScraper(BaseScraper):
    RSS_URL = "https://example.com/jobs.rss"
    
    async def scrape(self) -> List[Job]:
        # Fetch RSS feed
        async with httpx.AsyncClient() as client:
            response = await client.get(self.RSS_URL)
            response.raise_for_status()
        
        # Parse feed
        feed = feedparser.parse(response.text)
        jobs = []
        
        for entry in feed.entries:
            job = self._parse_entry(entry)
            if job:
                jobs.append(job)
        
        self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
        return jobs
    
    def _parse_entry(self, entry) -> Job:
        """Parse RSS entry into Job object."""
        return self._create_job(
            title=entry.title,
            company=entry.get("author", "Unknown"),
            location=self._extract_location(entry),
            description=entry.description,
            url=entry.link,
            posted_date=self._parse_date(entry.published),
            source=self.get_source_name(),
        )
    
    def _extract_location(self, entry) -> str:
        # Custom logic to extract location
        pass
    
    def _parse_date(self, date_str: str) -> str:
        # Parse date string to ISO format
        from dateutil import parser
        return parser.parse(date_str).isoformat()
    
    def get_source_name(self) -> str:
        return "MyRSS"
```

### 2. JSON API Scraper

**Use when**: Source provides REST API with JSON

**Libraries**: `httpx`

**Example**: Adzuna, StackOverflow Jobs

**Template**:

```python
import httpx
from scrapers.base import BaseScraper
from models.job import Job

class MyAPIScaper(BaseScraper):
    API_URL = "https://api.example.com/jobs"
    API_KEY = "your_api_key"  # Or load from env
    
    async def scrape(self) -> List[Job]:
        jobs = []
        page = 1
        
        while True:
            # Fetch page
            data = await self._fetch_page(page)
            
            if not data or not data.get("results"):
                break
            
            # Parse jobs
            for item in data["results"]:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)
            
            # Check if more pages
            if not data.get("has_more", False):
                break
            
            page += 1
            await self.rate_limiter.wait()  # Be nice to API
        
        self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
        return jobs
    
    async def _fetch_page(self, page: int) -> dict:
        """Fetch single page from API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.API_URL,
                params={
                    "page": page,
                    "api_key": self.API_KEY,
                    "what": "developer",  # Search query
                    "where": "remote",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
    
    def _parse_job(self, item: dict) -> Job:
        """Parse API response item into Job."""
        return self._create_job(
            title=item["title"],
            company=item["company"]["display_name"],
            location=item["location"]["display_name"],
            description=item["description"],
            url=item["redirect_url"],
            posted_date=item["created"],
            source=self.get_source_name(),
            salary=item.get("salary_min"),  # Optional fields
            contract_type=item.get("contract_type"),
        )
    
    def get_source_name(self) -> str:
        return "MyAPI"
```

### 3. Playwright Scraper (Dynamic HTML)

**Use when**: Source uses JavaScript rendering

**Libraries**: `playwright`

**Example**: Indeed, StepStone, XING

**Template**:

```python
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from models.job import Job

class MyPlaywrightScraper(BaseScraper):
    BASE_URL = "https://example.com/jobs"
    
    async def scrape(self) -> List[Job]:
        jobs = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to page
                await page.goto(self.BASE_URL, wait_until="networkidle")
                
                # Wait for jobs to load
                await page.wait_for_selector(".job-card", timeout=10000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Parse jobs
                job_cards = soup.find_all("div", class_="job-card")
                
                for card in job_cards:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                
                # Optional: Click "Load More" button
                # await page.click(".load-more")
                # await page.wait_for_selector(".job-card")
                
            finally:
                await browser.close()
        
        self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
        return jobs
    
    def _parse_card(self, card) -> Job:
        """Parse HTML job card into Job object."""
        title_elem = card.find("h2", class_="job-title")
        company_elem = card.find("span", class_="company-name")
        location_elem = card.find("span", class_="location")
        
        if not title_elem:
            return None
        
        return self._create_job(
            title=title_elem.text.strip(),
            company=company_elem.text.strip() if company_elem else "Unknown",
            location=location_elem.text.strip() if location_elem else "Unknown",
            description=self._extract_description(card),
            url=self._extract_url(card),
            posted_date=self._extract_date(card),
            source=self.get_source_name(),
        )
    
    def _extract_description(self, card) -> str:
        desc_elem = card.find("div", class_="job-description")
        return desc_elem.text.strip() if desc_elem else ""
    
    def _extract_url(self, card) -> str:
        link_elem = card.find("a", class_="job-link")
        if link_elem and link_elem.get("href"):
            return f"https://example.com{link_elem['href']}"
        return ""
    
    def _extract_date(self, card) -> str:
        date_elem = card.find("time")
        if date_elem and date_elem.get("datetime"):
            return date_elem["datetime"]
        return ""
    
    def get_source_name(self) -> str:
        return "MyPlaywright"
```

---

## Step-by-Step Guide

### Step 1: Choose Scraper Type

Determine the source type:

- **RSS feed** → Use RSS template
- **Public JSON API** → Use API template
- **Dynamic HTML (JavaScript)** → Use Playwright template
- **Static HTML** → Use API template with `httpx` + `BeautifulSoup`

### Step 2: Create Scraper File

Create `scrapers/my_source.py`:

```python
from scrapers.base import BaseScraper
from models.job import Job
from typing import List

class MySourceScraper(BaseScraper):
    """Scraper for MySource job board."""
    
    async def scrape(self) -> List[Job]:
        # TODO: Implement
        pass
    
    def get_source_name(self) -> str:
        return "MySource"
```

### Step 3: Implement `scrape()` Method

Follow the template for your scraper type (RSS/API/Playwright).

**Key tasks**:
1. Fetch data (HTTP request, RSS parse, browser automation)
2. Parse response into structured data
3. Convert to `Job` objects using `self._create_job()`
4. Handle errors gracefully (log, skip bad items)
5. Return `List[Job]`

### Step 4: Handle Job Fields

Map source data to `Job` model fields:

```python
from models.job import Job

job = Job(
    title="Backend Developer",               # Required
    company="Acme Corp",                      # Required
    location="Berlin, Germany",               # Required
    description="We are looking for...",      # Required
    url="https://example.com/job/123",        # Required
    posted_date="2025-02-15T10:00:00",        # Required (ISO format)
    source="MySource",                        # Required
    
    # Optional fields
    salary="€60,000 - €80,000",               # Optional
    contract_type="Festanstellung",           # Optional
    remote_type="Remote",                     # Optional
)
```

**Field Requirements**:

| Field | Type | Required | Format |
|-------|------|----------|--------|
| `title` | str | ✅ | Job title |
| `company` | str | ✅ | Company name |
| `location` | str | ✅ | City/country or "Remote" |
| `description` | str | ✅ | Full text (HTML stripped) |
| `url` | str | ✅ | Valid URL |
| `posted_date` | str | ✅ | ISO 8601 (YYYY-MM-DDTHH:MM:SS) |
| `source` | str | ✅ | Source name |
| `salary` | str | ❌ | Any format |
| `contract_type` | str | ❌ | "Festanstellung", "Freiberuflich", etc. |
| `remote_type` | str | ❌ | "Remote", "Hybrid", "Onsite" |

### Step 5: Error Handling

Always handle errors:

```python
async def scrape(self) -> List[Job]:
    jobs = []
    
    try:
        # Fetch data
        data = await self._fetch_data()
    except httpx.HTTPError as e:
        self.logger.error(f"HTTP error: {e}")
        return jobs  # Return empty list
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        return jobs
    
    for item in data:
        try:
            job = self._parse_job(item)
            if job:  # Validate before adding
                jobs.append(job)
        except Exception as e:
            self.logger.warning(f"Failed to parse job: {e}")
            continue  # Skip bad item, continue with rest
    
    return jobs
```

### Step 6: Add Rate Limiting (Optional)

If scraping multiple pages:

```python
async def scrape(self) -> List[Job]:
    jobs = []
    
    for page in range(1, 6):  # 5 pages
        data = await self._fetch_page(page)
        # ... parse data ...
        
        # Wait before next request
        if self.rate_limiter:
            await self.rate_limiter.wait()
    
    return jobs
```

### Step 7: Add Caching (Optional)

Cache results to avoid re-scraping:

```python
async def scrape(self) -> List[Job]:
    cache_key = f"{self.get_source_name()}_jobs"
    
    # Check cache
    if self.cache:
        cached_jobs = self.cache.get(cache_key)
        if cached_jobs:
            self.logger.info(f"Using cached jobs from {self.get_source_name()}")
            return cached_jobs
    
    # Scrape fresh data
    jobs = await self._scrape_fresh()
    
    # Cache results
    if self.cache:
        self.cache.set(cache_key, jobs, ttl=3600)  # 1 hour TTL
    
    return jobs
```

---

## Testing Your Scraper

### Step 1: Create Test File

Create `tests/test_my_source_scraper.py`:

```python
import pytest
from scrapers.my_source import MySourceScraper

@pytest.mark.asyncio
async def test_scrape_returns_jobs():
    """Test that scraper returns list of jobs."""
    scraper = MySourceScraper()
    jobs = await scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0

@pytest.mark.asyncio
async def test_job_fields_valid():
    """Test that jobs have all required fields."""
    scraper = MySourceScraper()
    jobs = await scraper.scrape()
    
    job = jobs[0]
    assert job.title
    assert job.company
    assert job.location
    assert job.description
    assert job.url.startswith("http")
    assert job.posted_date
    assert job.source == "MySource"

@pytest.mark.asyncio
async def test_get_source_name():
    """Test source name."""
    scraper = MySourceScraper()
    assert scraper.get_source_name() == "MySource"
```

### Step 2: Run Tests

```bash
# Run your tests
pytest tests/test_my_source_scraper.py -v

# Run with coverage
pytest tests/test_my_source_scraper.py --cov=scrapers/my_source -v
```

### Step 3: Quick Validation Script

Create `test_scraper_quick.py`:

```python
import asyncio
from scrapers.my_source import MySourceScraper

async def main():
    scraper = MySourceScraper()
    jobs = await scraper.scrape()
    
    print(f"\n✅ Scraped {len(jobs)} jobs\n")
    
    if jobs:
        job = jobs[0]
        print(f"Title: {job.title}")
        print(f"Company: {job.company}")
        print(f"Location: {job.location}")
        print(f"URL: {job.url}")
        print(f"Posted: {job.posted_date}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run:
```bash
python test_scraper_quick.py
```

---

## Integration

### Step 1: Register Scraper

Add scraper to `main.py`:

```python
from scrapers.remoteok import RemoteOKScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.my_source import MySourceScraper  # Import

# In main() function
scrapers = {
    "remoteok": RemoteOKScraper(rate_limiter, cache),
    "weworkremotely": WeWorkRemotelyScraper(rate_limiter, cache),
    "mysource": MySourceScraper(rate_limiter, cache),  # Register
}
```

### Step 2: Update CLI

Add CLI option (already auto-detected from scrapers dict):

```bash
# Use new scraper
python main.py --scrapers mysource

# With other scrapers
python main.py --scrapers remoteok,mysource,hackernews
```

### Step 3: Update Tests

Add integration test in `validate_milestone6.py` (or create new validator):

```python
def test_mysource_scraper_integration():
    """Test MySource scraper in end-to-end pipeline."""
    scraper = MySourceScraper()
    jobs = asyncio.run(scraper.scrape())
    
    assert len(jobs) > 0, "MySource scraper returned no jobs"
    assert all(job.source == "MySource" for job in jobs)
```

### Step 4: Update Documentation

Update `README.md`:

```markdown
## 🌐 Supported Job Sources (10)

1. RemoteOK - Global remote jobs (RSS)
2. We Work Remotely - Remote jobs (RSS)
3. HackerNews Who is Hiring - Monthly thread (HTML)
4. Adzuna - Job search API (JSON API)
5. Indeed - German jobs (Playwright)
6. StepStone - German jobs (Playwright)
7. XING - German professional network (Playwright)
8. StackOverflow Jobs - Developer jobs (JSON API)
9. GitHub Jobs - Tech jobs (JSON API, deprecated)
10. **MySource - Your new source** ✨ (API/RSS/HTML)
```

---

## Best Practices

### 1. Respect robots.txt

Check if scraping is allowed:

```python
# Check https://example.com/robots.txt
# Look for:
# User-agent: *
# Disallow: /jobs
```

### 2. Use Rate Limiting

Don't overload servers:

```python
from utils.rate_limiter import RateLimiter

rate_limiter = RateLimiter(requests_per_second=2)  # Max 2 req/sec
await rate_limiter.wait()
```

### 3. Handle Pagination

Scrape all pages (with limits):

```python
MAX_PAGES = 10  # Safety limit

for page in range(1, MAX_PAGES + 1):
    data = await self._fetch_page(page)
    
    if not data:  # No more results
        break
```

### 4. Strip HTML from Descriptions

Clean description text:

```python
from bs4 import BeautifulSoup

def _clean_description(self, html: str) -> str:
    """Remove HTML tags from description."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)
```

### 5. Normalize Dates

Convert to ISO format:

```python
from dateutil import parser

def _parse_date(self, date_str: str) -> str:
    """Parse various date formats to ISO."""
    try:
        dt = parser.parse(date_str)
        return dt.isoformat()
    except:
        return ""  # Return empty if parse fails
```

### 6. Set User-Agent

Identify your scraper:

```python
async with httpx.AsyncClient(
    headers={"User-Agent": "JobFinder/1.0 (your@email.com)"}
) as client:
    response = await client.get(url)
```

### 7. Log Statistics

Track scraping results:

```python
self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
self.logger.info(f"Failed to parse {failed_count} items")
```

### 8. Handle Authentication

For APIs requiring keys:

```python
import os

class MyAPIScraper(BaseScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MY_API_KEY")
        
        if not self.api_key:
            raise ValueError("MY_API_KEY environment variable not set")
```

### 9. Test with Small Batches

Limit results during development:

```python
async def scrape(self, limit: int = None) -> List[Job]:
    jobs = []
    
    for item in data:
        job = self._parse_job(item)
        if job:
            jobs.append(job)
        
        if limit and len(jobs) >= limit:
            break  # Stop at limit
    
    return jobs
```

### 10. Document Your Scraper

Add comprehensive docstring:

```python
class MySourceScraper(BaseScraper):
    """
    Scraper for MySource job board.
    
    Source: https://example.com/jobs
    Type: JSON API
    Rate Limit: 100 requests/hour
    Authentication: API key required (MY_API_KEY env var)
    
    Returns:
        List of Job objects with:
        - Developer/engineering roles
        - Remote and onsite positions
        - Primarily German market
    
    Example:
        >>> scraper = MySourceScraper()
        >>> jobs = await scraper.scrape()
        >>> len(jobs)
        42
    """
```

---

## Examples

### Example 1: Simple RSS Scraper

Complete implementation for a simple RSS feed:

```python
# scrapers/simplejobs.py
import feedparser
import httpx
from scrapers.base import BaseScraper
from models.job import Job
from typing import List
from dateutil import parser

class SimpleJobsScraper(BaseScraper):
    """Scraper for SimpleJobs RSS feed."""
    
    RSS_URL = "https://simplejobs.com/feed.rss"
    
    async def scrape(self) -> List[Job]:
        """Scrape jobs from SimpleJobs RSS feed."""
        try:
            # Fetch RSS
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.RSS_URL)
                response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.text)
            jobs = []
            
            for entry in feed.entries:
                job = self._parse_entry(entry)
                if job:
                    jobs.append(job)
            
            self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.get_source_name()}: {e}")
            return []
    
    def _parse_entry(self, entry) -> Job:
        """Parse RSS entry into Job object."""
        try:
            return self._create_job(
                title=entry.title,
                company=entry.author if hasattr(entry, "author") else "Unknown",
                location=self._extract_location(entry.title),
                description=entry.description,
                url=entry.link,
                posted_date=parser.parse(entry.published).isoformat(),
                source=self.get_source_name(),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse entry: {e}")
            return None
    
    def _extract_location(self, title: str) -> str:
        """Extract location from title (e.g., 'Developer (Berlin)')."""
        if "(" in title and ")" in title:
            start = title.rfind("(") + 1
            end = title.rfind(")")
            return title[start:end].strip()
        return "Unknown"
    
    def get_source_name(self) -> str:
        return "SimpleJobs"
```

### Example 2: API with Pagination

API scraper with multiple pages:

```python
# scrapers/techjobs.py
import httpx
from scrapers.base import BaseScraper
from models.job import Job
from typing import List

class TechJobsScraper(BaseScraper):
    """Scraper for TechJobs API."""
    
    API_URL = "https://api.techjobs.com/v1/jobs"
    MAX_PAGES = 5
    
    async def scrape(self) -> List[Job]:
        """Scrape jobs from TechJobs API (paginated)."""
        jobs = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, self.MAX_PAGES + 1):
                try:
                    # Fetch page
                    response = await client.get(
                        self.API_URL,
                        params={
                            "page": page,
                            "per_page": 50,
                            "category": "software",
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if empty
                    if not data.get("jobs"):
                        break
                    
                    # Parse jobs
                    for item in data["jobs"]:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)
                    
                    # Rate limit
                    if self.rate_limiter:
                        await self.rate_limiter.wait()
                    
                except Exception as e:
                    self.logger.error(f"Error fetching page {page}: {e}")
                    break
        
        self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
        return jobs
    
    def _parse_job(self, item: dict) -> Job:
        """Parse API item into Job object."""
        try:
            return self._create_job(
                title=item["title"],
                company=item["company"]["name"],
                location=item["location"]["name"],
                description=item["description"],
                url=item["url"],
                posted_date=item["published_at"],
                source=self.get_source_name(),
                salary=item.get("salary"),
                contract_type=item.get("employment_type"),
                remote_type=item.get("remote_type"),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse job: {e}")
            return None
    
    def get_source_name(self) -> str:
        return "TechJobs"
```

### Example 3: Playwright with Dynamic Content

Scraper for JavaScript-heavy site:

```python
# scrapers/dynamicjobs.py
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from models.job import Job
from typing import List
from dateutil import parser

class DynamicJobsScraper(BaseScraper):
    """Scraper for DynamicJobs (requires Playwright)."""
    
    BASE_URL = "https://dynamicjobs.com/jobs"
    
    async def scrape(self) -> List[Job]:
        """Scrape jobs from DynamicJobs using Playwright."""
        jobs = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="JobFinder/1.0"
            )
            page = await context.new_page()
            
            try:
                # Navigate
                await page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
                
                # Wait for job cards to load
                await page.wait_for_selector(".job-card", timeout=10000)
                
                # Optional: Scroll to load more
                await self._scroll_to_load_all(page)
                
                # Get final page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Parse job cards
                cards = soup.find_all("div", class_="job-card")
                
                for card in cards:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                
            except PlaywrightTimeout as e:
                self.logger.error(f"Timeout loading page: {e}")
            except Exception as e:
                self.logger.error(f"Error scraping: {e}")
            finally:
                await browser.close()
        
        self.logger.info(f"Scraped {len(jobs)} jobs from {self.get_source_name()}")
        return jobs
    
    async def _scroll_to_load_all(self, page):
        """Scroll page to trigger lazy loading."""
        for _ in range(3):  # Scroll 3 times
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)  # Wait 1 second
    
    def _parse_card(self, card) -> Job:
        """Parse HTML job card."""
        try:
            title = card.find("h3", class_="title").text.strip()
            company = card.find("span", class_="company").text.strip()
            location = card.find("span", class_="location").text.strip()
            description = card.find("div", class_="description").text.strip()
            
            # Extract URL
            link = card.find("a", class_="job-link")
            url = f"https://dynamicjobs.com{link['href']}" if link else ""
            
            # Extract date
            date_elem = card.find("time")
            posted_date = date_elem["datetime"] if date_elem else ""
            
            return self._create_job(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                posted_date=posted_date,
                source=self.get_source_name(),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse card: {e}")
            return None
    
    def get_source_name(self) -> str:
        return "DynamicJobs"
```

---

## Troubleshooting

### Issue: No Jobs Scraped

**Symptoms**: `scrape()` returns empty list

**Solutions**:
1. Check URL is accessible (test in browser)
2. Verify HTML selectors (inspect page source)
3. Check for API authentication requirements
4. Verify network connectivity
5. Check logs for error messages

### Issue: Pydantic ValidationError

**Symptoms**: `ValidationError: field required` or `invalid date format`

**Solutions**:
1. Ensure all required `Job` fields are provided
2. Convert dates to ISO format: `parser.parse(date_str).isoformat()`
3. Validate URLs start with `http://` or `https://`
4. Use `self._create_job()` helper (handles validation)

### Issue: Playwright Timeout

**Symptoms**: `TimeoutError: Timeout 30000ms exceeded`

**Solutions**:
1. Increase timeout: `await page.goto(url, timeout=60000)`
2. Change wait condition: `wait_until="domcontentloaded"`
3. Check if selector exists: `await page.wait_for_selector(".job-card", state="visible")`
4. Verify site is accessible (test manually)

### Issue: Rate Limiting

**Symptoms**: HTTP 429 (Too Many Requests)

**Solutions**:
1. Add rate limiter: `await self.rate_limiter.wait()`
2. Reduce concurrent requests
3. Add delays between pages: `await asyncio.sleep(2)`
4. Contact site owner for API access

---

## Resources

- **BaseScraper**: `scrapers/base.py`
- **Existing Scrapers**: `scrapers/*.py` (9 examples)
- **Job Model**: `models/job.py`
- **Rate Limiter**: `utils/rate_limiter.py`
- **Main Integration**: `main.py`

**Need help? [Open an issue](https://github.com/DmtiriyK/Job_finder_V2/issues)**

# 🔧 Troubleshooting Guide

Common issues and solutions for Job Finder.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Scraping Errors](#scraping-errors)
- [Scoring Issues](#scoring-issues)
- [Google Sheets Integration](#google-sheets-integration)
- [GitHub Actions](#github-actions)
- [Performance Problems](#performance-problems)
- [Testing Failures](#testing-failures)
- [FAQ](#faq)

---

## Installation Issues

### Issue: `pip install` fails with dependency conflicts

**Symptoms**:
```
ERROR: Cannot install -r requirements-full.txt due to conflicting dependencies
```

**Solutions**:

1. **Use Python 3.11+**:
```bash
python --version  # Should be 3.11.0 or higher
```

2. **Create clean virtual environment**:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Upgrade pip**:
```bash
python -m pip install --upgrade pip
```

4. **Install dependencies**:
```bash
pip install -r requirements-full.txt
```

5. **If still failing, install manually**:
```bash
pip install pydantic httpx playwright feedparser beautifulsoup4
pip install scikit-learn flashtext diskcache
pip install gspread google-auth
pip install pytest pytest-cov pytest-asyncio black flake8
```

### Issue: Playwright browsers not installed

**Symptoms**:
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Solutions**:

```bash
# Install Playwright browsers
playwright install

# Or specific browser
playwright install chromium

# If permission denied (Linux)
sudo playwright install chromium
```

### Issue: ImportError for `flashtext`

**Symptoms**:
```
ImportError: No module named 'flashtext'
```

**Solutions**:

```bash
# Install flashtext
pip install flashtext

# If fails, install from GitHub
pip install git+https://github.com/vi3k6i5/flashtext.git
```

---

## Configuration Problems

### Issue: Missing `.env` file

**Symptoms**:
```
WARNING: .env file not found, using default settings
```

**Solutions**:

1. **Copy example**:
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

2. **Edit `.env`**:
```env
LOG_LEVEL=INFO
CACHE_ENABLED=true
MIN_SCORE=40
```

### Issue: `profile.yaml` not found

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/profile.yaml'
```

**Solutions**:

1. **Create profile**:
```bash
# Create from template
cat > config/profile.yaml << EOF
name: "Your Name"
roles:
  - "Backend Developer"
  - "Software Engineer"

skills:
  - name: "Python"
    experience_years: 5
    proficiency: 9

preferences:
  remote: "yes"
  locations:
    - "Remote"
  contract_types:
    - "Festanstellung"

profile_text: |
  Your profile description here...
EOF
```

2. **Check path** (must be `config/profile.yaml`, not `profile.yaml`)

### Issue: Tech not recognized from `tech_dictionary.json`

**Symptoms**:
- Jobs show empty `tech_stack`
- Technologies not extracted

**Solutions**:

1. **Verify tech name** in `config/tech_dictionary.json`:
```json
{
  "languages": {
    "Python": ["Python", "python", "py"]
  }
}
```

2. **Check profile.yaml** uses exact key:
```yaml
skills:
  - name: "Python"  # Must match key in tech_dictionary.json
```

3. **Add aliases** if tech has variants:
```json
{
  "databases": {
    "PostgreSQL": ["PostgreSQL", "Postgres", "postgres", "PSQL", "pg"]
  }
}
```

### Issue: Scoring rules validation error

**Symptoms**:
```
pydantic.ValidationError: weights must sum to 100
```

**Solutions**:

Ensure weights in `config/scoring_rules.yaml` sum to 100:

```yaml
weights:
  tfidf_similarity: 40
  tech_stack_match: 30
  remote_priority: 15
  keyword_match: 10
  contract_type: 5
# Total = 100 ✓
```

---

## Scraping Errors

### Issue: No jobs scraped from any source

**Symptoms**:
```
INFO: Scraped 0 jobs from RemoteOK
INFO: Scraped 0 jobs from WeWorkRemotely
...
```

**Solutions**:

1. **Check internet connection**:
```bash
ping google.com
```

2. **Test specific scraper**:
```bash
python main.py --scrapers remoteok --output test.json
```

3. **Check logs** for errors:
```bash
cat logs/app.log | grep ERROR
```

4. **Verify source URLs** are accessible:
```bash
curl https://remoteok.com/remote-jobs.rss
```

5. **Try with different scrapers**:
```bash
python main.py --scrapers hackernews,adzuna
```

### Issue: Playwright scraper timeout

**Symptoms**:
```
playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded
```

**Solutions**:

1. **Increase timeout** in scraper code:
```python
await page.goto(url, timeout=60000)  # 60 seconds
```

2. **Change wait condition**:
```python
await page.goto(url, wait_until="domcontentloaded")
# Instead of "networkidle"
```

3. **Check site is up**:
```bash
curl -I https://example.com/jobs
```

4. **Disable headless** for debugging:
```python
browser = await p.chromium.launch(headless=False)
```

### Issue: HTTP 403 Forbidden

**Symptoms**:
```
httpx.HTTPStatusError: Client error '403 Forbidden'
```

**Solutions**:

1. **Add User-Agent header**:
```python
async with httpx.AsyncClient(
    headers={"User-Agent": "Mozilla/5.0"}
) as client:
    response = await client.get(url)
```

2. **Check robots.txt**:
```bash
curl https://example.com/robots.txt
```

3. **Respect rate limits** (add delays):
```python
await asyncio.sleep(2)  # Wait 2 seconds
```

### Issue: HTTP 429 Too Many Requests

**Symptoms**:
```
httpx.HTTPStatusError: Client error '429 Too Many Requests'
```

**Solutions**:

1. **Enable rate limiter**:
```python
from utils.rate_limiter import RateLimiter

rate_limiter = RateLimiter(requests_per_second=1)
await rate_limiter.wait()
```

2. **Reduce concurrent requests** in `.env`:
```env
MAX_CONCURRENT_REQUESTS=1
REQUEST_DELAY_SECONDS=3
```

3. **Enable caching** to avoid re-scraping:
```env
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
```

### Issue: RSS feed parse error

**Symptoms**:
```
xml.etree.ElementTree.ParseError: not well-formed
```

**Solutions**:

1. **Check feed URL**:
```bash
curl https://remoteok.com/remote-jobs.rss
```

2. **Validate RSS** at https://validator.w3.org/feed/

3. **Handle empty feed**:
```python
feed = feedparser.parse(response.text)

if not feed.entries:
    self.logger.warning("RSS feed is empty")
    return []
```

---

## Scoring Issues

### Issue: All jobs have low scores (<30)

**Symptoms**:
- No jobs pass filter
- Top job scores are 20-30

**Solutions**:

1. **Lower MIN_SCORE**:
```env
MIN_SCORE=20  # Instead of 40
```

2. **Expand profile_text** with more keywords:
```yaml
profile_text: |
  Add more technologies, frameworks, tools, methodologies,
  industries, domains, soft skills, etc.
```

3. **Add more skills** to profile:
```yaml
skills:
  - name: "Python"
    experience_years: 5
    proficiency: 9
  - name: "Django"
    experience_years: 3
    proficiency: 8
  - name: "FastAPI"
    experience_years: 2
    proficiency: 7
  # Add ALL technologies you know
```

4. **Adjust weights** in scoring_rules.yaml:
```yaml
weights:
  tfidf_similarity: 50  # Increase semantic match
  tech_stack_match: 20
  remote_priority: 15
  keyword_match: 10
  contract_type: 5
```

### Issue: Wrong jobs scoring high (irrelevant results)

**Symptoms**:
- PHP jobs when you want Python
- Junior roles when you're senior

**Solutions**:

1. **Add negative techs**:
```yaml
tech_stack:
  negative:
    - name: "PHP"
      points: -10
    - name: "WordPress"
      points: -10
```

2. **Add negative keywords**:
```yaml
keywords:
  negative:
    - keyword: "junior"
      points: -5
    - keyword: "intern"
      points: -5
```

3. **Increase tech_stack weight**:
```yaml
weights:
  tfidf_similarity: 30
  tech_stack_match: 40  # Prioritize tech match
```

### Issue: Tech stack not extracted

**Symptoms**:
- `tech_stack` field is empty `[]`
- Technologies in description not recognized

**Solutions**:

1. **Verify tech in dictionary**:
```bash
grep -i "docker" config/tech_dictionary.json
```

2. **Add missing tech**:
```json
{
  "tools": {
    "Docker": ["Docker", "docker", "docker-compose"]
  }
}
```

3. **Check description** isn't empty:
```python
print(job.description)  # Should contain text
```

4. **Test extractor directly**:
```python
from extractors.tech_extractor import TechExtractor

extractor = TechExtractor()
techs = extractor.extract("Looking for Python and Docker experience")
print(techs)  # Should show ['Python', 'Docker']
```

---

## Google Sheets Integration

### Issue: `gspread.exceptions.APIError: Quota exceeded`

**Symptoms**:
```
gspread.exceptions.APIError: [429] Quota exceeded for quota metric 'Queries' and limit 'Queries per minute per user'
```

**Solutions**:

1. **Reduce frequency**:
```yaml
# In .github/workflows/daily_scraper.yml
schedule:
  - cron: '0 9 * * *'  # Once per day, not every hour
```

2. **Add delay between writes**:
```python
for job in jobs:
    sheet.append_row(job)
    time.sleep(1)  # Wait 1 second
```

3. **Batch writes**:
```python
# Instead of append_row() for each job
rows = [job.to_list() for job in jobs]
sheet.append_rows(rows)  # Single API call
```

### Issue: `gspread.exceptions.SpreadsheetNotFound`

**Symptoms**:
```
gspread.exceptions.SpreadsheetNotFound: No spreadsheet found
```

**Solutions**:

1. **Create spreadsheet** first:
```python
gc = gspread.service_account(filename="credentials.json")
sh = gc.create("Job Finder Results")
```

2. **Check spreadsheet ID** in URL:
```
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

3. **Share with service account**:
   - Open spreadsheet
   - Click "Share"
   - Add service account email (from `credentials.json`)
   - Grant "Editor" access

### Issue: Authentication failed

**Symptoms**:
```
google.auth.exceptions.DefaultCredentialsError: Could not load credentials
```

**Solutions**:

1. **Check credentials file exists**:
```bash
ls credentials.json
```

2. **Verify JSON format**:
```bash
cat credentials.json | python -m json.tool
```

3. **Set environment variable**:
```bash
# Windows
set GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

4. **Use explicit path**:
```python
gc = gspread.service_account(
    filename="C:\\path\\to\\credentials.json"
)
```

### Issue: Column mismatch in Google Sheets

**Symptoms**:
- Data appears in wrong columns
- Headers don't match data

**Solutions**:

1. **Check export format** matches sheet headers:
```python
# integrations/google_sheets.py
headers = [
    "Score", "Title", "Company", "Location", "Remote",
    "Tech Stack", "Salary", "Contract", "Posted Date",
    "Source", "Match %", "Description", "URL"
]
```

2. **Clear sheet** and re-export:
```bash
python main.py --export-sheets --sheets-name "Jobs" --clear-first
```

---

## GitHub Actions

### Issue: Workflow fails with "playwright not found"

**Symptoms**:
```
Error: Executable doesn't exist at /home/runner/.cache/ms-playwright/chromium-1005/chrome-linux/chrome
```

**Solutions**:

Add Playwright browser install step:

```yaml
# .github/workflows/daily_scraper.yml
- name: Install Playwright Browsers
  run: playwright install chromium
```

### Issue: `credentials.json` not found in Actions

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'credentials.json'
```

**Solutions**:

1. **Add secret** to GitHub repository settings
2. **Create file in workflow**:
```yaml
- name: Create credentials file
  run: echo '${{ secrets.GOOGLE_CREDENTIALS_JSON }}' > credentials.json
```

### Issue: GitHub Actions quota exceeded

**Symptoms**:
```
Error: You have exceeded your spending limit for GitHub Actions
```

**Solutions**:

1. **Check usage** (Settings → Billing):
   - Free tier: 2000 minutes/month
   
2. **Optimize workflow**:
```yaml
# Run less frequently
schedule:
  - cron: '0 9 * * 1,3,5'  # Mon, Wed, Fri only
```

3. **Use caching**:
```yaml
- name: Cache pip
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements-full.txt') }}
```

### Issue: Secrets not available

**Symptoms**:
```
env:
  MY_SECRET: ${{ secrets.MY_SECRET }}  # Empty!
```

**Solutions**:

1. **Add secret** to repository:
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add secret name and value

2. **Use correct secret name**:
```yaml
env:
  GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}
  # Must match secret name exactly (case-sensitive)
```

---

## Performance Problems

### Issue: Scraping takes >5 minutes

**Symptoms**:
- Pipeline runs slow
- Timeout errors

**Solutions**:

1. **Enable caching**:
```env
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
```

2. **Reduce concurrent requests**:
```env
MAX_CONCURRENT_REQUESTS=3  # Lower number
```

3. **Scrape fewer sources**:
```bash
python main.py --scrapers remoteok,hackernews  # Only 2 sources
```

4. **Limit top results**:
```bash
python main.py --top-n 10  # Only top 10 jobs
```

### Issue: High memory usage

**Symptoms**:
- Process uses >2GB RAM
- System becomes slow

**Solutions**:

1. **Process jobs in batches**:
```python
for batch in batched(jobs, batch_size=100):
    scored_jobs = scorer.score(batch)
```

2. **Clear cache periodically**:
```python
cache.clear()
```

3. **Reduce scrapers**:
```bash
#Don't scrape all 9 sources at once
python main.py --scrapers remoteok,indeed
```

### Issue: TF-IDF scoring slow

**Symptoms**:
- Scoring takes >30 seconds

**Solutions**:

1. **Reduce max_features**:
```python
# scorers/components/tfidf_component.py
vectorizer = TfidfVectorizer(
    max_features=500  # Instead of 1000
)
```

2. **Use joblib caching**:
```python
from joblib import Memory

memory = Memory("cache/scoring", verbose=0)

@memory.cache
def tfidf_score(description, profile):
    # Cached scoring
    pass
```

---

## Testing Failures

### Issue: `pytest` fails with import errors

**Symptoms**:
```
ImportError: No module named 'scrapers'
```

**Solutions**:

1. **Install package in editable mode**:
```bash
pip install -e .
```

2. **Run from project root**:
```bash
cd /path/to/Job_finder
pytest tests/
```

3. **Set PYTHONPATH**:
```bash
# Windows
set PYTHONPATH=.

# Linux/Mac
export PYTHONPATH=.

pytest tests/
```

### Issue: Async tests fail

**Symptoms**:
```
RuntimeError: This event loop is already running
```

**Solutions**:

1. **Install pytest-asyncio**:
```bash
pip install pytest-asyncio
```

2. **Use `@pytest.mark.asyncio`**:
```python
import pytest

@pytest.mark.asyncio
async def test_scraper():
    scraper = MyScaper()
    jobs = await scraper.scrape()
    assert len(jobs) > 0
```

### Issue: Tests pass locally but fail in CI

**Symptoms**:
- Tests pass on your machine
- GitHub Actions tests fail

**Solutions**:

1. **Check Python version**:
```yaml
# .github/workflows/test.yml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'  # Match local version
```

2. **Install all dependencies**:
```yaml
- name: Install dependencies
  run: |
    pip install -r requirements-full.txt
    playwright install chromium
```

3. **Check environment differences**:
```python
import sys
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")
```

### Issue: Coverage below threshold

**Symptoms**:
```
FAIL: Coverage is 75%, below threshold of 80%
```

**Solutions**:

1. **Identify uncovered code**:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

2. **Add missing tests**:
```python
# tests/test_missing_coverage.py
def test_edge_case():
    # Test uncovered branch
    pass
```

3. **Exclude non-critical files**:
```ini
# .coveragerc
[run]
omit =
    tests/*
    venv/*
    */__pycache__/*
```

---

## FAQ

### Q: How do I add a new scraper?

**A**: See [ADDING_SCRAPERS.md](ADDING_SCRAPERS.md) for detailed guide.

### Q: How do I customize scoring?

**A**: See [CUSTOMIZATION.md](CUSTOMIZATION.md) for configuration options.

### Q: Which scrapers are fastest?

**A**:
- **Fast** (RSS/API): RemoteOK, WeWorkRemotely, Adzuna, HackerNews
- **Medium**: StackOverflow, GitHub Jobs
- **Slow** (Playwright): Indeed, StepStone, XING

### Q: Can I run without Google Sheets?

**A**: Yes, use `--output` flag:
```bash
python main.py --output results.json
```

### Q: Can I scrape only remote jobs?

**A**: Yes, use filter in `.env`:
```env
LOCATION_FILTER=Remote
```

Or post-process results:
```python
remote_jobs = [job for job in jobs if job.remote_type == "Remote"]
```

### Q: How do I export to CSV instead of JSON?

**A**: Convert JSON to CSV:
```python
import pandas as pd

df = pd.read_json("results.json")
df.to_csv("results.csv", index=False)
```

Or use Google Sheets export (already CSV-like).

### Q: Can I use this for non-tech jobs?

**A**: Yes, but you'll need to:
1. Update `tech_dictionary.json` with relevant terms
2. Modify scoring rules
3. Add domain-specific scrapers

### Q: Is this free to use?

**A**: Yes, MIT license. All services used (GitHub Actions, Google Sheets API) have free tiers sufficient for personal use.

### Q: Can I deploy this on AWS/Azure?

**A**: Yes, use scheduled Lambda/Function:
```yaml
# AWS Lambda with EventBridge schedule
schedule: rate(1 day)
runtime: python3.11
handler: main.lambda_handler
```

### Q: How do I debug a failing scraper?

**A**:
1. Enable DEBUG logging:
```env
LOG_LEVEL=DEBUG
```

2. Run single scraper:
```bash
python main.py --scrapers remoteok --output test.json
```

3. Check logs:
```bash
tail -f logs/app.log
```

4. Test manually:
```python
import asyncio
from scrapers.remoteok import RemoteOKScraper

scraper = RemoteOKScraper()
jobs = asyncio.run(scraper.scrape())
print(f"Scraped {len(jobs)} jobs")
```

### Q: How do I contribute a new scraper?

**A**:
1. Fork repository
2. Add scraper to `scrapers/`
3. Add tests to `tests/`
4. Update documentation
5. Submit Pull Request

See [ADDING_SCRAPERS.md](ADDING_SCRAPERS.md) for details.

---

## Getting Help

### 1. Check Logs

```bash
# View recent logs
tail -50 logs/app.log

# Search for errors
grep ERROR logs/app.log

# Watch live logs
tail -f logs/app.log
```

### 2. Enable Debug Mode

```env
# .env
LOG_LEVEL=DEBUG
```

### 3. Run Validation Scripts

```bash
# Test all components
python validate_milestone6.py  # Scrapers
python validate_milestone7.py  # Google Sheets
python validate_milestone8.py  # GitHub Actions
```

### 4. Check GitHub Issues

Search existing issues: https://github.com/DmtiriyK/Job_finder_V2/issues

### 5. Open New Issue

If problem persists, [open an issue](https://github.com/DmtiriyK/Job_finder_V2/issues/new) with:
- Error message
- Full logs (`logs/app.log`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce

---

## Resources

- **Main README**: [../README.md](../README.md)
- **Customization Guide**: [CUSTOMIZATION.md](CUSTOMIZATION.md)
- **Adding Scrapers**: [ADDING_SCRAPERS.md](ADDING_SCRAPERS.md)
- **Google Sheets Setup**: [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)
- **GitHub Actions Setup**: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

---

**Still stuck? [Open an issue](https://github.com/DmtiriyK/Job_finder_V2/issues) and we'll help!**

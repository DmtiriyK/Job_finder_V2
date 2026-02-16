# GitHub Actions Setup Guide

This guide explains how to set up the Job Finder to run automatically in GitHub Actions.

---

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step-by-Step Setup](#step-by-step-setup)
3. [Configuration](#configuration)
4. [Manual Trigger](#manual-trigger)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## 🔧 Prerequisites

Before setting up GitHub Actions, ensure you have:

✅ **GitHub Repository**:
- Job Finder code pushed to GitHub
- Repository is public or you have GitHub Actions enabled

✅ **Google Sheets Credentials** (from M7):
- `config/google_credentials.json` file (Service Account key)
- Google Sheet created and shared with service account email
- See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for details

✅ **GitHub Actions Enabled**:
- Go to repository → **Settings** → **Actions** → **General**
- Ensure "Allow all actions and reusable workflows" is selected

---

## 🚀 Step-by-Step Setup

### Step 1: Configure GitHub Secrets

1. **Go to Repository Settings**:
   ```
   GitHub Repository → Settings → Secrets and variables → Actions
   ```

2. **Add Google Sheets Credentials Secret**:
   - Click **New repository secret**
   - **Name**: `GOOGLE_SHEETS_CREDENTIALS`
   - **Value**: Copy entire contents of `config/google_credentials.json`
   ```json
   {
     "type": "service_account",
     "project_id": "job-finder-123456",
     "private_key_id": "abc123...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "job-finder@job-finder-123456.iam.gserviceaccount.com",
     ...
   }
   ```
   - Click **Add secret**

3. **Verify Secret Added**:
   - You should see `GOOGLE_SHEETS_CREDENTIALS` in the secrets list
   - Secret value is hidden (shows as `***`)

### Step 2: Commit Workflow File

The workflow file is already included in the repository:
```
.github/workflows/daily_scraper.yml
```

If you've modified it, commit and push:
```bash
git add .github/workflows/daily_scraper.yml
git commit -m "chore: Add GitHub Actions workflow for daily scraper"
git push origin main
```

### Step 3: Verify Workflow Appears

1. Go to **Actions** tab in your GitHub repository
2. You should see **Daily Job Scraper** workflow listed
3. Workflow is now ready to run!

---

## ⚙️ Configuration

### Scheduled Run

The workflow runs automatically at **09:00 CET (08:00 UTC)** every day.

To modify the schedule, edit `.github/workflows/daily_scraper.yml`:
```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # 09:00 CET (08:00 UTC)
```

**Example Cron Expressions**:
- `'0 9 * * *'` - 10:00 CET (09:00 UTC)
- `'0 8 * * 1-5'` - 09:00 CET, Monday-Friday only
- `'0 8,18 * * *'` - 09:00 CET and 19:00 CET (twice daily)

**Cron Format**: `minute hour day month weekday`
- Use [crontab.guru](https://crontab.guru/) to generate cron expressions

### Default Scrapers

By default, the workflow runs with these scrapers:
- `remoteok`
- `weworkremotely`
- `hackernews`

To change default scrapers, edit the workflow file:
```yaml
python main.py --export-sheets --top-n 20 --scrapers remoteok,weworkremotely,hackernews
```

### Timeout

Maximum workflow runtime is **15 minutes**:
```yaml
jobs:
  scrape-jobs:
    timeout-minutes: 15
```

Increase if needed (GitHub free plan: 2000 minutes/month).

---

## 🖱️ Manual Trigger

You can manually run the workflow anytime:

### Option 1: GitHub UI

1. Go to **Actions** tab
2. Select **Daily Job Scraper** workflow
3. Click **Run workflow** dropdown
4. (Optional) Customize parameters:
   - **top_n**: Number of top jobs to export (default: 20)
   - **scrapers**: Comma-separated scraper names (default: remoteok,weworkremotely,hackernews)
5. Click **Run workflow** button

### Option 2: GitHub CLI

```bash
# Run with default parameters
gh workflow run daily_scraper.yml

# Run with custom parameters
gh workflow run daily_scraper.yml \
  -f top_n=50 \
  -f scrapers=remoteok,weworkremotely,hackernews,stackoverflow
```

### Option 3: API Call

```bash
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_USERNAME/Job_finder/actions/workflows/daily_scraper.yml/dispatches \
  -d '{"ref":"main","inputs":{"top_n":"20","scrapers":"remoteok"}}'
```

---

## 📊 Monitoring

### View Workflow Runs

1. Go to **Actions** tab
2. Click on **Daily Job Scraper** workflow
3. See list of all runs with status:
   - ✅ **Success**: Completed without errors
   - ❌ **Failure**: Encountered errors
   - 🟡 **In Progress**: Currently running
   - ⭕ **Cancelled**: Manually stopped

### View Run Details

1. Click on a specific run
2. Click on **Scrape and Export Jobs** job
3. Expand steps to see detailed logs:
   - **Setup Python**: ~10 seconds
   - **Install dependencies**: ~45 seconds
   - **Install Playwright browsers**: ~15 seconds (cached: ~5 seconds)
   - **Run Job Scraper**: ~3-4 minutes
   - **Upload logs**: ~5 seconds

### Download Logs

1. Go to workflow run details
2. Scroll to **Artifacts** section
3. Download **job-scraper-logs-{run_number}**
4. Unzip to view detailed logs

**Log Files**:
- `job_finder.log` - Main application log
- Logs retained for **30 days**

### Email Notifications

GitHub sends email notifications for:
- ❌ **Workflow failures** (enabled by default)
- ✅ **Workflow successes** (optional)

Configure in: **Settings** → **Notifications** → **Actions**

---

## 🐛 Troubleshooting

### ❌ Error: "Secret GOOGLE_SHEETS_CREDENTIALS not found"

**Cause**: Secret not configured or misspelled

**Solution**:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Verify `GOOGLE_SHEETS_CREDENTIALS` exists
3. Name must match exactly (case-sensitive)
4. Re-add secret if needed

---

### ❌ Error: "Invalid credentials JSON"

**Cause**: Malformed JSON in secret value

**Solution**:
1. Open `config/google_credentials.json` locally
2. Verify it's valid JSON (use [jsonlint.com](https://jsonlint.com/))
3. Copy **entire file contents** (including all newlines in private_key)
4. Paste into GitHub secret without modifications

---

### ❌ Error: "Playwright browser not found"

**Cause**: Browser cache not working or corrupted

**Solution**:
1. Edit workflow file to force reinstall:
   ```yaml
   - name: Install Playwright browsers
     run: |
       playwright install chromium
       playwright install-deps chromium
   ```
2. Commit and push changes
3. Clear Actions cache: **Settings** → **Actions** → **Management** → **Clear caches**

---

### ❌ Error: "Workflow timeout after 15 minutes"

**Cause**: Scrapers taking too long

**Solution 1**: Increase timeout
```yaml
jobs:
  scrape-jobs:
    timeout-minutes: 20  # Increase from 15 to 20
```

**Solution 2**: Reduce number of scrapers
```yaml
python main.py --export-sheets --top-n 20 --scrapers remoteok,hackernews
```

**Solution 3**: Use cache (already configured)
- Cache is automatically enabled for Playwright browsers
- First run: ~5 minutes
- Cached runs: ~3 minutes

---

### ❌ Error: "Permission denied" when writing to Google Sheets

**Cause**: Service account doesn't have access to spreadsheet

**Solution**:
1. Open Google Sheet
2. Click **Share** button
3. Add service account email (from credentials JSON):
   ```
   job-finder@job-finder-123456.iam.gserviceaccount.com
   ```
4. Grant **Editor** permissions
5. Click **Send**

See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for details.

---

### ⚠️ Warning: "Rate limit exceeded"

**Cause**: Scraped too many jobs too quickly

**Solution**:
- Built-in rate limiter should prevent this
- If it occurs, workflow will retry automatically
- Reduce `--top-n` value if needed

---

### 📊 Workflow runs but no jobs exported

**Possible Causes**:
1. **No jobs found**: Check scraper logs in artifacts
2. **All jobs filtered out**: Review `config/profile.yaml` filters
3. **Low scores**: All jobs below `min_score` threshold

**Debug Steps**:
1. Download logs from workflow run
2. Search for lines containing:
   - `[INFO] Scraping completed: X jobs`
   - `[INFO] After filtering: X jobs`
   - `[INFO] Top 20 jobs`
3. Adjust filters in `config/profile.yaml` if needed

---

## 🔒 Security Best Practices

### 1. Never Commit Credentials

✅ **Good**:
```bash
# config/google_credentials.json is in .gitignore
git status
# Should NOT show config/google_credentials.json
```

❌ **Bad**:
```bash
git add config/google_credentials.json  # DON'T DO THIS!
```

### 2. Rotate Service Account Keys

- Rotate keys every **90 days**
- Delete old keys after rotation
- Update GitHub secret with new key

### 3. Limit Secret Access

- Use **repository secrets** (not environment secrets for public repos)
- Secrets are only accessible during workflow runs
- Secret values never appear in logs

### 4. Review Workflow Logs

- Logs should NOT contain credential values
- If credentials appear in logs, rotate them immediately

### 5. Restrict Workflow Permissions

The workflow uses minimal permissions:
```yaml
permissions:
  contents: read  # Read-only access to repo
```

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Schedule Triggers](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [crontab.guru](https://crontab.guru/) - Cron expression editor

---

## 🎯 Example Workflow Run

**Successful Run Output**:
```
✅ Setup Python 3.11               (10s)
✅ Install dependencies            (45s, cached: 20s)
✅ Install Playwright browsers     (15s, cached: 5s)
✅ Setup Google Sheets credentials (1s)
✅ Run Job Scraper
   [INFO] Scraping completed: 424 jobs
   [INFO] After filtering: 186 jobs
   [INFO] After deduplication: 178 jobs
   [INFO] Scoring completed: 178 jobs
   [INFO] Top 20 jobs written to Google Sheets
   [INFO] Pipeline completed in 3m 42s
   (3m 52s)
✅ Upload logs                     (7s)
✅ Clean up credentials            (1s)

Total Duration: 4m 56s
```

---

## 🔄 Updating the Workflow

### Add New Environment Variables

```yaml
- name: Run Job Scraper
  env:
    LOG_LEVEL: "DEBUG"  # Add this
    USE_ADVANCED_NLP: "true"  # Add this
  run: |
    python main.py --export-sheets --top-n 20
```

### Add New Secrets

1. Create new secret in GitHub:
   - Settings → Secrets and variables → Actions → New repository secret
2. Use in workflow:
   ```yaml
   env:
     MY_SECRET: ${{ secrets.MY_SECRET_NAME }}
   ```

### Test Changes Locally First

```bash
# Simulate GitHub Actions environment
export PYTHONUNBUFFERED=1
export LOG_LEVEL=INFO

python main.py --export-sheets --top-n 20
```

---

## ✅ Checklist

Before first run, verify:

- [ ] GitHub repository created and code pushed
- [ ] `GOOGLE_SHEETS_CREDENTIALS` secret configured
- [ ] Google Sheet shared with service account
- [ ] Workflow file committed (`.github/workflows/daily_scraper.yml`)
- [ ] GitHub Actions enabled in repository settings
- [ ] Manual test run completed successfully
- [ ] Scheduled time configured correctly (cron expression)
- [ ] Email notifications configured (optional)

**Ready to go!** 🚀

The workflow will run automatically every day at 09:00 CET, or you can trigger it manually anytime.

# Google Sheets Setup Guide

This guide explains how to set up Google Sheets API integration for Job Finder.

## Prerequisites

- Google account
- Python 3.11+
- Job Finder project installed

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" (or select existing project)
3. Enter project name: `job-finder-sheets`
4. Click "Create"

### 2. Enable Google Sheets API

1. In Google Cloud Console, go to **APIs & Services > Library**
2. Search for "Google Sheets API"
3. Click on it and press **Enable**
4. Also enable "Google Drive API"

### 3. Create Service Account

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > Service Account**
3. Enter details:
   - **Service account name**: `job-finder-writer`
   - **Service account ID**: (auto-generated)
   - Click **Create and Continue**
4. Grant roles (optional):
   - Skip for now, click **Continue**
5. Click **Done**

### 4. Create Service Account Key

1. In **Credentials** page, find your service account
2. Click on the service account email
3. Go to **Keys** tab
4. Click **Add Key > Create new key**
5. Select **JSON** format
6. Click **Create**
7. JSON file will download automatically

### 5. Save Credentials

1. Rename downloaded file to `google_credentials.json`
2. Move it to Job Finder project:
   ```bash
   mv ~/Downloads/job-finder-*.json config/google_credentials.json
   ```
3. **IMPORTANT**: Add to `.gitignore` (already done):
   ```
   config/google_credentials.json
   ```

### 6. Create Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create new spreadsheet
3. Name it: `Job Finder Results`
4. Copy the spreadsheet URL

### 7. Share Sheet with Service Account

**IMPORTANT**: Service accounts need explicit access to spreadsheets.

1. Open your Google Sheet
2. Click **Share** button
3. Paste service account email:
   - Find in `google_credentials.json`: `"client_email": "...@....iam.gserviceaccount.com"`
4. Give **Editor** permissions
5. Click **Send**

### 8. Test Integration

Run Job Finder with Google Sheets export:

```bash
python main.py --export-sheets
```

Expected output:
```
[INFO] Google Sheets client initialized successfully
[INFO] Successfully wrote 20 jobs to Google Sheets: https://docs.google.com/spreadsheets/d/...
```

## Configuration

### Environment Variables

You can use environment variables instead of hardcoded paths:

```bash
# Windows PowerShell
$env:GOOGLE_CREDENTIALS_PATH="C:\path\to\credentials.json"
$env:GOOGLE_SHEETS_SHARE_EMAIL="your-email@gmail.com"

# Linux/macOS
export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"
export GOOGLE_SHEETS_SHARE_EMAIL="your-email@gmail.com"
```

### Spreadsheet Name

By default, spreadsheet is named "Job Finder Results". To change:

```python
from integrations.google_sheets import GoogleSheetsWriter

writer = GoogleSheetsWriter(spreadsheet_name="My Custom Name")
```

### Sheet Name

Each run creates a new worksheet named "Job Finder - YYYY-MM-DD". To change:

```python
writer.write_jobs(jobs, scores, sheet_name="Custom Sheet Name")
```

## Troubleshooting

### Error: "Spreadsheet not found"

**Solution**: Share spreadsheet with service account email.

1. Open `config/google_credentials.json`
2. Find `"client_email"` value
3. Share Google Sheet with this email

### Error: "Permission denied"

**Solution**: Grant Editor permissions to service account.

### Error: "API not enabled"

**Solution**: Enable Google Sheets API and Google Drive API in Cloud Console.

### Error: "Credentials not found"

**Solution**: Ensure `config/google_credentials.json` exists with valid JSON.

### Warning: "Google credentials not found"

**Solution**: Download service account key and save to `config/google_credentials.json`.

## Sheet Structure

The exported sheet has 13 columns:

| Column | Description |
|--------|-------------|
| Date Found | Job posting date |
| Title | Job title |
| Company | Company name |
| Location | Job location |
| Remote | Remote work type |
| Contract | Contract type |
| Tech Stack | Technologies (comma-separated) |
| Score | Matching score (0-100) |
| Breakdown | Score component breakdown |
| URL | Job posting URL (clickable) |
| Source | Source scraper |
| Applied? | Checkbox (manual) |
| Notes | Free text notes (manual) |

## Color Coding

Rows are automatically color-coded based on score:

- **Green** (score ≥ 80): High match
- **Yellow** (60 ≤ score < 80): Medium match
- **White** (score < 60): Low match

## Advanced Usage

### Multiple Spreadsheets

Create separate spreadsheets for different searches:

```python
# Backend jobs
backend_writer = GoogleSheetsWriter(spreadsheet_name="Backend Jobs")
backend_writer.write_jobs(backend_jobs, backend_scores)

# Frontend jobs
frontend_writer = GoogleSheetsWriter(spreadsheet_name="Frontend Jobs")
frontend_writer.write_jobs(frontend_jobs, frontend_scores)
```

### Custom Formatting

Extend `GoogleSheetsWriter` class for custom formatting:

```python
class CustomSheetsWriter(GoogleSheetsWriter):
    def _get_color_for_score(self, score: float):
        # Custom color logic
        if score >= 90:
            return {'red': 0.0, 'green': 1.0, 'blue': 0.0}  # Bright green
        return super()._get_color_for_score(score)
```

## Security Best Practices

1. **Never commit credentials**:
   - Ensure `google_credentials.json` is in `.gitignore`
   
2. **Rotate keys regularly**:
   - Delete old keys in Cloud Console
   - Create new keys every 90 days

3. **Use environment variables**:
   - Store credentials path in env vars
   - Don't hardcode in source code

4. **Limit permissions**:
   - Only grant "Editor" access to specific sheet
   - Don't use owner account as service account

5. **Monitor usage**:
   - Check Cloud Console for API usage
   - Set up billing alerts

## Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [gspread Library Documentation](https://docs.gspread.org/)
- [Google Cloud Console](https://console.cloud.google.com/)

## Support

If you encounter issues:

1. Check logs: `logs/job_finder.log`
2. Verify credentials: `config/google_credentials.json`
3. Test authentication:
   ```python
   from integrations.google_sheets import GoogleSheetsWriter
   writer = GoogleSheetsWriter()
   print(f"Enabled: {writer.is_enabled()}")
   ```

## Example Workflow

Complete workflow from setup to export:

```bash
# 1. Install dependencies
pip install -r requirements-full.txt

# 2. Set up credentials (follow steps above)

# 3. Run job finder with Google Sheets export
python main.py --scrapers remoteok,indeed --top-n 20 --export-sheets

# 4. Open Google Sheets to view results
# URL printed in console output
```

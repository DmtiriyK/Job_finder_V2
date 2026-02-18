"""
Google Sheets integration for exporting job results.

Uses gspread library with Google Service Account authentication.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

import gspread
from google.oauth2.service_account import Credentials

from models.job import Job, ScoreResult
from utils.logger import get_logger


class GoogleSheetsWriter:
    """
    Writer for exporting jobs to Google Sheets with formatting.
    
    Features:
    - Creates or updates spreadsheet
    - 13-column structure
    - Color coding by score (green/yellow/white)
    - Conditional formatting
    - Sortable columns
    """
    
    # Google Sheets API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Column headers (13 columns)
    HEADERS = [
        'Date Found',
        'Title',
        'Company',
        'Location',
        'Remote',
        'Contract',
        'Tech Stack',
        'Score',
        'Breakdown',
        'URL',
        'Source',
        'Applied?',
        'Notes'
    ]
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        spreadsheet_name: Optional[str] = None
    ):
        """
        Initialize Google Sheets writer.
        
        Args:
            credentials_path: Path to service account JSON file
                             (defaults to GOOGLE_CREDENTIALS_PATH env var or config/google_credentials.json)
            spreadsheet_name: Name of spreadsheet to use
                             (defaults to "Job Finder Results")
        """
        self.logger = get_logger('integrations.google_sheets')
        
        # Determine credentials path
        if credentials_path is None:
            credentials_path = os.environ.get(
                'GOOGLE_CREDENTIALS_PATH',
                'config/google_credentials.json'
            )
        
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name or "Job_finder_results"
        
        # Check if credentials exist
        if not os.path.exists(credentials_path):
            self.logger.warning(
                f"Google credentials not found at {credentials_path}. "
                "Google Sheets export will not work. "
                "See docs/GOOGLE_SHEETS_SETUP.md for setup instructions."
            )
            self.client = None
            self.enabled = False
            return
        
        try:
            # Authenticate with service account
            creds = Credentials.from_service_account_file(
                credentials_path,
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(creds)
            self.enabled = True
            self.logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Sheets client: {e}", exc_info=True)
            self.client = None
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if Google Sheets integration is enabled."""
        return self.enabled
    
    def write_jobs(
        self,
        jobs: List[Job],
        scores: Optional[Dict[str, ScoreResult]] = None,
        sheet_name: Optional[str] = None
    ) -> bool:
        """
        Write jobs to Google Sheets.
        
        Args:
            jobs: List of Job objects to write
            scores: Optional dict mapping job IDs to ScoreResult objects
            sheet_name: Optional sheet name (defaults to current date)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            self.logger.warning("Google Sheets integration not enabled")
            return False
        
        if not jobs:
            self.logger.warning("No jobs to write")
            return False
        
        try:
            # Create or get spreadsheet
            spreadsheet = self._get_or_create_spreadsheet()
            
            # Determine sheet name
            if sheet_name is None:
                sheet_name = f"Job Finder - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create or get worksheet
            worksheet = self._get_or_create_worksheet(spreadsheet, sheet_name)
            
            # Clear existing data
            worksheet.clear()
            
            # Write header
            worksheet.append_row(self.HEADERS)
            
            # Format header (bold, freeze)
            self._format_header(worksheet)
            
            # Write job data
            rows = []
            for job in jobs:
                row = self._job_to_row(job, scores)
                rows.append(row)
            
            # Batch write rows (more efficient than append_row in loop)
            if rows:
                worksheet.append_rows(rows)
            
            # Apply formatting
            self._apply_formatting(worksheet, len(jobs), scores)
            
            # Get sheet URL
            sheet_url = spreadsheet.url
            
            self.logger.info(
                f"Successfully wrote {len(jobs)} jobs to Google Sheets: {sheet_url}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write jobs to Google Sheets: {e}", exc_info=True)
            return False
    
    def _get_or_create_spreadsheet(self) -> gspread.Spreadsheet:
        """
        Get or create spreadsheet.
        
        Returns:
            Spreadsheet object
        """
        try:
            # Try to open existing spreadsheet
            spreadsheet = self.client.open(self.spreadsheet_name)
            self.logger.info(f"Opened existing spreadsheet: {self.spreadsheet_name}")
            return spreadsheet
            
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet
            self.logger.info(f"Creating new spreadsheet: {self.spreadsheet_name}")
            spreadsheet = self.client.create(self.spreadsheet_name)
            
            # Share with your email (optional, requires email in env var)
            share_email = os.environ.get('GOOGLE_SHEETS_SHARE_EMAIL')
            if share_email:
                try:
                    spreadsheet.share(share_email, perm_type='user', role='writer')
                    self.logger.info(f"Shared spreadsheet with {share_email}")
                except Exception as e:
                    self.logger.warning(f"Failed to share spreadsheet: {e}")
            
            return spreadsheet
    
    def _get_or_create_worksheet(
        self,
        spreadsheet: gspread.Spreadsheet,
        sheet_name: str
    ) -> gspread.Worksheet:
        """
        Get or create worksheet in spreadsheet.
        
        Args:
            spreadsheet: Spreadsheet object
            sheet_name: Name of worksheet
        
        Returns:
            Worksheet object
        """
        try:
            # Try to get existing worksheet
            worksheet = spreadsheet.worksheet(sheet_name)
            self.logger.info(f"Using existing worksheet: {sheet_name}")
            return worksheet
            
        except gspread.WorksheetNotFound:
            # Create new worksheet
            self.logger.info(f"Creating new worksheet: {sheet_name}")
            worksheet = spreadsheet.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=len(self.HEADERS)
            )
            return worksheet
    
    def _job_to_row(
        self,
        job: Job,
        scores: Optional[Dict[str, ScoreResult]] = None
    ) -> List[str]:
        """
        Convert Job object to spreadsheet row.
        
        Args:
            job: Job object
            scores: Optional dict mapping job IDs to ScoreResult objects
        
        Returns:
            List of strings for row
        """
        # Get score data
        score = None
        breakdown = ""
        
        if scores and job.id in scores:
            score_result = scores[job.id]
            score = score_result.score
            
            # Format breakdown
            components = []
            for comp_name, comp_data in score_result.breakdown.items():
                normalized = comp_data.get('normalized', 0.0)
                components.append(f"{comp_name}:{normalized:.1f}")
            breakdown = ", ".join(components)
        
        # Format tech stack
        tech_stack = ", ".join(job.tech_stack) if job.tech_stack else ""
        
        # Format date
        date_found = job.posted_date.strftime('%Y-%m-%d') if job.posted_date else ""
        
        # Build row
        row = [
            date_found,
            job.title,
            job.company,
            job.location,
            job.remote_type or "",
            job.contract_type or "",
            tech_stack,
            str(score) if score is not None else "",
            breakdown,
            str(job.url),  # Convert HttpUrl to string
            job.source,
            "",  # Applied? (empty checkbox)
            ""   # Notes (empty)
        ]
        
        return row
    
    def _format_header(self, worksheet: gspread.Worksheet):
        """
        Format header row (bold, freeze).
        
        Args:
            worksheet: Worksheet object
        """
        try:
            # Bold header
            worksheet.format('A1:M1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            
            # Freeze header row
            worksheet.freeze(rows=1)
            
        except Exception as e:
            self.logger.warning(f"Failed to format header: {e}")
    
    def _apply_formatting(
        self,
        worksheet: gspread.Worksheet,
        num_jobs: int,
        scores: Optional[Dict[str, ScoreResult]] = None
    ):
        """
        Apply formatting to worksheet.
        
        Args:
            worksheet: Worksheet object
            num_jobs: Number of jobs written
            scores: Optional dict mapping job IDs to ScoreResult objects
        """
        if num_jobs == 0:
            return
        
        try:
            # Color code rows based on score (column H)
            # We need to get all scores first
            score_column = []
            for i in range(2, num_jobs + 2):  # Starting from row 2 (after header)
                cell_value = worksheet.cell(i, 8).value  # Column H (Score)
                try:
                    score = float(cell_value) if cell_value else None
                except:
                    score = None
                score_column.append(score)
            
            # Apply color coding
            for i, score in enumerate(score_column, start=2):
                if score is None:
                    continue
                
                color = self._get_color_for_score(score)
                
                # Format entire row
                row_range = f'A{i}:M{i}'
                worksheet.format(row_range, {
                    'backgroundColor': color
                })
            
            # Auto-resize columns
            self._auto_resize_columns(worksheet)
            
            # Make URLs clickable (they're already clickable in Google Sheets)
            # Just ensure column J has proper width
            
        except Exception as e:
            self.logger.warning(f"Failed to apply formatting: {e}")
    
    def _get_color_for_score(self, score: float) -> Dict[str, float]:
        """
        Get background color for score.
        
        Args:
            score: Job score (0-100)
        
        Returns:
            Dict with RGB values (0-1)
        """
        if score >= 80:
            # Green
            return {'red': 0.85, 'green': 1.0, 'blue': 0.85}
        elif score >= 60:
            # Yellow
            return {'red': 1.0, 'green': 1.0, 'blue': 0.85}
        else:
            # White
            return {'red': 1.0, 'green': 1.0, 'blue': 1.0}
    
    def _auto_resize_columns(self, worksheet: gspread.Worksheet):
        """
        Auto-resize columns to fit content.
        
        Args:
            worksheet: Worksheet object
        """
        try:
            # Set column widths (approximate based on content)
            column_widths = {
                'A': 120,   # Date Found
                'B': 250,   # Title
                'C': 150,   # Company
                'D': 150,   # Location
                'E': 100,   # Remote
                'F': 120,   # Contract
                'G': 200,   # Tech Stack
                'H': 70,    # Score
                'I': 200,   # Breakdown
                'J': 300,   # URL
                'K': 100,   # Source
                'L': 80,    # Applied?
                'M': 200    # Notes
            }
            
            # Apply column widths
            requests = []
            for col_letter, width in column_widths.items():
                col_index = ord(col_letter) - ord('A')
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_index,
                            'endIndex': col_index + 1
                        },
                        'properties': {
                            'pixelSize': width
                        },
                        'fields': 'pixelSize'
                    }
                })
            
            # Batch update
            if requests:
                worksheet.spreadsheet.batch_update({'requests': requests})
                
        except Exception as e:
            self.logger.warning(f"Failed to auto-resize columns: {e}")

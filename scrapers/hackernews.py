"""HackerNews scraper - uses Algolia API to find hiring posts."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re

from scrapers.base import BaseScraper
from models.job import Job


class HackerNewsScraper(BaseScraper):
    """
    Scraper for HackerNews "Who is hiring?" posts via Algolia API.
    
    HackerNews has monthly "Who is hiring?" threads where companies
    post job listings in comments. We use Algolia's HN Search API
    to find recent hiring posts.
    """
    
    ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
    
    # Search query for hiring posts (monthly "Who is hiring?" threads)
    HIRING_QUERY = "Who is hiring"
    
    def __init__(self, **kwargs):
        """Initialize HackerNews scraper."""
        super().__init__(
            name="HackerNews",
            base_url="https://news.ycombinator.com",
            **kwargs
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        max_age_days: int = 60,
        **kwargs
    ) -> List[Job]:
        """
        Fetch jobs from HackerNews hiring threads.
        
        Args:
            keywords: Keywords to filter jobs (applied to title/description)
            location: Location filter (applied to description)
            max_age_days: Maximum age of hiring thread in days
            **kwargs: Additional parameters
        
        Returns:
            List of Job objects
        """
        try:
            # Step 1: Find recent "Who is hiring?" threads
            self.logger.info("Searching for recent HackerNews hiring threads")
            
            hiring_threads = await self._find_hiring_threads(max_age_days)
            
            if not hiring_threads:
                self.logger.warning("No recent hiring threads found")
                return []
            
            self.logger.info(f"Found {len(hiring_threads)} hiring threads")
            
            # Step 2: Fetch comments from each thread
            all_jobs = []
            
            for thread in hiring_threads[:3]:  # Limit to 3 most recent threads
                thread_id = thread.get('objectID')
                thread_title = thread.get('title', 'Unknown')
                
                self.logger.debug(f"Fetching comments from thread: {thread_title}")
                
                try:
                    jobs = await self._fetch_thread_comments(
                        thread_id,
                        thread_title,
                        keywords,
                        location
                    )
                    all_jobs.extend(jobs)
                    
                except Exception as e:
                    self.logger.error(f"Failed to fetch comments from thread {thread_id}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(all_jobs)} jobs from HackerNews")
            return all_jobs
            
        except Exception as e:
            self.logger.error(f"Failed to fetch jobs from HackerNews: {e}", exc_info=True)
            return []
    
    async def _find_hiring_threads(self, max_age_days: int) -> List[Dict[str, Any]]:
        """
        Find recent "Who is hiring?" threads using Algolia API.
        
        Args:
            max_age_days: Maximum age of threads in days
        
        Returns:
            List of thread objects
        """
        try:
            # Calculate timestamp for max age
            min_timestamp = int((datetime.now() - timedelta(days=max_age_days)).timestamp())
            
            # Search for hiring threads
            params = {
                "query": self.HIRING_QUERY,
                "tags": "story",  # Only top-level posts
                "numericFilters": f"created_at_i>{min_timestamp}",
                "hitsPerPage": 10
            }
            
            response = await self._fetch_url(self.ALGOLIA_URL, params=params)
            data = response.json()
            
            hits = data.get('hits', [])
            
            # Filter for actual hiring threads (title contains "hiring")
            hiring_threads = [
                hit for hit in hits
                if 'hiring' in hit.get('title', '').lower()
                and hit.get('num_comments', 0) > 10  # At least 10 comments
            ]
            
            return hiring_threads
            
        except Exception as e:
            self.logger.error(f"Failed to find hiring threads: {e}", exc_info=True)
            return []
    
    async def _fetch_thread_comments(
        self,
        thread_id: str,
        thread_title: str,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None
    ) -> List[Job]:
        """
        Fetch and parse comments from a hiring thread.
        
        Args:
            thread_id: Thread object ID
            thread_title: Thread title
            keywords: Keywords to filter jobs
            location: Location filter
        
        Returns:
            List of Job objects
        """
        try:
            # Fetch thread item (includes comments)
            url = f"https://hn.algolia.com/api/v1/items/{thread_id}"
            response = await self._fetch_url(url)
            data = response.json()
            
            comments = data.get('children', [])
            
            if not comments:
                self.logger.warning(f"No comments found in thread {thread_id}")
                return []
            
            self.logger.debug(f"Found {len(comments)} comments in thread")
            
            jobs = []
            
            # Parse each top-level comment as potential job posting
            for comment in comments[:100]:  # Limit to first 100 comments
                try:
                    job = self._parse_comment(comment, thread_title)
                    
                    if job is None:
                        continue
                    
                    # Apply filters
                    if keywords and not self._matches_keywords(job, keywords):
                        continue
                    
                    if location and not self._matches_location(job, location):
                        continue
                    
                    jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse comment: {e}", exc_info=True)
                    continue
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to fetch thread comments: {e}", exc_info=True)
            return []
    
    def _parse_comment(self, comment: Dict[str, Any], thread_title: str) -> Optional[Job]:
        """
        Parse hiring comment into Job model.
        
        Args:
            comment: Comment object from Algolia API
            thread_title: Title of hiring thread
        
        Returns:
            Job object or None if parsing failed
        """
        try:
            # Extract comment text
            text = comment.get('text', '').strip()
            
            if not text or len(text) < 50:
                # Too short to be a real job posting
                return None
            
            # Parse company name (usually first line, often starts with company name)
            # Common patterns: "Company Name | Position | Location"
            lines = text.split('\n')
            first_line = lines[0].strip() if lines else ''
            
            # Try to extract company and title from first line
            company, title = self._parse_first_line(first_line)
            
            if not company:
                company = "Unknown"
            
            if not title:
                title = "Software Engineer"  # Default title
            
            # Extract location (look for common patterns)
            location = self._extract_location(text)
            
            # Determine if remote
            remote_type = self._determine_remote_type(text)
            
            # Extract URL (look for application links)
            url = self._extract_url(comment, text)
            
            # Posted date
            created_at = comment.get('created_at_i')
            if created_at:
                posted_date = datetime.fromtimestamp(created_at)
            else:
                posted_date = datetime.now()
            
            # Generate unique ID
            comment_id = comment.get('objectID', comment.get('id', ''))
            job_id = Job.generate_id(
                url=url or f"https://news.ycombinator.com/item?id={comment_id}",
                title=title
            )
            
            # Create Job object
            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url or f"https://news.ycombinator.com/item?id={comment_id}",
                description=text[:1000],  # Limit description length
                posted_date=posted_date,
                source=self.name,
                source_id=comment_id,
                tech_stack=[],  # Will be extracted later
                salary_min=None,
                salary_max=None,
                contract_type=None
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to parse comment: {e}", exc_info=True)
            return None
    
    def _parse_first_line(self, line: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse company and title from first line.
        
        Common formats:
        - "Company | Title | Location"
        - "Company - Title - Location"
        - "Company: Title"
        
        Args:
            line: First line of comment
        
        Returns:
            Tuple of (company, title)
        """
        company = None
        title = None
        
        # Try to split by common delimiters
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                company = parts[0]
                title = parts[1]
        elif '-' in line and line.count('-') >= 2:
            parts = [p.strip() for p in line.split('-')]
            if len(parts) >= 2:
                company = parts[0]
                title = parts[1]
        elif ':' in line:
            parts = [p.strip() for p in line.split(':', 1)]
            if len(parts) == 2:
                company = parts[0]
                title = parts[1]
        else:
            # Fallback: use whole line as company
            company = line[:50]  # Limit length
        
        return company, title
    
    def _extract_location(self, text: str) -> str:
        """
        Extract location from job text.
        
        Args:
            text: Job description text
        
        Returns:
            Location string
        """
        text_lower = text.lower()
        
        # Common location patterns
        location_patterns = [
            r'location[:\s]+([^|\n]+)',
            r'\|([^|\n]*(?:remote|onsite|hybrid)[^|\n]*)\|',
            r'based in ([^|\n,\.]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).strip()[:50]
        
        # Default
        return "Remote"
    
    def _determine_remote_type(self, text: str) -> str:
        """
        Determine remote work type from text.
        
        Args:
            text: Job description text
        
        Returns:
            Remote type string
        """
        text_lower = text.lower()
        
        if 'remote' in text_lower:
            if 'no remote' in text_lower or 'not remote' in text_lower:
                return "Onsite"
            elif 'remote ok' in text_lower or 'remote-ok' in text_lower:
                return "Hybrid"
            else:
                return "Remote"
        elif 'onsite' in text_lower:
            return "Onsite"
        else:
            return "Onsite"  # Conservative default
    
    def _extract_url(self, comment: Dict[str, Any], text: str) -> Optional[str]:
        """
        Extract application URL from comment.
        
        Args:
            comment: Comment object
            text: Comment text
        
        Returns:
            URL string or None
        """
        # Look for URLs in text
        url_pattern = r'https?://[^\s<>"\']+'
        matches = re.findall(url_pattern, text)
        
        if matches:
            # Return first URL
            return matches[0]
        
        return None
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse raw job data into Job model.
        
        For HackerNews, we use _parse_comment() instead.
        This method is here for BaseScraper compatibility.
        
        Args:
            raw_data: Raw job data
        
        Returns:
            Job object or None
        """
        # Not used for HackerNews (we parse comments directly)
        return None
    
    def _matches_keywords(self, job: Job, keywords: List[str]) -> bool:
        """Check if job matches any keywords."""
        searchable = f"{job.title} {job.description} {job.company}".lower()
        return any(keyword.lower() in searchable for keyword in keywords)
    
    def _matches_location(self, job: Job, location: str) -> bool:
        """Check if job matches location."""
        job_location = f"{job.location} {job.remote_type}".lower()
        return location.lower() in job_location

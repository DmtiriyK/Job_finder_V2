"""RemoteOK scraper - parses RSS feed for remote jobs."""

import feedparser
from typing import List, Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.job import Job


class RemoteOKScraper(BaseScraper):
    """
    Scraper for RemoteOK.com RSS feed.
    
    RemoteOK provides a simple RSS feed with job postings.
    """
    
    RSS_URL = "https://remoteok.com/remote-jobs.rss"
    
    def __init__(self, **kwargs):
        """Initialize RemoteOK scraper."""
        super().__init__(
            name="RemoteOK",
            base_url="https://remoteok.com",
            **kwargs
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        **kwargs
    ) -> List[Job]:
        """
        Fetch jobs from RemoteOK RSS feed.
        
        Args:
            keywords: Keywords to filter jobs (applied to title/description)
            location: Location filter (RemoteOK is remote-first, so mostly ignored)
            **kwargs: Additional parameters
        
        Returns:
            List of Job objects
        """
        try:
            # Fetch RSS feed
            response = await self._fetch_url(self.RSS_URL)
            
            # Parse RSS
            feed_content = response.text
            feed = feedparser.parse(feed_content)
            
            if not feed.entries:
                self.logger.warning("No jobs found in RSS feed")
                return []
            
            self.logger.info(f"Found {len(feed.entries)} jobs in RSS feed")
            
            # Parse each job
            jobs = []
            for entry in feed.entries:
                try:
                    job = self.parse_job(entry)
                    
                    if job is None:
                        continue
                    
                    # Apply keyword filter
                    if keywords and not self._matches_keywords(job, keywords):
                        continue
                    
                    jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse job entry: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Successfully parsed {len(jobs)} jobs from RemoteOK")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to fetch jobs from RemoteOK: {e}", exc_info=True)
            return []
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse RSS entry into Job model.
        
        Args:
            raw_data: RSS entry from feedparser
        
        Returns:
            Job object or None if parsing failed
        """
        try:
            # Extract basic fields
            title = raw_data.get('title', '').strip()
            url = raw_data.get('link', '').strip()
            
            if not title or not url:
                self.logger.warning("Missing title or URL in RSS entry")
                return None
            
            # Extract description (HTML content)
            description = ''
            if 'summary' in raw_data:
                # Parse HTML and extract text
                soup = BeautifulSoup(raw_data['summary'], 'html.parser')
                description = soup.get_text(separator=' ', strip=True)
            
            # Extract published date
            posted_date = datetime.now()
            if 'published_parsed' in raw_data and raw_data['published_parsed']:
                try:
                    import time
                    posted_date = datetime.fromtimestamp(time.mktime(raw_data['published_parsed']))
                except Exception as e:
                    self.logger.warning(f"Failed to parse date: {e}")
            
            # Extract company from RSS field or fallback to parsing title
            company = raw_data.get('company', '').strip()
            if not company:
                # Fallback: try to parse from title (format: "Company: Job Title")
                if ':' in title:
                    parts = title.split(':', 1)
                    company = parts[0].strip()
                    title = parts[1].strip()
                else:
                    company = "Unknown"
            
            # Extract location from RSS field
            location = raw_data.get('location', '').strip()
            if not location:
                location = "Remote"  # RemoteOK is remote-first
            
            # Extract tags (tech stack)
            tags = []
            if 'tags' in raw_data:
                tags = [tag.get('term', '') for tag in raw_data.get('tags', [])]
            
            # Generate unique ID
            job_id = Job.generate_id(url=url, title=title)
            
            # Create Job object
            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location,
                remote_type="Full Remote",  # RemoteOK is remote-first
                url=url,
                description=description or "No description available",
                posted_date=posted_date,
                source=self.name,
                source_id=url,  # Use URL as source ID
                tech_stack=tags if tags else None,
                salary_min=None,
                salary_max=None,
                contract_type=None
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to parse job: {e}", exc_info=True)
            return None
    
    def _matches_keywords(self, job: Job, keywords: List[str]) -> bool:
        """
        Check if job matches any of the keywords.
        
        Args:
            job: Job object
            keywords: List of keywords
        
        Returns:
            True if job matches any keyword
        """
        # Combine searchable fields
        searchable = f"{job.title} {job.description} {' '.join(job.tech_stack or [])}".lower()
        
        # Check if any keyword matches
        return any(keyword.lower() in searchable for keyword in keywords)

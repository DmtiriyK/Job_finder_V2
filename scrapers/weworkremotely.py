"""WeWorkRemotely scraper - parses RSS feed for remote jobs."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET
from html import unescape
import re

from scrapers.base import BaseScraper
from models.job import Job


class WeWorkRemotelyScraper(BaseScraper):
    """
    Scraper for WeWorkRemotely.com using RSS feed.
    
    WeWorkRemotely provides a comprehensive RSS feed with all remote jobs.
    RSS Feed: https://weworkremotely.com/remote-jobs.rss
    """
    
    BASE_URL = "https://weworkremotely.com"
    RSS_URL = "https://weworkremotely.com/remote-jobs.rss"
    
    def __init__(self, **kwargs):
        """Initialize WeWorkRemotely scraper."""
        super().__init__(
            name="WeWorkRemotely",
            base_url=self.BASE_URL,
            **kwargs
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        **kwargs
    ) -> List[Job]:
        """
        Fetch jobs from WeWorkRemotely RSS feed.
        
        Args:
            keywords: Keywords to filter jobs (applied to title/description)
            location: Location filter (optional, for filtering results)
            **kwargs: Additional parameters
        
        Returns:
            List of Job objects
        """
        try:
            self.logger.info("Fetching jobs from WeWorkRemotely RSS feed")
            
            # Rate limiting
            await self.rate_limiter.async_wait()
            
            # Fetch RSS feed
            response = await self._fetch_url(self.RSS_URL)
            xml_content = response.text
            
            # Parse XML
            jobs = self._parse_rss_feed(xml_content)
            
            # Apply filters
            if keywords:
                jobs = [j for j in jobs if self._matches_keywords(j, keywords)]
            
            if location:
                jobs = [j for j in jobs if self._matches_location(j, location)]
            
            self.logger.info(f"WeWorkRemotely: Found {len(jobs)} jobs")
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to fetch jobs from WeWorkRemotely: {e}", exc_info=True)
            return []
    
    def _parse_rss_feed(self, xml_content: str) -> List[Job]:
        """
        Parse WeWorkRemotely RSS feed XML.
        
        Args:
            xml_content: RSS feed XML string
        
        Returns:
            List of Job objects
        """
        jobs = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all job items in the feed
            for item in root.findall(".//item"):
                try:
                    job = self._parse_rss_item(item)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    self.logger.debug(f"Error parsing RSS item: {e}")
                    continue
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
        
        return jobs
    
    def _parse_rss_item(self, item: ET.Element) -> Optional[Job]:
        """
        Parse a single RSS item into a Job object.
        
        RSS item structure:
        <item>
          <title>Company: Job Title (Remote, Location)</title>
          <link>URL</link>
          <region>Location</region>
          <category>Category</category>
          <type>Full-Time/Contract/Part-Time</type>
          <description>HTML description</description>
          <pubDate>Date</pubDate>
        </item>
        
        Args:
            item: XML Element representing a job item
        
        Returns:
            Job object or None if parsing fails
        """
        try:
            # Extract fields from RSS item
            title_elem = item.find("title")
            link_elem = item.find("link")
            region_elem = item.find("region")
            category_elem = item.find("category")
            type_elem = item.find("type")
            description_elem = item.find("description")
            pubdate_elem = item.find("pubDate")
            
            if title_elem is None or link_elem is None:
                return None
            
            # Parse title: "Company: Job Title (Info)"
            full_title = unescape(title_elem.text or "").strip()
            url = link_elem.text or ""
            
            # Split title into company and job title
            company, job_title = self._parse_title(full_title)
            
            # Location
            location = unescape(region_elem.text or "Worldwide").strip() if region_elem is not None and region_elem.text else "Worldwide"
            
            # Category
            category = unescape(category_elem.text or "").strip() if category_elem is not None and category_elem.text else ""
            
            # Contract type
            contract_type = unescape(type_elem.text or "").strip() if type_elem is not None and type_elem.text else None
            
            # Description (contains HTML, clean it)
            description = ""
            if description_elem is not None and description_elem.text:
                description = self._clean_html(description_elem.text)
            
            # Posted date
            posted_date = datetime.now()
            if pubdate_elem is not None and pubdate_elem.text:
                try:
                    parsed_date = datetime.strptime(
                        pubdate_elem.text.strip(),
                        "%a, %d %b %Y %H:%M:%S %z"
                    )
                    # Remove timezone info to make it naive (compatible with datetime.now())
                    posted_date = parsed_date.replace(tzinfo=None)
                except:
                    pass
            
            # Remote type (WeWorkRemotely is remote-only by nature)
            remote_type = "Remote"
            
            # Generate unique ID
            job_id = f"wwr_{hash(url) % 1000000000}"
            
            # Create Job object
            job = Job(
                id=job_id,
                title=job_title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url,
                description=description or f"{job_title} at {company}. Category: {category}.",
                posted_date=posted_date,
                source="WeWorkRemotely",
                contract_type=contract_type
            )
            
            return job
            
        except Exception as e:
            self.logger.debug(f"Error parsing RSS item: {e}")
            return None
    
    def _parse_title(self, full_title: str) -> tuple:
        """
        Parse WeWorkRemotely title format: "Company: Job Title (Extra Info)".
        
        Args:
            full_title: Full RSS item title
        
        Returns:
            Tuple of (company, job_title)
        """
        # Remove extra info in parentheses
        title_cleaned = re.sub(r'\([^)]+\)', '', full_title).strip()
        
        # Split by colon
        if ': ' in title_cleaned:
            parts = title_cleaned.split(': ', 1)
            company = parts[0].strip()
            job_title = parts[1].strip()
        else:
            company = "Unknown Company"
            job_title = title_cleaned
        
        return company, job_title
    
    def _clean_html(self, html_text: str) -> str:
        """
        Remove HTML tags and clean description text.
        
        Args:
            html_text: Text potentially containing HTML
        
        Returns:
            Clean text
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html_text)
        
        # Unescape HTML entities
        text = unescape(text)
        
        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        return text
    
    def _matches_keywords(self, job: Job, keywords: List[str]) -> bool:
        """
        Check if job matches any of the keywords.
        
        Args:
            job: Job object
            keywords: List of keywords
        
        Returns:
            True if job matches any keyword
        """
        searchable = f"{job.title} {job.description} {job.company}".lower()
        return any(keyword.lower() in searchable for keyword in keywords)
    
    def _matches_location(self, job: Job, location: str) -> bool:
        """
        Check if job matches location filter.
        
        Args:
            job: Job object
            location: Location string to match
        
        Returns:
            True if job matches location
        """
        job_location = job.location.lower()
        location_check = location.lower()
        
        # Match if location is in job location or vice versa
        return location_check in job_location or job_location in location_check or job_location == "worldwide"
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse raw job data into Job model.
        
        For WeWorkRemotely, we use RSS parsing instead.
        This method is here for BaseScraper compatibility.
        
        Args:
            raw_data: Raw job data
        
        Returns:
            Job object or None
        """
        return None

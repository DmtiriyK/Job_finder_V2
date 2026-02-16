"""
Indeed RSS feed scraper for job listings.

Indeed provides RSS feeds for job searches. No API key required.
RSS Feed Format: https://de.indeed.com/rss?q={keywords}&l={location}
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET
from html import unescape
import re

from scrapers.base import BaseScraper
from models.job import Job


class IndeedScraper(BaseScraper):
    """
    Scraper for Indeed using RSS feeds.
    
    Features:
    - No API key required
    - RSS feed access (freely available)
    - Search by keywords and location
    - Returns basic job information
    
    Limitations:
    - RSS feeds may have limited results (~25 jobs per feed)
    - Description field is often truncated
    - No salary information in RSS
    """
    
    def __init__(
        self,
        country_domain: str = "de",  # de, com, co.uk, etc.
        max_results: int = 100
    ):
        """
        Initialize Indeed scraper.
        
        Args:
            country_domain: Indeed country domain (de=Germany, com=USA, co.uk=UK)
            max_results: Maximum number of jobs to return
        """
        base_url = f"https://{country_domain}.indeed.com"
        super().__init__(
            name="Indeed",
            base_url=base_url,
            timeout=15.0,
            max_retries=2
        )
        
        self.country_domain = country_domain
        self.max_results = max_results
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: str = "Deutschland"
    ) -> List[Job]:
        """
        Fetch jobs from Indeed RSS feeds.
        
        Args:
            keywords: Search keywords (e.g., ["Full Stack", "Backend"])
            location: Location filter (e.g., "Berlin", "München", "Deutschland")
        
        Returns:
            List of Job objects
        """
        jobs = []
        
        # If keywords provided, search each keyword separately
        # Otherwise, use default tech stack keywords
        keyword_list = keywords or [
            "Full Stack Engineer",
            "Backend Developer",
            "DevOps Engineer"
        ]
        
        self.logger.info(
            f"Searching Indeed ({self.country_domain}) in {location} "
            f"for {len(keyword_list)} keyword(s)"
        )
        
        for keyword in keyword_list:
            try:
                keyword_jobs = await self._fetch_rss_feed(
                    keywords=keyword,
                    location=location
                )
                
                jobs.extend(keyword_jobs)
                
                self.logger.debug(
                    f"Keyword '{keyword}': {len(keyword_jobs)} jobs found"
                )
                
                # Stop if we have enough jobs
                if len(jobs) >= self.max_results:
                    break
                
            except Exception as e:
                self.logger.error(f"Error fetching '{keyword}': {e}")
                continue
        
        # Remove duplicates by ID
        unique_jobs = {}
        for job in jobs:
            if job.id not in unique_jobs:
                unique_jobs[job.id] = job
        
        jobs = list(unique_jobs.values())[:self.max_results]
        
        self.logger.info(f"Indeed: Found {len(jobs)} unique jobs total")
        return jobs
    
    async def _fetch_rss_feed(
        self,
        keywords: str,
        location: str
    ) -> List[Job]:
        """
        Fetch jobs from a single Indeed RSS feed.
        
        Args:
            keywords: Search keywords string
            location: Location filter
        
        Returns:
            List of Job objects
        """
        # Build RSS feed URL
        # Format: https://de.indeed.com/rss?q=Full+Stack+Engineer&l=Berlin
        rss_url = (
            f"{self.base_url}/rss"
            f"?q={keywords.replace(' ', '+')}"
            f"&l={location.replace(' ', '+')}"
        )
        
        self.logger.debug(f"Fetching RSS: {rss_url}")
        
        # Rate limiting
        await self.rate_limiter.wait()
        
        # Fetch RSS feed
        client = await self._get_client()
        response = await client.get(rss_url)
        response.raise_for_status()
        
        # Parse XML
        xml_content = response.text
        jobs = self._parse_rss_feed(xml_content, keywords)
        
        return jobs
    
    def _parse_rss_feed(self, xml_content: str, search_keywords: str) -> List[Job]:
        """
        Parse Indeed RSS feed XML.
        
        Args:
            xml_content: RSS feed XML string
            search_keywords: Original search keywords (for context)
        
        Returns:
            List of Job objects
        """
        jobs = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all job items in the feed
            # RSS format: <rss><channel><item>...</item></channel></rss>
            for item in root.findall(".//item"):
                try:
                    job = self._parse_rss_item(item, search_keywords)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    self.logger.debug(f"Error parsing RSS item: {e}")
                    continue
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
        
        return jobs
    
    def _parse_rss_item(self, item: ET.Element, search_keywords: str) -> Optional[Job]:
        """
        Parse a single RSS item into a Job object.
        
        Args:
            item: XML Element representing a job item
            search_keywords: Original search keywords
        
        Returns:
            Job object or None if parsing fails
        """
        try:
            # Extract fields from RSS item
            title_elem = item.find("title")
            link_elem = item.find("link")
            description_elem = item.find("description")
            pubdate_elem = item.find("pubDate")
            
            if title_elem is None or link_elem is None:
                return None
            
            title = unescape(title_elem.text or "").strip()
            url = link_elem.text or ""
            
            # Extract description (may contain HTML)
            description = ""
            if description_elem is not None and description_elem.text:
                description = self._clean_html(description_elem.text)
            
            # Parse title to extract company and location
            # Format often: "Job Title - Company Name - Location"
            company, location = self._parse_title_for_company_location(title)
            
            # Clean title (remove company and location if present)
            clean_title = self._clean_title(title, company, location)
            
            # Parse posted date
            posted_date = datetime.now()
            if pubdate_elem is not None and pubdate_elem.text:
                try:
                    # RSS pubDate format: "Wed, 15 Feb 2025 10:30:00 GMT"
                    posted_date = datetime.strptime(
                        pubdate_elem.text,
                        "%a, %d %b %Y %H:%M:%S %Z"
                    )
                except:
                    pass
            
            # Determine remote type
            remote_type = self._determine_remote_type(title, description)
            
            # Extract job ID from URL
            job_id = self._extract_job_id(url)
            
            # Create Job object
            job = Job(
                id=f"indeed_{job_id}",
                title=clean_title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url,
                description=description or f"Job posting for {clean_title} at {company}. Keywords: {search_keywords}",
                posted_date=posted_date,
                source="Indeed"
            )
            
            return job
            
        except Exception as e:
            self.logger.debug(f"Error parsing RSS item: {e}")
            return None
    
    def _parse_title_for_company_location(self, title: str) -> tuple:
        """
        Extract company and location from Indeed RSS title.
        
        Indeed RSS titles often follow format:
        "Job Title - Company Name - City, Country"
        
        Args:
            title: Full RSS item title
        
        Returns:
            Tuple of (company, location)
        """
        parts = [p.strip() for p in title.split(" - ")]
        
        company = "Unknown Company"
        location = "Unknown Location"
        
        if len(parts) >= 3:
            # Last part is often location
            location = parts[-1]
            # Second-to-last is often company
            company = parts[-2]
        elif len(parts) == 2:
            # Assume: "Job Title - Company"
            company = parts[-1]
        
        return company, location
    
    def _clean_title(self, title: str, company: str, location: str) -> str:
        """
        Clean job title by removing company and location.
        
        Args:
            title: Full title string
            company: Extracted company name
            location: Extracted location
        
        Returns:
            Cleaned title
        """
        # Remove company and location from title
        clean = title
        
        if company != "Unknown Company":
            clean = clean.replace(f" - {company}", "")
        
        if location != "Unknown Location":
            clean = clean.replace(f" - {location}", "")
        
        return clean.strip()
    
    def _extract_job_id(self, url: str) -> str:
        """
        Extract job ID from Indeed URL.
        
        Indeed URLs contain job IDs like:
        https://de.indeed.com/viewjob?jk=abc123def456
        
        Args:
            url: Indeed job URL
        
        Returns:
            Job ID string
        """
        # Look for jk= parameter in URL
        match = re.search(r"jk=([a-f0-9]+)", url)
        if match:
            return match.group(1)
        
        # Fallback: use hash of URL
        return str(hash(url))[-10:]
    
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
    
    def _determine_remote_type(self, title: str, description: str) -> str:
        """
        Determine remote work type from job details.
        
        Args:
            title: Job title
            description: Job description
        
        Returns:
            Remote type string
        """
        text = f"{title} {description}".lower()
        
        # Check for remote indicators
        remote_keywords = [
            "remote", "work from home", "wfh", "distributed",
            "telecommute", "home office", "homeoffice"
        ]
        
        if any(keyword in text for keyword in remote_keywords):
            # Check for hybrid
            if "hybrid" in text:
                return "Hybrid"
            return "Remote"
        
        return "Onsite"    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse job from raw data.
        
        Note: Indeed scraper uses RSS feed parsing internally,
        so this method is not used directly.
        
        Args:
            raw_data: Raw job data dictionary
        
        Returns:
            Job object or None
        """
        self.logger.warning("parse_job() called on Indeed scraper - use fetch_jobs() instead")
        return None    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

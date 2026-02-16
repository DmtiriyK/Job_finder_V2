"""
StepStone HTML scraper for job listings.

StepStone (www.stepstone.de) is one of the largest job boards in Germany.
This scraper uses HTML parsing to extract job listings from search results.

Note: StepStone uses JavaScript rendering, so results may be limited without
a headless browser (Playwright/Selenium). This scraper attempts HTML-only parsing first.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.job import Job


class StepStoneScraper(BaseScraper):
    """
    Scraper for StepStone using HTML parsing.
    
    Features:
    - Search by keywords and location
    - HTML parsing with BeautifulSoup
    - Extracts job title, company, location, description preview
    
    Limitations:
    - StepStone heavily uses JavaScript, so results may be limited
    - Some content may not be available without JS rendering
    - Consider using Playwright for better results (future enhancement)
    
    Future Enhancement:
    - Add Playwright support for JavaScript rendering
    - Handle pagination more robustly
    - Extract salary information when available
    """
    
    def __init__(
        self,
        max_pages: int = 3,
        results_per_page: int = 25
    ):
        """
        Initialize StepStone scraper.
        
        Args:
            max_pages: Maximum number of pages to scrape
            results_per_page: Results per page (StepStone default is 25)
        """
        super().__init__(
            name="StepStone",
            base_url="https://www.stepstone.de",
            timeout=20.0,
            max_retries=2
        )
        
        self.max_pages = max_pages
        self.results_per_page = results_per_page
        
        # Log JavaScript limitation warning
        self.logger.info(
            "StepStone scraper initialized. Note: StepStone uses JavaScript rendering. "
            "Results may be limited without Playwright/Selenium."
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: str = "Deutschland"
    ) -> List[Job]:
        """
        Fetch jobs from StepStone.
        
        Args:
            keywords: Search keywords (e.g., ["Full Stack", "Backend"])
            location: Location filter (e.g., "Berlin", "München", "Deutschland")
        
        Returns:
            List of Job objects
        """
        jobs = []
        
        # Build search query
        search_query = " ".join(keywords) if keywords else "Full Stack Backend Developer"
        
        self.logger.info(
            f"Searching StepStone in {location} for: {search_query} "
            f"(max {self.max_pages} pages)"
        )
        
        for page in range(1, self.max_pages + 1):
            try:
                page_jobs = await self._fetch_page(
                    keywords=search_query,
                    location=location,
                    page=page
                )
                
                jobs.extend(page_jobs)
                
                self.logger.debug(
                    f"Page {page}/{self.max_pages}: {len(page_jobs)} jobs found"
                )
                
                # Stop if no results on this page
                if len(page_jobs) == 0:
                    break
                
            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                continue
        
        self.logger.info(f"StepStone: Found {len(jobs)} jobs total")
        return jobs
    
    async def _fetch_page(
        self,
        keywords: str,
        location: str,
        page: int
    ) -> List[Job]:
        """
        Fetch a single page of search results.
        
        Args:
            keywords: Search keywords string
            location: Location filter
            page: Page number (1-indexed)
        
        Returns:
            List of Job objects
        """
        # Build search URL
        # StepStone URL format: /jobs/{keywords}/in-{location}?page={page}
        keywords_slug = keywords.lower().replace(" ", "-")
        location_slug = location.lower().replace(" ", "-")
        
        search_url = (
            f"{self.base_url}/jobs/{keywords_slug}/in-{location_slug}"
            f"?page={page}"
        )
        
        self.logger.debug(f"Fetching: {search_url}")
        
        # Rate limiting
        await self.rate_limiter.wait()
        
        # Fetch page
        client = await self._get_client()
        response = await client.get(search_url)
        
        # Check response
        if response.status_code == 404:
            self.logger.warning(f"Page {page} returned 404, no more results")
            return []
        
        response.raise_for_status()
        
        # Parse HTML
        html_content = response.text
        jobs = self._parse_search_results(html_content, keywords)
        
        return jobs
    
    def _parse_search_results(self, html_content: str, search_keywords: str) -> List[Job]:
        """
        Parse StepStone search results HTML.
        
        Args:
            html_content: HTML page content
            search_keywords: Original search keywords
        
        Returns:
            List of Job objects
        """
        soup = BeautifulSoup(html_content, "html.parser")
        jobs = []
        
        # Try to find job listing containers
        # StepStone uses various class names, try multiple selectors
        job_containers = []
        
        # Common StepStone selectors (may change over time)
        selectors = [
            "article[data-at='job-item']",  # Main job item
            "div.job-element",              # Alternative
            "article.listing",              # Alternative
            "div.resultlist-item"           # Alternative
        ]
        
        for selector in selectors:
            job_containers = soup.select(selector)
            if job_containers:
                self.logger.debug(f"Found {len(job_containers)} jobs using selector: {selector}")
                break
        
        if not job_containers:
            self.logger.warning(
                "Could not find job containers in HTML. "
                "StepStone may have changed their HTML structure or requires JavaScript rendering."
            )
            return []
        
        # Parse each job container
        for container in job_containers:
            try:
                job = self._parse_job_container(container, search_keywords)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Error parsing job container: {e}")
                continue
        
        return jobs
    
    def _parse_job_container(
        self,
        container: BeautifulSoup,
        search_keywords: str
    ) -> Optional[Job]:
        """
        Parse a single job listing container.
        
        Args:
            container: BeautifulSoup element containing job listing
            search_keywords: Original search keywords
        
        Returns:
            Job object or None if parsing fails
        """
        try:
            # Extract title
            title_elem = (
                container.select_one("h2 a") or
                container.select_one(".job-element-title a") or
                container.select_one("a[data-at='job-item-title']")
            )
            
            if not title_elem:
                return None
            
            title = title_elem.text.strip()
            url = title_elem.get("href", "")
            
            # Make URL absolute if relative
            if url and not url.startswith("http"):
                url = f"{self.base_url}{url}"
            
            # Extract company
            company_elem = (
                container.select_one(".job-element-company") or
                container.select_one("div[data-at='job-item-company']") or
                container.select_one(".company-name")
            )
            
            company = company_elem.text.strip() if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = (
                container.select_one(".job-element-location") or
                container.select_one("div[data-at='job-item-location']") or
                container.select_one(".location")
            )
            
            location = location_elem.text.strip() if location_elem else "Deutschland"
            
            # Extract description preview (if available)
            description_elem = (
                container.select_one(".job-element-description") or
                container.select_one("div[data-at='job-item-snippet']") or
                container.select_one(".snippet")
            )
            
            description = (
                description_elem.text.strip()
                if description_elem
                else f"Job posting for {title} at {company}. Search keywords: {search_keywords}"
            )
            
            # Extract job ID from URL
            job_id = self._extract_job_id(url)
            
            # Determine remote type
            remote_type = self._determine_remote_type(title, description, location)
            
            # Posted date (StepStone doesn't always show, use current time)
            posted_date = datetime.now() - timedelta(days=1)  # Assume posted yesterday
            
            # Create Job object
            job = Job(
                id=f"stepstone_{job_id}",
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url,
                description=description,
                posted_date=posted_date,
                source="StepStone"
            )
            
            return job
            
        except Exception as e:
            self.logger.debug(f"Error parsing job container: {e}")
            return None
    
    def _extract_job_id(self, url: str) -> str:
        """
        Extract job ID from StepStone URL.
        
        StepStone URLs typically contain numeric IDs.
        
        Args:
            url: StepStone job URL
        
        Returns:
            Job ID string
        """
        # Look for numeric ID in URL
        match = re.search(r"/(\d+)/", url)
        if match:
            return match.group(1)
        
        # Fallback: use hash of URL
        return str(hash(url))[-10:]
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse job from raw data.
        
        Note: StepStone scraper uses HTML parsing internally,
        so this method is not used directly.
        
        Args:
            raw_data: Raw job data dictionary
        
        Returns:
            Job object or None
        """
        self.logger.warning("parse_job() called on StepStone scraper - use fetch_jobs() instead")
        return None
    
    def _determine_remote_type(
        self,
        title: str,
        description: str,
        location: str
    ) -> str:
        """
        Determine remote work type from job details.
        
        Args:
            title: Job title
            description: Job description
            location: Job location
        
        Returns:
            Remote type string
        """
        text = f"{title} {description} {location}".lower()
        
        # Check for remote indicators
        remote_keywords = [
            "remote", "homeoffice", "home office", "home-office",
            "von zu hause", "deutschlandweit", "ortsunabhängig"
        ]
        
        if any(keyword in text for keyword in remote_keywords):
            # Check for hybrid
            if "hybrid" in text or "teilweise" in text:
                return "Hybrid"
            return "Remote"
        
        return "Onsite"
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

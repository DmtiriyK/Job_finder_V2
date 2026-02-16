"""
XING HTML scraper for job listings.

XING (www.xing.com/jobs) is a professional networking platform popular in
Germany, Austria, and Switzerland - similar to LinkedIn but focused on DACH region.

This scraper uses HTML parsing to extract job listings from search results.

Note: XING requires authentication for many features and uses heavy JavaScript
rendering. This scraper attempts HTML-only parsing with limited results.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re
from urllib.parse import urlencode, quote

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.job import Job


class XINGScraper(BaseScraper):
    """
    Scraper for XING Jobs using HTML parsing.
    
    Features:
    - Search XING job listings
    - HTML parsing with BeautifulSoup
    - Extracts job title, company, location
    
    Limitations:
    - XING requires authentication for full access
    - Heavy JavaScript rendering limits HTML-only scraping
    - Some job details require login
    - Consider using Playwright for better results (future enhancement)
    
    Alternative Approach:
    - XING has an API but requires partnership/authentication
    - Playwright could handle JavaScript rendering
    - Focus on public job listings that don't require login
    """
    
    def __init__(
        self,
        max_pages: int = 3,
        results_per_page: int = 20
    ):
        """
        Initialize XING scraper.
        
        Args:
            max_pages: Maximum number of pages to scrape
            results_per_page: Results per page (XING default varies)
        """
        super().__init__(
            name="XING",
            base_url="https://www.xing.com",
            timeout=20.0,
            max_retries=2
        )
        
        self.max_pages = max_pages
        self.results_per_page = results_per_page
        
        # Log JavaScript/auth limitation warning
        self.logger.info(
            "XING scraper initialized. Note: XING requires authentication for full access "
            "and uses JavaScript rendering. Results may be very limited."
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: str = "Deutschland"
    ) -> List[Job]:
        """
        Fetch jobs from XING.
        
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
            f"Searching XING in {location} for: {search_query} "
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
        
        # Note: Due to XING's authentication requirements, we may get 0 results
        if len(jobs) == 0:
            self.logger.warning(
                "XING returned 0 jobs. This is expected as XING requires authentication "
                "for most content. Consider using alternative sources or implementing "
                "authenticated scraping with Playwright."
            )
        else:
            self.logger.info(f"XING: Found {len(jobs)} jobs total")
        
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
        # XING Jobs URL format: /jobs/search?keywords={keywords}&location={location}&page={page}
        params = {
            "keywords": keywords,
            "location": location,
            "page": page
        }
        
        search_url = f"{self.base_url}/jobs/search?{urlencode(params)}"
        
        self.logger.debug(f"Fetching: {search_url}")
        
        # Rate limiting
        await self.rate_limiter.wait()
        
        # Fetch page
        client = await self._get_client()
        
        # Add headers to appear more like a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        response = await client.get(search_url, headers=headers)
        
        # Check response
        if response.status_code == 401 or response.status_code == 403:
            self.logger.warning(
                f"XING returned {response.status_code} (authentication required)"
            )
            return []
        
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
        Parse XING search results HTML.
        
        Args:
            html_content: HTML page content
            search_keywords: Original search keywords
        
        Returns:
            List of Job objects
        """
        soup = BeautifulSoup(html_content, "html.parser")
        jobs = []
        
        # Try to find job listing containers
        # XING uses various class names and data attributes
        job_containers = []
        
        # Common XING selectors (may change over time)
        selectors = [
            "article[data-job-id]",        # Main job item with data attribute
            "div.job-card",                 # Job card container
            "li.job-listing",               # List item variant
            "div[data-testid='job-item']"  # Test ID variant
        ]
        
        for selector in selectors:
            job_containers = soup.select(selector)
            if job_containers:
                self.logger.debug(f"Found {len(job_containers)} jobs using selector: {selector}")
                break
        
        if not job_containers:
            self.logger.warning(
                "Could not find job containers in HTML. "
                "XING likely requires authentication or has changed their HTML structure."
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
                container.select_one("a.job-title") or
                container.select_one("a[data-testid='job-title']")
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
                container.select_one(".company-name") or
                container.select_one("div[data-testid='company-name']") or
                container.select_one("span.job-company")
            )
            
            company = company_elem.text.strip() if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = (
                container.select_one(".location") or
                container.select_one("div[data-testid='job-location']") or
                container.select_one("span.job-location")
            )
            
            location = location_elem.text.strip() if location_elem else "Deutschland"
            
            # Extract description preview (if available)
            description_elem = (
                container.select_one(".job-description") or
                container.select_one("div[data-testid='job-snippet']") or
                container.select_one("p.snippet")
            )
            
            description = (
                description_elem.text.strip()
                if description_elem
                else f"Job posting for {title} at {company} on XING. Search keywords: {search_keywords}"
            )
            
            # Extract job ID
            job_id = (
                container.get("data-job-id") or
                self._extract_job_id(url)
            )
            
            # Determine remote type
            remote_type = self._determine_remote_type(title, description, location)
            
            # Posted date (XING doesn't always show, use current time)
            posted_date = datetime.now() - timedelta(days=1)  # Assume posted yesterday
            
            # Create Job object
            job = Job(
                id=f"xing_{job_id}",
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url,
                description=description,
                posted_date=posted_date,
                source="XING"
            )
            
            return job
            
        except Exception as e:
            self.logger.debug(f"Error parsing job container: {e}")
            return None
    
    def _extract_job_id(self, url: str) -> str:
        """
        Extract job ID from XING URL.
        
        XING URLs typically contain alphanumeric job IDs.
        
        Args:
            url: XING job URL
        
        Returns:
            Job ID string
        """
        # Look for job ID pattern in URL
        # Format: /jobs/{some-slug}/{job-id}
        match = re.search(r"/jobs/[^/]+/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        
        # Fallback: use hash of URL
        return str(hash(url))[-10:]
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse job from raw data.
        
        Note: XING scraper uses HTML parsing internally,
        so this method is not used directly.
        
        Args:
            raw_data: Raw job data dictionary
        
        Returns:
            Job object or None
        """
        self.logger.warning("parse_job() called on XING scraper - use fetch_jobs() instead")
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
        
        # Check for remote indicators (German and English)
        remote_keywords = [
            "remote", "homeoffice", "home office", "home-office",
            "von zu hause", "ortsunabhängig", "deutschlandweit",
            "work from home", "wfh"
        ]
        
        if any(keyword in text for keyword in remote_keywords):
            # Check for hybrid
            if "hybrid" in text or "teilweise" in text or "anteilig" in text:
                return "Hybrid"
            return "Remote"
        
        return "Onsite"
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

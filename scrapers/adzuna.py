"""
Adzuna API scraper for job listings.

Adzuna provides a free API with rate limits (250 calls/month for free tier).
API Documentation: https://developer.adzuna.com/docs/search
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from scrapers.base import BaseScraper
from models.job import Job


class AdzunaScraper(BaseScraper):
    """
    Scraper for Adzuna API.
    
    Features:
    - Free API with 250 calls/month limit
    - Search by location, keywords, salary
    - Returns job listings with good metadata
    
    Environment Variables Required:
    - ADZUNA_APP_ID: Your Adzuna application ID
    - ADZUNA_APP_KEY: Your Adzuna application key
    
    Get API keys from: https://developer.adzuna.com/signup
    """
    
    BASE_API_URL = "https://api.adzuna.com/v1/api"
    
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        country: str = "de",  # Germany
        results_per_page: int = 50,
        max_pages: int = 3
    ):
        """
        Initialize Adzuna scraper.
        
        Args:
            app_id: Adzuna application ID (falls back to env var)
            app_key: Adzuna application key (falls back to env var)
            country: Country code (de, gb, us, etc.)
            results_per_page: Number of results per page (max 50)
            max_pages: Maximum number of pages to scrape
        """
        super().__init__(
            name="Adzuna",
            base_url=self.BASE_API_URL,
            timeout=15.0,
            max_retries=2
        )
        
        # API credentials (from args or environment)
        self.app_id = app_id or os.getenv("ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("ADZUNA_APP_KEY")
        self.country = country
        self.results_per_page = min(results_per_page, 50)  # API max is 50
        self.max_pages = max_pages
        
        # Check credentials
        if not self.app_id or not self.app_key:
            self.logger.warning(
                "Adzuna API credentials not found. Set ADZUNA_APP_ID and ADZUNA_APP_KEY "
                "environment variables or pass them to constructor."
            )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: str = "Germany"
    ) -> List[Job]:
        """
        Fetch jobs from Adzuna API.
        
        Args:
            keywords: Search keywords (e.g., ["Full Stack", "Backend"])
            location: Location filter (e.g., "Berlin", "Munich", "Germany")
        
        Returns:
            List of Job objects
        """
        # Check API credentials
        if not self.app_id or not self.app_key:
            self.logger.error("Cannot fetch jobs without API credentials")
            return []
        
        jobs = []
        search_query = " OR ".join(keywords) if keywords else "Full Stack OR Backend OR DevOps"
        
        self.logger.info(
            f"Searching Adzuna in {location} for: {search_query} "
            f"(max {self.max_pages} pages)"
        )
        
        for page in range(1, self.max_pages + 1):
            try:
                page_jobs = await self._fetch_page(
                    search_query=search_query,
                    location=location,
                    page=page
                )
                
                jobs.extend(page_jobs)
                
                self.logger.debug(
                    f"Page {page}/{self.max_pages}: {len(page_jobs)} jobs found"
                )
                
                # Stop if no more results
                if len(page_jobs) == 0:
                    break
                
            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                # Continue with other pages
        
        self.logger.info(f"Adzuna: Found {len(jobs)} jobs total")
        return jobs
    
    async def _fetch_page(
        self,
        search_query: str,
        location: str,
        page: int
    ) -> List[Job]:
        """
        Fetch a single page of results from Adzuna API.
        
        Args:
            search_query: Search query string
            location: Location filter
            page: Page number (1-indexed)
        
        Returns:
            List of Job objects from this page
        """
        # Build API URL
        endpoint = f"{self.BASE_API_URL}/jobs/{self.country}/search/{page}"
        
        # Build query parameters
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": self.results_per_page,
            "what": search_query,
            "where": location,
            "content-type": "application/json"
        }
        
        url = f"{endpoint}?{urlencode(params)}"
        
        # Rate limiting
        await self.rate_limiter.wait()
        
        # Fetch data
        client = await self._get_client()
        response = await client.get(url)
        
        # Check for rate limit errors
        if response.status_code == 429:
            self.logger.warning("Adzuna API rate limit exceeded")
            return []
        
        response.raise_for_status()
        data = response.json()
        
        # Parse results
        jobs = []
        results = data.get("results", [])
        
        for item in results:
            try:
                job = self.parse_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Error parsing job: {e}")
                continue
        
        return jobs
    
    def parse_job(self, item: Dict[str, Any]) -> Optional[Job]:
        """
        Parse a single job listing from Adzuna API response.
        
        Args:
            item: Job item dictionary from API
        
        Returns:
            Job object or None if parsing fails
        """
        try:
            # Extract fields
            title = item.get("title", "").strip()
            company = item.get("company", {}).get("display_name", "Unknown Company").strip()
            location = item.get("location", {}).get("display_name", "Unknown Location").strip()
            description = item.get("description", "").strip()
            url = item.get("redirect_url", "")
            
            # Validate required fields
            if not title or not description:
                return None
            
            # Parse posted date
            created = item.get("created")
            if created:
                try:
                    posted_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except:
                    posted_date = datetime.now()
            else:
                posted_date = datetime.now()
            
            # Determine remote type
            remote_type = self._determine_remote_type(title, description, location)
            
            # Extract contract type
            contract_type = item.get("contract_type") or item.get("contract_time")
            
            # Create Job object
            job = Job(
                id=f"adzuna_{item.get('id', '')}",
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                url=url,
                description=description,
                posted_date=posted_date,
                source="Adzuna",
                contract_type=contract_type,
                salary_min=item.get("salary_min"),
                salary_max=item.get("salary_max"),
                salary_currency="EUR" if self.country == "de" else "GBP"
            )
            
            return job
            
        except Exception as e:
            self.logger.debug(f"Error parsing job item: {e}")
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
            "remote", "work from home", "wfh", "distributed",
            "anywhere", "telecommute", "home office"
        ]
        
        if any(keyword in text for keyword in remote_keywords):
            # Check for hybrid
            if "hybrid" in text:
                return "Hybrid"
            return "Remote"
        
        return "Onsite"
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

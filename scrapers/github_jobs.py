"""
GitHub Jobs scraper.

Note: GitHub Jobs was discontinued in May 2021.
This scraper serves as a placeholder/example for similar job boards.

Alternative approach: Search GitHub repositories for job postings
(e.g., repos with "hiring" or "jobs" in name/description).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from scrapers.base import BaseScraper
from models.job import Job


class GitHubJobsScraper(BaseScraper):
    """
    Scraper for GitHub Jobs (currently non-functional).
    
    GitHub Jobs was shut down in May 2021.
    This scraper is implemented as a placeholder and will return
    an empty list with a warning message.
    
    Alternative approaches:
    1. Search GitHub repositories for job postings
    2. Use GitHub's "Who is hiring?" discussions/issues
    3. Search for company career pages on GitHub Pages
    4. Use alternative job boards that aggregate GitHub-based companies
    
    Related resources:
    - HackerNews "Who is hiring?" threads (already implemented)
    - Company career pages
    - Tech job aggregators
    """
    
    def __init__(self):
        """Initialize GitHub Jobs scraper."""
        super().__init__(
            name="GitHubJobs",
            base_url="https://jobs.github.com",
            timeout=15.0,
            max_retries=2
        )
        
        # Log deprecation warning on initialization
        self.logger.warning(
            "GitHub Jobs was discontinued in May 2021. "
            "This scraper returns no results. Consider using alternative sources "
            "like HackerNews 'Who is hiring?' threads."
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: str = "Germany"
    ) -> List[Job]:
        """
        Fetch jobs from GitHub Jobs.
        
        Since GitHub Jobs is discontinued, this returns an empty list.
        
        Args:
            keywords: Search keywords (ignored)
            location: Location filter (ignored)
        
        Returns:
            Empty list
        """
        self.logger.info(
            "GitHub Jobs scraper called but service is discontinued. "
            "Returning 0 jobs. Consider using HackerNews scraper instead."
        )
        
        return []
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse job from raw data.
        
        Note: GitHub Jobs API is discontinued.
        This method is a stub to satisfy BaseScraper interface.
        
        Args:
            raw_data: Raw job data dictionary
        
        Returns:
            None (service discontinued)
        """
        self.logger.warning("parse_job() called on GitHubJobs scraper - service discontinued")
        return None


# Future implementation ideas:
#
# 1. GitHub Repository Search:
#    Search for repositories with "hiring" or "jobs" in name/topics
#    Extract job information from README files
#
# 2. GitHub Discussions API:
#    Search discussions in tech communities for job postings
#    Parse structured job information from discussion posts
#
# 3. GitHub Pages Career Sites:
#    Many companies host career pages on GitHub Pages
#    Scrape these pages for job listings
#
# Example implementation skeleton:
#
# async def _search_hiring_repos(self, keywords: str) -> List[Job]:
#     """Search GitHub for repositories related to hiring."""
#     github_api = "https://api.github.com/search/repositories"
#     params = {
#         "q": f"{keywords} hiring OR jobs",
#         "sort": "updated",
#         "order": "desc"
#     }
#     client = await self._get_client()
#     response = await client.get(github_api, params=params)
#     data = response.json()
#     return self._parse_repo_results(data.get("items", []))
#
# def _parse_repo_results(self, repos: List[dict]) -> List[Job]:
#     """Extract job postings from repository metadata."""
#     jobs = []
#     for repo in repos:
#         # Parse repo description, README, etc.
#         job = self._extract_job_from_repo(repo)
#         if job:
#             jobs.append(job)
#     return jobs

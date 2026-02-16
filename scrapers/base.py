"""Base scraper class for all job board scrapers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from models.job import Job
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Provides:
    - Rate limiting
    - Error handling with retries
    - Logging
    - HTTP client management
    """
    
    def __init__(
        self,
        name: str,
        base_url: str,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize scraper.
        
        Args:
            name: Scraper name (used for logging and rate limiting)
            base_url: Base URL for the job board
            rate_limiter: Rate limiter instance (creates default if None)
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Rate limiter with per-scraper state
        self.rate_limiter = rate_limiter or RateLimiter(
            min_delay_seconds=2.0,
            max_requests_per_minute=30
        )
        
        # Logger
        self.logger = get_logger(f"scraper.{name.lower()}")
        
        # HTTP client (created lazily)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client.
        
        Returns:
            Configured AsyncClient
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    async def _fetch_url(self, url: str, **kwargs) -> httpx.Response:
        """
        Fetch URL with rate limiting and retries.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for httpx.get()
        
        Returns:
            HTTP response
        
        Raises:
            httpx.HTTPError: On HTTP errors after retries
        """
        # Apply rate limiting
        await self.rate_limiter.async_wait(source=self.name)
        
        self.logger.info(f"Fetching: {url}")
        
        client = await self._get_client()
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        
        return response
    
    @abstractmethod
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        **kwargs
    ) -> List[Job]:
        """
        Fetch jobs from the job board.
        
        Args:
            keywords: List of keywords to search for
            location: Location filter
            **kwargs: Additional scraper-specific parameters
        
        Returns:
            List of Job objects
        """
        pass
    
    @abstractmethod
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse raw job data into Job model.
        
        Args:
            raw_data: Raw job data from API/RSS/HTML
        
        Returns:
            Job object or None if parsing failed
        """
        pass
    
    def normalize_remote_type(self, text: str) -> str:
        """
        Normalize remote type string.
        
        Args:
            text: Raw remote type text
        
        Returns:
            Normalized remote type
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['full remote', 'fully remote', '100% remote']):
            return 'Full Remote'
        elif any(word in text_lower for word in ['hybrid', 'partial']):
            return 'Hybrid'
        elif 'remote' in text_lower:
            return 'Remote'
        else:
            return 'On-site'
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

"""Tests for scrapers."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import httpx

from scrapers.base import BaseScraper
from scrapers.remoteok import RemoteOKScraper
from models.job import Job
from utils.rate_limiter import RateLimiter


class TestBaseScraper:
    """Tests for BaseScraper abstract class."""
    
    def test_base_scraper_cannot_be_instantiated(self):
        """Test that BaseScraper is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseScraper(name="test", base_url="https://example.com")
    
    @pytest.mark.asyncio
    async def test_concrete_scraper_initialization(self):
        """Test that concrete scraper can be initialized."""
        scraper = RemoteOKScraper()
        
        assert scraper.name == "RemoteOK"
        assert scraper.base_url == "https://remoteok.com"
        assert scraper.rate_limiter is not None
        assert scraper.timeout == 30.0
        assert scraper.max_retries == 3
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_integration(self):
        """Test that scraper uses rate limiter."""
        # Create scraper with custom rate limiter
        rate_limiter = RateLimiter(min_delay_seconds=0.1)
        scraper = RemoteOKScraper(rate_limiter=rate_limiter)
        
        # Mock HTTP response
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = '<?xml version="1.0"?><rss><channel></channel></rss>'
        mock_response.raise_for_status = Mock()
        
        with patch.object(scraper, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            # Make two requests and measure time
            start = asyncio.get_event_loop().time()
            await scraper._fetch_url("https://example.com")
            await scraper._fetch_url("https://example.com")
            elapsed = asyncio.get_event_loop().time() - start
            
            # Should have delay between requests
            assert elapsed >= 0.1, "Rate limiter should enforce delay"
        
        await scraper.close()
    
    def test_normalize_remote_type(self):
        """Test remote type normalization."""
        scraper = RemoteOKScraper()
        
        assert scraper.normalize_remote_type("Full Remote") == "Full Remote"
        assert scraper.normalize_remote_type("100% remote") == "Full Remote"
        assert scraper.normalize_remote_type("Fully Remote") == "Full Remote"
        assert scraper.normalize_remote_type("Hybrid") == "Hybrid"
        assert scraper.normalize_remote_type("Partial Remote") == "Hybrid"
        assert scraper.normalize_remote_type("Remote") == "Remote"
        assert scraper.normalize_remote_type("On-site") == "On-site"
        assert scraper.normalize_remote_type("Office") == "On-site"


class TestRemoteOKScraper:
    """Tests for RemoteOKScraper."""
    
    @pytest.fixture
    def sample_rss_content(self) -> str:
        """Load sample RSS content from fixture file."""
        fixture_path = Path(__file__).parent / "fixtures" / "remoteok_sample.xml"
        return fixture_path.read_text(encoding='utf-8')
    
    @pytest.fixture
    def scraper(self) -> RemoteOKScraper:
        """Create RemoteOKScraper instance."""
        return RemoteOKScraper()
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self, scraper):
        """Test RemoteOKScraper initialization."""
        assert scraper.name == "RemoteOK"
        assert scraper.RSS_URL == "https://remoteok.com/remote-jobs.rss"
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_fetch_jobs_with_mock_response(self, scraper, sample_rss_content):
        """Test fetching jobs with mocked RSS response."""
        # Mock HTTP response
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = sample_rss_content
        mock_response.raise_for_status = Mock()
        
        with patch.object(scraper, '_fetch_url', return_value=mock_response) as mock_fetch:
            jobs = await scraper.fetch_jobs()
            
            # Verify fetch was called
            mock_fetch.assert_called_once()
            
            # Verify jobs were parsed
            assert len(jobs) > 0, "Should parse jobs from RSS feed"
            assert all(isinstance(job, Job) for job in jobs), "All items should be Job objects"
            assert all(job.source == "RemoteOK" for job in jobs), "All jobs should have RemoteOK source"
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_fetch_jobs_with_keyword_filter(self, scraper, sample_rss_content):
        """Test fetching jobs with keyword filtering."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = sample_rss_content
        mock_response.raise_for_status = Mock()
        
        with patch.object(scraper, '_fetch_url', return_value=mock_response):
            # Filter by Python keyword
            python_jobs = await scraper.fetch_jobs(keywords=["Python"])
            
            # Should only get Python job
            assert len(python_jobs) >= 1, "Should find Python jobs"
            assert any("python" in job.title.lower() or 
                      "python" in job.description.lower() 
                      for job in python_jobs), "Jobs should contain Python keyword"
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_parse_job_entry(self, scraper):
        """Test parsing a single RSS entry."""
        import feedparser
        
        rss_entry = {
            'title': 'TestCorp: Senior Developer',
            'link': 'https://remoteok.com/job/123',
            'summary': '<p>Great job with C# and .NET experience required.</p>',
            'published_parsed': None,
            'tags': [
                {'term': 'C#'},
                {'term': '.NET'},
                {'term': 'Backend'}
            ]
        }
        
        job = scraper.parse_job(rss_entry)
        
        assert job is not None, "Should successfully parse job"
        assert job.title == "Senior Developer"
        assert job.company == "TestCorp"
        assert str(job.url) == "https://remoteok.com/job/123"
        assert job.location == "Remote"
        assert job.remote_type == "Full Remote"
        assert job.source == "RemoteOK"
        assert "C#" in (job.tech_stack or [])
        assert ".NET" in (job.tech_stack or [])
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_parse_job_missing_fields(self, scraper):
        """Test parsing job with missing fields."""
        # Missing title
        entry_no_title = {'link': 'https://example.com'}
        assert scraper.parse_job(entry_no_title) is None, "Should return None for missing title"
        
        # Missing URL
        entry_no_url = {'title': 'Test Job'}
        assert scraper.parse_job(entry_no_url) is None, "Should return None for missing URL"
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_fetch_jobs_handles_errors(self, scraper):
        """Test that fetch_jobs handles errors gracefully."""
        # Mock HTTP error
        with patch.object(scraper, '_fetch_url', side_effect=httpx.HTTPError("Network error")):
            jobs = await scraper.fetch_jobs()
            
            # Should return empty list on error
            assert jobs == [], "Should return empty list on network error"
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_matches_keywords(self, scraper):
        """Test keyword matching logic."""
        job = Job(
            id="test-1",
            title="Python Developer",
            company="Test Corp",
            location="Remote",
            remote_type="Full Remote",
            url="https://example.com",
            description="Looking for Python and Django expert",
            posted_date=datetime.now(),
            source="RemoteOK",
            tech_stack=["Python", "Django"]
        )
        
        # Should match keyword in title
        assert scraper._matches_keywords(job, ["Python"]) is True
        
        # Should match keyword in description
        assert scraper._matches_keywords(job, ["expert"]) is True
        
        # Should match keyword in tech_stack
        assert scraper._matches_keywords(job, ["Django"]) is True
        
        # Should not match non-existent keyword
        assert scraper._matches_keywords(job, ["Java"]) is False
        
        # Should match at least one keyword (OR logic)
        assert scraper._matches_keywords(job, ["Java", "Python"]) is True
        
        await scraper.close()
    
    @pytest.mark.asyncio
    async def test_http_client_cleanup(self, scraper):
        """Test that HTTP client is properly closed."""
        # Get client (creates it)
        client = await scraper._get_client()
        assert client is not None
        
        # Close scraper
        await scraper.close()
        
        # Client should be None after close
        assert scraper._client is None

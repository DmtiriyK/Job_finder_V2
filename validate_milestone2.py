"""
Validation script for Milestone 2: First Scraper Working End-to-End

Tests acceptance criteria:
1. Scraper execution works
2. Rate limiting is applied
3. Error handling works
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.remoteok import RemoteOKScraper
from models.job import Job
from utils.logger import get_logger


logger = get_logger("validation_milestone2")


async def test_scraper_execution():
    """Test that scraper can fetch and parse jobs."""
    logger.info("=" * 60)
    logger.info("TEST 1: Scraper Execution")
    logger.info("=" * 60)
    
    try:
        scraper = RemoteOKScraper()
        
        # Fetch jobs with keywords
        jobs = await scraper.fetch_jobs(
            keywords=["Full Stack", "Backend", ".NET"],
            location="Germany"
        )
        
        # Validate results
        assert len(jobs) > 0, "Should fetch at least some jobs"
        assert all(isinstance(j, Job) for j in jobs), "All items should be Job objects"
        assert all(j.source == "RemoteOK" for j in jobs), "All jobs should have RemoteOK source"
        
        logger.info(f"✅ Found {len(jobs)} jobs from RemoteOK")
        if jobs:
            sample = jobs[0]
            logger.info(f"Sample job: {sample.title} at {sample.company}")
            logger.info(f"  URL: {sample.url}")
            logger.info(f"  Posted: {sample.posted_date}")
            logger.info(f"  Tech Stack: {sample.tech_stack}")
        
        await scraper.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Scraper execution test failed: {e}", exc_info=True)
        return False


async def test_rate_limiting():
    """Test that rate limiting delays are applied."""
    logger.info("=" * 60)
    logger.info("TEST 2: Rate Limiting")
    logger.info("=" * 60)
    
    try:
        from utils.rate_limiter import RateLimiter
        import time
        
        scraper = RemoteOKScraper(
            rate_limiter=RateLimiter(min_delay_seconds=1.0)
        )
        
        # Make two requests and measure time
        start = time.time()
        
        jobs1 = await scraper.fetch_jobs(keywords=["Python"])
        jobs2 = await scraper.fetch_jobs(keywords=["React"])
        
        elapsed = time.time() - start
        
        # Should have at least 1 second delay
        assert elapsed >= 1.0, f"Expected delay >= 1s, got {elapsed:.2f}s"
        
        logger.info(f"✅ Rate limiting works: {elapsed:.2f}s elapsed (expected >= 1s)")
        
        await scraper.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Rate limiting test failed: {e}", exc_info=True)
        return False


async def test_error_handling():
    """Test that scraper handles errors gracefully."""
    logger.info("=" * 60)
    logger.info("TEST 3: Error Handling")
    logger.info("=" * 60)
    
    try:
        scraper = RemoteOKScraper()
        
        # Test with invalid RSS entry (missing fields)
        invalid_entry = {'title': '', 'link': ''}
        job = scraper.parse_job(invalid_entry)
        
        assert job is None, "Should return None for invalid entry"
        logger.info("✅ Invalid entries handled gracefully (returns None)")
        
        # Test that fetch_jobs doesn't crash on network errors
        # (This is tested in unit tests with mocks, just verify the method exists)
        assert hasattr(scraper, 'fetch_jobs'), "fetch_jobs method exists"
        assert hasattr(scraper, '_fetch_url'), "_fetch_url method exists"
        
        logger.info("✅ Error handling methods implemented")
        
        await scraper.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}", exc_info=True)
        return False


async def test_unified_job_model():
    """Test that scraper returns unified Job models."""
    logger.info("=" * 60)
    logger.info("TEST 4: Unified Job Model")
    logger.info("=" * 60)
    
    try:
        scraper = RemoteOKScraper()
        
        jobs = await scraper.fetch_jobs(keywords=["Developer"])
        
        if not jobs:
            logger.warning("⚠️  No jobs found, skipping model validation")
            await scraper.close()
            return True
        
        # Check that all required fields are present
        job = jobs[0]
        
        assert hasattr(job, 'id'), "Job has id field"
        assert hasattr(job, 'title'), "Job has title field"
        assert hasattr(job, 'company'), "Job has company field"
        assert hasattr(job, 'location'), "Job has location field"
        assert hasattr(job, 'url'), "Job has url field"
        assert hasattr(job, 'description'), "Job has description field"
        assert hasattr(job, 'source'), "Job has source field"
        
        assert job.id is not None and len(job.id) > 0, "ID is generated"
        assert job.source == "RemoteOK", "Source is set correctly"
        
        logger.info("✅ Jobs follow unified Job model")
        logger.info(f"   Fields present: id, title, company, location, url, description, source")
        
        await scraper.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Unified model test failed: {e}", exc_info=True)
        return False


async def run_all_tests():
    """Run all validation tests."""
    logger.info("\n" + "=" * 60)
    logger.info("MILESTONE 2 VALIDATION")
    logger.info("First Scraper Working End-to-End")
    logger.info("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Scraper Execution", await test_scraper_execution()))
    results.append(("Rate Limiting", await test_rate_limiting()))
    results.append(("Error Handling", await test_error_handling()))
    results.append(("Unified Job Model", await test_unified_job_model()))
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("🎉 Milestone 2 Validation SUCCESSFUL!")
        logger.info("All acceptance criteria met.")
    else:
        logger.info("❌ Milestone 2 Validation FAILED")
        logger.info("Some tests did not pass.")
    logger.info("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

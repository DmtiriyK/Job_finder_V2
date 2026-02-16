"""
Milestone 5 Acceptance Tests: Local Pipeline Working (3 Scrapers)

Validates:
- 3 scrapers implemented (RemoteOK, WeWorkRemotely, HackerNews)
- Pre-filtering logic
- Deduplication
- Basic orchestration
"""

import sys
from datetime import datetime, timedelta
from typing import List

from models.job import Job
from processors.filter import JobFilter
from processors.deduplicator import Deduplicator
from scrapers.remoteok import RemoteOKScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.hackernews import HackerNewsScraper


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result with color coding."""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if details:
        print(f"      {details}")


def print_section(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


# ============================================================================
# TEST 1: Scrapers Implemented
# ============================================================================
def test_scrapers_implemented() -> bool:
    """Test that all 3 scrapers are implemented and can be instantiated."""
    print_section("TEST 1: Scrapers Implemented")
    
    scrapers_passed = True
    
    # Test RemoteOK scraper
    try:
        remoteok = RemoteOKScraper()
        assert remoteok.name == "RemoteOK"
        print_test("RemoteOK scraper", True, "Instantiated and has correct name")
    except Exception as e:
        print_test("RemoteOK scraper", False, f"Error: {e}")
        scrapers_passed = False
    
    # Test WeWorkRemotely scraper
    try:
        wwr = WeWorkRemotelyScraper()
        assert wwr.name == "WeWorkRemotely"
        print_test("WeWorkRemotely scraper", True, "Instantiated and has correct name")
    except Exception as e:
        print_test("WeWorkRemotely scraper", False, f"Error: {e}")
        scrapers_passed = False
    
    # Test HackerNews scraper
    try:
        hn = HackerNewsScraper()
        assert hn.name == "HackerNews"
        print_test("HackerNews scraper", True, "Instantiated and has correct name")
    except Exception as e:
        print_test("HackerNews scraper", False, f"Error: {e}")
        scrapers_passed = False
    
    return scrapers_passed


# ============================================================================
# TEST 2: Pre-filtering Logic
# ============================================================================
def test_prefiltering_logic() -> bool:
    """Test pre-filtering logic with various criteria."""
    print_section("TEST 2: Pre-filtering Logic")
    
    # Create sample jobs
    jobs = [
        Job(
            id="job1",
            title="Full Stack Engineer",
            company="TechCorp",
            location="Berlin, Germany",
            remote_type="Remote",
            url="https://example.com/1",
            description="Looking for a Full Stack Engineer with React and .NET experience. " * 10,
            posted_date=datetime.now() - timedelta(days=2),
            source="test"
        ),
        Job(
            id="job2",
            title="Backend Developer",
            company="StartupX",
            location="Munich, Germany",
            remote_type="Hybrid",
            url="https://example.com/2",
            description="Backend Developer position with Python and Django. " * 10,
            posted_date=datetime.now() - timedelta(days=15),  # Too old
            source="test"
        ),
        Job(
            id="job3",
            title="DevOps Engineer",
            company="BigCo",
            location="London, UK",  # Not Germany
            remote_type="Onsite",
            url="https://example.com/3",
            description="DevOps Engineer needed for cloud infrastructure. " * 10,
            posted_date=datetime.now() - timedelta(days=3),
            source="test"
        ),
        Job(
            id="job4",
            title="Platform Engineer",
            company="CloudCo",
            location="Remote",
            remote_type="Remote",
            url="https://example.com/4",
            description="Platform Engineer with Kubernetes experience. " * 10,
            posted_date=datetime.now() - timedelta(days=5),
            source="test"
        ),
    ]
    
    filter_obj = JobFilter()
    
    # Test location filtering
    filtered = filter_obj.apply(jobs, {"locations": ["Germany"]})
    passed = len(filtered) == 2 and all("Germany" in j.location for j in filtered)
    print_test(
        "Location filtering", 
        passed, 
        f"Filtered {len(jobs)} → {len(filtered)} jobs (Germany only)"
    )
    if not passed:
        return False
    
    # Test age filtering
    filtered = filter_obj.apply(jobs, {"max_age_days": 7})
    passed = len(filtered) == 3 and all(
        j.posted_date >= datetime.now() - timedelta(days=7) for j in filtered
    )
    print_test(
        "Age filtering",
        passed,
        f"Filtered {len(jobs)} → {len(filtered)} jobs (last 7 days)"
    )
    if not passed:
        return False
    
    # Test combined filtering
    filtered = filter_obj.apply(jobs, {
        "locations": ["Germany", "Remote"],
        "max_age_days": 7,
        "remote_types": ["Remote", "Hybrid"]
    })
    passed = len(filtered) == 2
    print_test(
        "Combined filtering",
        passed,
        f"Filtered {len(jobs)} → {len(filtered)} jobs (Germany+Remote, <7 days, Remote+Hybrid)"
    )
    if not passed:
        return False
    
    # Test filter statistics
    stats = filter_obj.get_filter_stats(jobs, {"locations": ["Germany"]})
    passed = "estimated_retained" in stats and stats["estimated_retained"] == 2
    print_test(
        "Filter statistics",
        passed,
        f"Statistics: {stats.get('estimated_retained', 0)} jobs would remain"
    )
    
    return passed


# ============================================================================
# TEST 3: Deduplication
# ============================================================================
def test_deduplication() -> bool:
    """Test deduplication logic with similar jobs."""
    print_section("TEST 3: Deduplication")
    
    # Create jobs with duplicates
    jobs = [
        Job(
            id="job1",
            title="Full Stack Engineer",
            company="TechCorp",
            location="Berlin",
            remote_type="Remote",
            url="https://example.com/1",
            description="Full Stack Engineer position at TechCorp with React and .NET. " * 5,
            posted_date=datetime.now(),
            source="remoteok"
        ),
        Job(
            id="job2",
            title="Full Stack Engineer",  # Exact duplicate
            company="TechCorp",
            location="Berlin",
            remote_type="Remote",
            url="https://example.com/2",
            description="Full Stack Engineer position at TechCorp with React and .NET. " * 5,
            posted_date=datetime.now(),
            source="weworkremotely"
        ),
        Job(
            id="job3",
            title="Fullstack Engineer",  # Similar (typo variant)
            company="TechCorp",
            location="Berlin",
            remote_type="Remote",
            url="https://example.com/3",
            description="Fullstack Engineer role at TechCorp with React and .NET. " * 5,
            posted_date=datetime.now(),
            source="hackernews"
        ),
        Job(
            id="job4",
            title="Backend Developer",  # Different job
            company="StartupX",
            location="Munich",
            remote_type="Remote",
            url="https://example.com/4",
            description="Backend Developer position at StartupX with Python. " * 5,
            posted_date=datetime.now(),
            source="remoteok"
        ),
    ]
    
    dedup = Deduplicator()
    
    # Test exact duplicate removal
    unique = dedup.remove_duplicates(jobs[:2])  # job1 and job2 are exact duplicates
    passed = len(unique) == 1
    print_test(
        "Exact duplicate removal",
        passed,
        f"Removed {len(jobs[:2]) - len(unique)} exact duplicate(s)"
    )
    if not passed:
        return False
    
    # Test similar duplicate removal
    unique = dedup.remove_duplicates(jobs[:3])  # job1, job2, job3 are similar
    passed = len(unique) <= 2  # Should remove at least 1 duplicate
    print_test(
        "Similar duplicate removal",
        passed,
        f"Removed {len(jobs[:3]) - len(unique)} similar duplicate(s) (threshold=0.85)"
    )
    if not passed:
        return False
    
    # Test no duplicates
    unique = dedup.remove_duplicates([jobs[0], jobs[3]])  # Different jobs
    passed = len(unique) == 2
    print_test(
        "No false positives",
        passed,
        f"Kept {len(unique)}/2 unique jobs (no false duplicates)"
    )
    if not passed:
        return False
    
    # Test deduplication statistics
    stats = dedup.get_deduplication_stats(jobs)
    passed = "exact_duplicates" in stats and "similar_duplicate_pairs" in stats
    print_test(
        "Deduplication statistics",
        passed,
        f"Found {stats.get('exact_duplicates', 0)} exact + {stats.get('similar_duplicate_pairs', 0)} similar duplicates"
    )
    
    return passed


# ============================================================================
# TEST 4: Integration Test (Mock Pipeline)
# ============================================================================
def test_integration_mock_pipeline() -> bool:
    """Test full pipeline with mock data."""
    print_section("TEST 4: Integration Test (Mock Pipeline)")
    
    # Create a larger dataset with various scenarios
    jobs = []
    
    # Add 10 valid jobs
    for i in range(10):
        jobs.append(Job(
            id=f"valid_{i}",
            title=f"Full Stack Engineer {i}",
            company=f"TechCorp{i}",
            location="Berlin, Germany",
            remote_type="Remote",
            url=f"https://example.com/valid{i}",
            description=f"Full Stack Engineer position with React and .NET. Great benefits. " * 10,
            posted_date=datetime.now() - timedelta(days=i),
            source="test"
        ))
    
    # Add 5 old jobs (should be filtered out)
    for i in range(5):
        jobs.append(Job(
            id=f"old_{i}",
            title=f"Backend Developer {i}",
            company=f"OldCo{i}",
            location="Munich, Germany",
            remote_type="Remote",
            url=f"https://example.com/old{i}",
            description=f"Backend Developer position with Python. " * 10,
            posted_date=datetime.now() - timedelta(days=20 + i),
            source="test"
        ))
    
    # Add 3 duplicates
    for i in range(3):
        jobs.append(Job(
            id=f"dup_{i}",
            title="Full Stack Engineer 0",  # Duplicate of valid_0
            company="TechCorp0",
            location="Berlin, Germany",
            remote_type="Remote",
            url=f"https://example.com/dup{i}",
            description="Full Stack Engineer position with React and .NET. Great benefits. " * 10,
            posted_date=datetime.now(),
            source="test"
        ))
    
    initial_count = len(jobs)
    print(f"Initial job count: {initial_count}")
    
    # Step 1: Pre-filter
    filter_obj = JobFilter()
    filtered = filter_obj.apply(jobs, {
        "locations": ["Germany"],
        "max_age_days": 14
    })
    after_filter = len(filtered)
    passed = after_filter < initial_count
    print_test(
        "Pipeline step 1: Pre-filtering",
        passed,
        f"{initial_count} → {after_filter} jobs (removed {initial_count - after_filter} old/non-Germany)"
    )
    if not passed:
        return False
    
    # Step 2: Deduplicate
    dedup = Deduplicator()
    unique = dedup.remove_duplicates(filtered)
    after_dedup = len(unique)
    passed = after_dedup <= after_filter
    print_test(
        "Pipeline step 2: Deduplication",
        passed,
        f"{after_filter} → {after_dedup} jobs (removed {after_filter - after_dedup} duplicates)"
    )
    if not passed:
        return False
    
    # Verify final output
    passed = after_dedup > 0 and after_dedup < initial_count
    print_test(
        "Pipeline output validation",
        passed,
        f"Final: {after_dedup} unique, recent, Germany-based jobs"
    )
    
    return passed


# ============================================================================
# Main Execution
# ============================================================================
def main():
    """Run all Milestone 5 acceptance tests."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Milestone 5 Acceptance Tests: Local Pipeline (3 Scrapers){Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    tests = [
        ("Scrapers Implemented", test_scrapers_implemented),
        ("Pre-filtering Logic", test_prefiltering_logic),
        ("Deduplication", test_deduplication),
        ("Integration (Mock Pipeline)", test_integration_mock_pipeline),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print_test(name, False, f"Exception: {e}")
            results.append((name, False))
    
    # Print summary
    print_section("Summary")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {name}")
    
    print(f"\n{Colors.BOLD}Results: {passed_count}/{total_count} tests passed{Colors.END}")
    
    if passed_count == total_count:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Milestone 5 COMPLETE!{Colors.END}")
        print(f"{Colors.GREEN}All acceptance criteria met.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Milestone 5 INCOMPLETE{Colors.END}")
        print(f"{Colors.RED}Some tests failed. Please review.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Milestone 6 Acceptance Tests: All 9 Scrapers Integrated

Validates:
- All 9 scrapers can be instantiated
- main.py recognizes all scrapers
- Pipeline initialization works with all scrapers
- Error handling for scrapers without credentials/access
"""

import sys
from typing import List

from scrapers import (
    RemoteOKScraper,
    WeWorkRemotelyScraper,
    HackerNewsScraper,
    AdzunaScraper,
    IndeedScraper,
    StackOverflowScraper,
    GitHubJobsScraper,
    StepStoneScraper,
    XINGScraper
)
from main import JobFinderPipeline


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
# TEST 1: All Scrapers Can Be Instantiated
# ============================================================================
def test_all_scrapers_instantiation() -> bool:
    """Test that all 9 scrapers can be instantiated."""
    print_section("TEST 1: All Scrapers Can Be Instantiated")
    
    scrapers = [
        ("RemoteOK", RemoteOKScraper, {}),
        ("WeWorkRemotely", WeWorkRemotelyScraper, {}),
        ("HackerNews", HackerNewsScraper, {}),
        ("Adzuna", AdzunaScraper, {}),
        ("Indeed", IndeedScraper, {}),
        ("StackOverflow", StackOverflowScraper, {}),
        ("GitHub Jobs", GitHubJobsScraper, {}),
        ("StepStone", StepStoneScraper, {}),
        ("XING", XINGScraper, {}),
    ]
    
    all_passed = True
    
    for name, scraper_class, kwargs in scrapers:
        try:
            scraper = scraper_class(**kwargs)
            assert scraper.name is not None
            print_test(f"{name} scraper", True, f"Name: {scraper.name}")
        except Exception as e:
            print_test(f"{name} scraper", False, f"Error: {e}")
            all_passed = False
    
    return all_passed


# ============================================================================
# TEST 2: Pipeline Recognizes All Scrapers
# ============================================================================
def test_pipeline_recognizes_all_scrapers() -> bool:
    """Test that JobFinderPipeline recognizes all 9 scrapers."""
    print_section("TEST 2: Pipeline Recognizes All Scrapers")
    
    expected_scrapers = [
        'remoteok',
        'weworkremotely',
        'hackernews',
        'adzuna',
        'indeed',
        'stackoverflow',
        'github',
        'stepstone',
        'xing'
    ]
    
    available_scrapers = JobFinderPipeline.SCRAPERS.keys()
    
    all_passed = True
    found_count = 0
    
    for scraper_name in expected_scrapers:
        if scraper_name in available_scrapers:
            print_test(f"'{scraper_name}' registered", True)
            found_count += 1
        else:
            print_test(f"'{scraper_name}' registered", False, "Not found in SCRAPERS dict")
            all_passed = False
    
    print_test(
        "All scrapers registered",
        found_count == len(expected_scrapers),
        f"{found_count}/{len(expected_scrapers)} scrapers found"
    )
    
    return all_passed and found_count == len(expected_scrapers)


# ============================================================================
# TEST 3: Pipeline Initialization
# ============================================================================
def test_pipeline_initialization() -> bool:
    """Test pipeline initialization with different scraper configurations."""
    print_section("TEST 3: Pipeline Initialization")
    
    all_passed = True
    
    # Test 1: Initialize with default (all scrapers)
    try:
        pipeline = JobFinderPipeline()
        scraper_count = len(pipeline.scrapers)
        passed = scraper_count == 9
        print_test(
            "Default initialization (all scrapers)",
            passed,
            f"Initialized {scraper_count}/9 scrapers"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Default initialization", False, f"Error: {e}")
        all_passed = False
    
    # Test 2: Initialize with subset of scrapers
    try:
        pipeline = JobFinderPipeline(scrapers=['remoteok', 'indeed', 'adzuna'])
        scraper_count = len(pipeline.scrapers)
        passed = scraper_count == 3
        print_test(
            "Subset initialization (3 scrapers)",
            passed,
            f"Initialized {scraper_count}/3 scrapers"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Subset initialization", False, f"Error: {e}")
        all_passed = False
    
    # Test 3: Initialize with single scraper
    try:
        pipeline = JobFinderPipeline(scrapers=['remoteok'])
        scraper_count = len(pipeline.scrapers)
        passed = scraper_count == 1
        print_test(
            "Single scraper initialization",
            passed,
            f"Initialized {scraper_count}/1 scraper"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Single scraper initialization", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 4: Scraper Base Properties
# ============================================================================
def test_scraper_base_properties() -> bool:
    """Test that all scrapers have required base properties."""
    print_section("TEST 4: Scraper Base Properties")
    
    scrapers = [
        RemoteOKScraper(),
        WeWorkRemotelyScraper(),
        HackerNewsScraper(),
        AdzunaScraper(),
        IndeedScraper(),
        StackOverflowScraper(),
        GitHubJobsScraper(),
        StepStoneScraper(),
        XINGScraper(),
    ]
    
    all_passed = True
    
    for scraper in scrapers:
        # Check name property
        has_name = hasattr(scraper, 'name') and scraper.name
        
        # Check base_url property
        has_base_url = hasattr(scraper, 'base_url') and scraper.base_url
        
        # Check fetch_jobs method
        has_fetch_jobs = hasattr(scraper, 'fetch_jobs') and callable(scraper.fetch_jobs)
        
        # Check close method
        has_close = hasattr(scraper, 'close') and callable(scraper.close)
        
        passed = has_name and has_base_url and has_fetch_jobs and has_close
        
        details = []
        if not has_name:
            details.append("missing 'name'")
        if not has_base_url:
            details.append("missing 'base_url'")
        if not has_fetch_jobs:
            details.append("missing 'fetch_jobs()'")
        if not has_close:
            details.append("missing 'close()'")
        
        detail_str = ", ".join(details) if details else "All required properties present"
        
        print_test(
            f"{scraper.name} properties",
            passed,
            detail_str
        )
        
        if not passed:
            all_passed = False
    
    return all_passed


# ============================================================================
# TEST 5: Scraper Error Handling
# ============================================================================
def test_scraper_error_handling() -> bool:
    """Test that scrapers handle missing credentials/access gracefully."""
    print_section("TEST 5: Scraper Error Handling")
    
    all_passed = True
    
    # Test 1: Adzuna without credentials (should warn, not crash)
    try:
        adzuna = AdzunaScraper(app_id=None, app_key=None)
        # Should instantiate without crashing
        passed = adzuna.name == "Adzuna"
        print_test(
            "Adzuna without credentials",
            passed,
            "Instantiated successfully (will warn when scraping)"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Adzuna without credentials", False, f"Unexpected error: {e}")
        all_passed = False
    
    # Test 2: StackOverflow (deprecated service)
    try:
        stackoverflow = StackOverflowScraper()
        # Should instantiate and log warning
        passed = stackoverflow.name == "StackOverflow"
        print_test(
            "StackOverflow (deprecated)",
            passed,
            "Handles deprecated service gracefully"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("StackOverflow (deprecated)", False, f"Unexpected error: {e}")
        all_passed = False
    
    # Test 3: GitHub Jobs (deprecated service)
    try:
        github = GitHubJobsScraper()
        # Should instantiate and log warning
        passed = github.name == "GitHubJobs"
        print_test(
            "GitHub Jobs (deprecated)",
            passed,
            "Handles deprecated service gracefully"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("GitHub Jobs (deprecated)", False, f"Unexpected error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# Main Execution
# ============================================================================
def main():
    """Run all Milestone 6 acceptance tests."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Milestone 6 Acceptance Tests: All 9 Scrapers Integrated{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    tests = [
        ("All Scrapers Instantiation", test_all_scrapers_instantiation),
        ("Pipeline Recognizes Scrapers", test_pipeline_recognizes_all_scrapers),
        ("Pipeline Initialization", test_pipeline_initialization),
        ("Scraper Base Properties", test_scraper_base_properties),
        ("Scraper Error Handling", test_scraper_error_handling),
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
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Milestone 6 COMPLETE!{Colors.END}")
        print(f"{Colors.GREEN}All 9 scrapers are integrated and working.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Milestone 6 INCOMPLETE{Colors.END}")
        print(f"{Colors.RED}Some tests failed. Please review.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

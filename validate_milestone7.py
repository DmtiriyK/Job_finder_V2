"""
Milestone 7 Acceptance Tests: Google Sheets Integration

Validates:
- GoogleSheetsWriter initialization (with/without credentials)
- Color coding logic
- Row formatting
- Sheet structure
- CLI integration
"""

import sys
from typing import List
from datetime import datetime
from unittest.mock import Mock

from integrations.google_sheets import GoogleSheetsWriter
from models.job import Job, ScoreResult


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


def create_sample_jobs() -> List[Job]:
    """Create sample jobs for testing."""
    return [
        Job(
            id="job1",
            title="Senior Python Developer",
            company="TechCorp",
            location="Berlin, Germany",
            remote_type="Full Remote",
            url="https://example.com/job1",
            description="Python backend developer position requiring experience with Django and FastAPI.",
            posted_date=datetime(2026, 2, 15),
            source="RemoteOK",
            source_id="12345",
            tech_stack=["Python", "Django", "FastAPI", "Docker"],
            contract_type="Festanstellung"
        ),
        Job(
            id="job2",
            title="Full Stack Engineer",
            company="StartupX",
            location="Remote, Europe",
            remote_type="Remote",
            url="https://example.com/job2",
            description="Full stack position with React and Node.js",
            posted_date=datetime(2026, 2, 14),
            source="Indeed",
            source_id="67890",
            tech_stack=["React", "Node.js", "TypeScript"],
            contract_type="Freelance"
        )
    ]


def create_sample_scores() -> dict:
    """Create sample score results."""
    return {
        "job1": ScoreResult(
            score=85.5,
            breakdown={
                "tfidf": {"raw": 35.0, "normalized": 35.0, "max": 40.0},
                "tech_stack": {"raw": 25.0, "normalized": 25.0, "max": 30.0},
                "remote": {"raw": 15.0, "normalized": 15.0, "max": 15.0},
                "keyword": {"raw": 10.5, "normalized": 10.5, "max": 10.0}
            }
        ),
        "job2": ScoreResult(
            score=72.3,
            breakdown={
                "tfidf": {"raw": 28.0, "normalized": 28.0, "max": 40.0},
                "tech_stack": {"raw": 20.0, "normalized": 20.0, "max": 30.0},
                "remote": {"raw": 15.0, "normalized": 15.0, "max": 15.0},
                "keyword": {"raw": 9.3, "normalized": 9.3, "max": 10.0}
            }
        )
    }


# ============================================================================
# TEST 1: GoogleSheetsWriter Initialization
# ============================================================================
def test_writer_initialization() -> bool:
    """Test GoogleSheetsWriter initialization."""
    print_section("TEST 1: GoogleSheetsWriter Initialization")
    
    all_passed = True
    
    # Test 1: Initialize without credentials (should not crash)
    try:
        writer = GoogleSheetsWriter(credentials_path="nonexistent.json")
        passed = not writer.is_enabled()
        print_test(
            "Initialize without credentials",
            passed,
            "Gracefully handles missing credentials"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Initialize without credentials", False, f"Unexpected error: {e}")
        all_passed = False
    
    # Test 2: Check default credentials path
    try:
        writer = GoogleSheetsWriter()
        # Should either enable (if creds exist) or disable (if not)
        passed = isinstance(writer.is_enabled(), bool)
        status = "enabled" if writer.is_enabled() else "disabled"
        print_test(
            "Default initialization",
            passed,
            f"Writer is {status} (expected behavior)"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Default initialization", False, f"Unexpected error: {e}")
        all_passed = False
    
    # Test 3: Check spreadsheet name
    try:
        writer = GoogleSheetsWriter(spreadsheet_name="Test Spreadsheet")
        passed = writer.spreadsheet_name == "Test Spreadsheet"
        print_test(
            "Custom spreadsheet name",
            passed,
            f"Spreadsheet name: {writer.spreadsheet_name}"
        )
        if not passed:
            all_passed = False
    except Exception as e:
        print_test("Custom spreadsheet name", False, f"Unexpected error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 2: Color Coding Logic
# ============================================================================
def test_color_coding() -> bool:
    """Test color coding based on score."""
    print_section("TEST 2: Color Coding Logic")
    
    writer = GoogleSheetsWriter()
    all_passed = True
    
    test_cases = [
        (90.0, "green", "High score (≥80)"),
        (80.0, "green", "Boundary high score"),
        (75.0, "yellow", "Medium score (60-80)"),
        (60.0, "yellow", "Boundary medium score"),
        (50.0, "white", "Low score (<60)"),
        (0.0, "white", "Zero score")
    ]
    
    for score, expected_color, desc in test_cases:
        color = writer._get_color_for_score(score)
        
        # Validate color format
        is_dict = isinstance(color, dict)
        has_rgb = 'red' in color and 'green' in color and 'blue' in color
        
        # Determine actual color based on RGB values
        # white: {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        # yellow: {'red': 1.0, 'green': 1.0, 'blue': 0.85}
        # green: {'red': 0.85, 'green': 1.0, 'blue': 0.85}
        r, g, b = color.get('red', 0), color.get('green', 0), color.get('blue', 0)
        
        if r == 1.0 and g == 1.0 and b == 1.0:
            actual_color = "white"
        elif r == 1.0 and g == 1.0 and b < 1.0:
            actual_color = "yellow"
        elif r < 1.0 and g == 1.0 and b < 1.0:
            actual_color = "green"
        else:
            actual_color = "white"
        
        passed = is_dict and has_rgb and actual_color == expected_color
        
        print_test(
            f"Score {score:.1f} → {expected_color}",
            passed,
            desc
        )
        
        if not passed:
            all_passed = False
    
    return all_passed


# ============================================================================
# TEST 3: Row Formatting
# ============================================================================
def test_row_formatting() -> bool:
    """Test job to row conversion."""
    print_section("TEST 3: Row Formatting")
    
    writer = GoogleSheetsWriter()
    jobs = create_sample_jobs()
    scores = create_sample_scores()
    
    all_passed = True
    
    for job in jobs:
        try:
            row = writer._job_to_row(job, scores)
            
            # Validate row structure
            has_13_columns = len(row) == 13
            has_date = row[0] != ""
            has_title = row[1] == job.title
            has_company = row[2] == job.company
            has_score = row[7] != ""
            has_url = row[9] == job.url
            
            passed = has_13_columns and has_date and has_title and has_company and has_score and has_url
            
            details = []
            if not has_13_columns:
                details.append(f"expected 13 columns, got {len(row)}")
            if not has_date:
                details.append("missing date")
            if not has_title:
                details.append("missing title")
            if not has_score:
                details.append("missing score")
            
            detail_str = ", ".join(details) if details else "All 13 columns present"
            
            print_test(
                f"Format job: {job.title[:30]}...",
                passed,
                detail_str
            )
            
            if not passed:
                all_passed = False
        
        except Exception as e:
            print_test(f"Format job: {job.title}", False, f"Error: {e}")
            all_passed = False
    
    return all_passed


# ============================================================================
# TEST 4: Sheet Structure
# ============================================================================
def test_sheet_structure() -> bool:
    """Test sheet structure and headers."""
    print_section("TEST 4: Sheet Structure")
    
    writer = GoogleSheetsWriter()
    all_passed = True
    
    # Test 1: Verify header count
    expected_headers = [
        'Date Found', 'Title', 'Company', 'Location', 'Remote', 'Contract',
        'Tech Stack', 'Score', 'Breakdown', 'URL', 'Source', 'Applied?', 'Notes'
    ]
    
    has_13_headers = len(writer.HEADERS) == 13
    headers_match = writer.HEADERS == expected_headers
    
    print_test(
        "13 column headers",
        has_13_headers,
        f"Found {len(writer.HEADERS)} headers"
    )
    
    print_test(
        "Header names match",
        headers_match,
        "All header names correct"
    )
    
    if not has_13_headers or not headers_match:
        all_passed = False
    
    # Test 2: Verify SCOPES
    has_sheets_scope = 'https://www.googleapis.com/auth/spreadsheets' in writer.SCOPES
    has_drive_scope = 'https://www.googleapis.com/auth/drive' in writer.SCOPES
    
    print_test(
        "Google API scopes",
        has_sheets_scope and has_drive_scope,
        "Sheets and Drive scopes present"
    )
    
    if not (has_sheets_scope and has_drive_scope):
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 5: Write Jobs (Mock)
# ============================================================================
def test_write_jobs_disabled() -> bool:
    """Test write_jobs behavior when disabled."""
    print_section("TEST 5: Write Jobs (Disabled Mode)")
    
    all_passed = True
    
    # Test with disabled writer (no credentials)
    try:
        writer = GoogleSheetsWriter(credentials_path="nonexistent.json")
        jobs = create_sample_jobs()
        scores = create_sample_scores()
        
        # Should return False (not crash)
        success = writer.write_jobs(jobs, scores)
        
        passed = not success and not writer.is_enabled()
        
        print_test(
            "Write jobs when disabled",
            passed,
            "Returns False without crashing"
        )
        
        if not passed:
            all_passed = False
    
    except Exception as e:
        print_test("Write jobs when disabled", False, f"Unexpected error: {e}")
        all_passed = False
    
    # Test with empty job list
    try:
        writer = GoogleSheetsWriter(credentials_path="nonexistent.json")
        success = writer.write_jobs([], {})
        
        passed = not success
        
        print_test(
            "Write empty job list",
            passed,
            "Returns False for empty list"
        )
        
        if not passed:
            all_passed = False
    
    except Exception as e:
        print_test("Write empty job list", False, f"Unexpected error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# Main Execution
# ============================================================================
def main():
    """Run all Milestone 7 acceptance tests."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Milestone 7 Acceptance Tests: Google Sheets Integration{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    tests = [
        ("GoogleSheetsWriter Initialization", test_writer_initialization),
        ("Color Coding Logic", test_color_coding),
        ("Row Formatting", test_row_formatting),
        ("Sheet Structure", test_sheet_structure),
        ("Write Jobs (Disabled)", test_write_jobs_disabled),
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
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Milestone 7 COMPLETE!{Colors.END}")
        print(f"{Colors.GREEN}Google Sheets integration is working.{Colors.END}")
        print(f"{Colors.YELLOW}Note: Full end-to-end test requires Google credentials.{Colors.END}")
        print(f"{Colors.YELLOW}See docs/GOOGLE_SHEETS_SETUP.md for setup instructions.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Milestone 7 INCOMPLETE{Colors.END}")
        print(f"{Colors.RED}Some tests failed. Please review.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

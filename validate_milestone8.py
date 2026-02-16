"""
Milestone 8 Acceptance Tests: GitHub Actions Deployment

Tests validate GitHub Actions workflow configuration:
- Workflow file exists and is valid YAML
- Schedule configured correctly (cron)
- Manual trigger enabled (workflow_dispatch)
- All required steps present
- Secrets usage correct
- Caching configured
- Logs uploaded as artifacts

Run: python validate_milestone8.py
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List


# ============================================================================
# Terminal Colors
# ============================================================================
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


# ============================================================================
# Helper Functions
# ============================================================================
def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print('=' * 70 + '\n')


def print_test(name: str, passed: bool, detail: str = ""):
    """Print test result."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} {name}")
    if detail:
        print(f"      {detail}")


# ============================================================================
# TEST 1: Workflow File Exists
# ============================================================================
def test_workflow_file_exists() -> bool:
    """Test that workflow file exists and is valid YAML."""
    print_section("TEST 1: Workflow File Exists")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    # Test 1.1: File exists
    try:
        file_exists = workflow_path.exists()
        print_test(
            "Workflow file exists",
            file_exists,
            f"Path: {workflow_path}"
        )
        if not file_exists:
            all_passed = False
            return all_passed
    except Exception as e:
        print_test("Workflow file exists", False, f"Error: {e}")
        return False
    
    # Test 1.2: Valid YAML
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
        
        is_valid = isinstance(workflow, dict)
        print_test(
            "Valid YAML format",
            is_valid,
            f"Parsed as {type(workflow).__name__}"
        )
        if not is_valid:
            all_passed = False
    except Exception as e:
        print_test("Valid YAML format", False, f"Parse error: {e}")
        all_passed = False
    
    # Test 1.3: Has name
    try:
        has_name = 'name' in workflow and len(workflow['name']) > 0
        print_test(
            "Workflow has name",
            has_name,
            f"Name: {workflow.get('name', 'N/A')}"
        )
        if not has_name:
            all_passed = False
    except Exception as e:
        print_test("Workflow has name", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 2: Schedule Configuration
# ============================================================================
def test_schedule_configuration() -> bool:
    """Test schedule and manual trigger configuration."""
    print_section("TEST 2: Schedule Configuration")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
        
        # YAML parser may convert 'on' to True (boolean)
        # Check both 'on' and True keys
        on_config = workflow.get('on', workflow.get(True, {}))
        
        # Test 2.1: Schedule exists
        has_schedule = 'schedule' in on_config
        print_test(
            "Schedule configured",
            has_schedule,
            "Workflow will run on schedule"
        )
        if not has_schedule:
            all_passed = False
        
        # Test 2.2: Cron expression present
        if has_schedule:
            schedule_list = on_config['schedule']
            has_cron = (
                isinstance(schedule_list, list) and
                len(schedule_list) > 0 and
                'cron' in schedule_list[0]
            )
            cron_expr = schedule_list[0].get('cron', '') if has_cron else ''
            print_test(
                "Cron expression present",
                has_cron,
                f"Cron: {cron_expr}"
            )
            if not has_cron:
                all_passed = False
        
        # Test 2.3: Manual trigger enabled (workflow_dispatch)
        has_dispatch = 'workflow_dispatch' in on_config
        print_test(
            "Manual trigger enabled",
            has_dispatch,
            "workflow_dispatch present"
        )
        if not has_dispatch:
            all_passed = False
        
        # Test 2.4: Manual trigger has inputs (optional but good practice)
        if has_dispatch:
            dispatch_config = on_config['workflow_dispatch']
            has_inputs = 'inputs' in dispatch_config if isinstance(dispatch_config, dict) else False
            print_test(
                "Manual trigger has inputs",
                has_inputs,
                f"Custom parameters: {list(dispatch_config.get('inputs', {}).keys()) if has_inputs else []}"
            )
            # This is optional, don't fail if missing
    
    except Exception as e:
        print_test("Schedule configuration", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 3: Job Configuration
# ============================================================================
def test_job_configuration() -> bool:
    """Test job configuration and steps."""
    print_section("TEST 3: Job Configuration")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
        
        jobs = workflow.get('jobs', {})
        
        # Test 3.1: Has at least one job
        has_jobs = len(jobs) > 0
        print_test(
            "Has jobs defined",
            has_jobs,
            f"Jobs: {list(jobs.keys())}"
        )
        if not has_jobs:
            all_passed = False
            return all_passed
        
        # Get first job (should be scrape-jobs)
        job_name = list(jobs.keys())[0]
        job = jobs[job_name]
        
        # Test 3.2: Job runs on ubuntu-latest
        runs_on = job.get('runs-on', '')
        is_ubuntu = 'ubuntu' in runs_on.lower()
        print_test(
            "Runs on Ubuntu",
            is_ubuntu,
            f"runs-on: {runs_on}"
        )
        if not is_ubuntu:
            all_passed = False
        
        # Test 3.3: Has timeout configured
        has_timeout = 'timeout-minutes' in job
        timeout = job.get('timeout-minutes', 0)
        print_test(
            "Timeout configured",
            has_timeout,
            f"Timeout: {timeout} minutes"
        )
        if not has_timeout:
            all_passed = False
        
        # Test 3.4: Has steps
        steps = job.get('steps', [])
        has_steps = len(steps) > 0
        print_test(
            "Has steps defined",
            has_steps,
            f"Steps: {len(steps)}"
        )
        if not has_steps:
            all_passed = False
    
    except Exception as e:
        print_test("Job configuration", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 4: Required Steps Present
# ============================================================================
def test_required_steps() -> bool:
    """Test that all required steps are present."""
    print_section("TEST 4: Required Steps Present")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    # Required step keywords (flexible matching)
    required_steps = {
        'checkout': ['checkout', 'actions/checkout'],
        'python': ['python', 'setup-python'],
        'dependencies': ['install', 'dependencies', 'requirements'],
        'playwright': ['playwright', 'browser'],
        'credentials': ['credentials', 'google', 'sheets'],
        'scraper': ['main.py', 'scraper', 'run'],
        'logs': ['upload', 'artifact', 'logs'],
        'cleanup': ['clean', 'rm', 'credentials']
    }
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
        
        jobs = workflow.get('jobs', {})
        job_name = list(jobs.keys())[0]
        job = jobs[job_name]
        steps = job.get('steps', [])
        
        # Convert steps to searchable format
        step_text = ' '.join([
            str(step.get('name', '')) + ' ' + 
            str(step.get('run', '')) + ' ' + 
            str(step.get('uses', ''))
            for step in steps
        ]).lower()
        
        # Check each required step
        for step_name, keywords in required_steps.items():
            found = any(keyword.lower() in step_text for keyword in keywords)
            print_test(
                f"Step: {step_name.capitalize()}",
                found,
                f"Keywords: {', '.join(keywords)}"
            )
            if not found:
                all_passed = False
    
    except Exception as e:
        print_test("Required steps", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 5: Secrets Usage
# ============================================================================
def test_secrets_usage() -> bool:
    """Test that secrets are properly used."""
    print_section("TEST 5: Secrets Usage")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
        
        # Test 5.1: Uses secrets
        uses_secrets = 'secrets.' in workflow_content
        print_test(
            "Uses GitHub Secrets",
            uses_secrets,
            "Secrets referenced in workflow"
        )
        if not uses_secrets:
            all_passed = False
        
        # Test 5.2: Google Sheets credentials secret
        has_google_secret = 'GOOGLE_SHEETS_CREDENTIALS' in workflow_content or 'GOOGLE_CREDENTIALS' in workflow_content
        print_test(
            "Google Sheets secret referenced",
            has_google_secret,
            "Secret: GOOGLE_SHEETS_CREDENTIALS or similar"
        )
        if not has_google_secret:
            all_passed = False
        
        # Test 5.3: Credentials cleanup (security)
        has_cleanup = 'rm' in workflow_content and 'google_credentials.json' in workflow_content
        print_test(
            "Credentials cleanup present",
            has_cleanup,
            "Removes credentials after use"
        )
        if not has_cleanup:
            all_passed = False
        
        # Test 5.4: Cleanup runs always (even on failure)
        workflow = yaml.safe_load(workflow_content)
        jobs = workflow.get('jobs', {})
        job_name = list(jobs.keys())[0]
        job = jobs[job_name]
        steps = job.get('steps', [])
        
        cleanup_always = False
        for step in steps:
            step_text = str(step.get('run', '')).lower()
            if 'rm' in step_text and 'google_credentials' in step_text:
                if_condition = step.get('if', '')
                cleanup_always = 'always()' in if_condition
                break
        
        print_test(
            "Cleanup runs always",
            cleanup_always,
            "if: always() present"
        )
        if not cleanup_always:
            all_passed = False
    
    except Exception as e:
        print_test("Secrets usage", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 6: Caching Configured
# ============================================================================
def test_caching_configured() -> bool:
    """Test that caching is properly configured."""
    print_section("TEST 6: Caching Configured")
    
    workflow_path = Path('.github/workflows/daily_scraper.yml')
    all_passed = True
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
            workflow = yaml.safe_load(workflow_content)
        
        # Test 6.1: Pip caching via setup-python
        has_pip_cache = 'cache: ' in workflow_content and 'pip' in workflow_content
        print_test(
            "Pip caching enabled",
            has_pip_cache,
            "setup-python with cache: 'pip'"
        )
        if not has_pip_cache:
            all_passed = False
        
        # Test 6.2: Playwright browser caching
        has_playwright_cache = 'actions/cache' in workflow_content and 'playwright' in workflow_content.lower()
        print_test(
            "Playwright caching enabled",
            has_playwright_cache,
            "actions/cache for Playwright browsers"
        )
        if not has_playwright_cache:
            all_passed = False
        
        # Test 6.3: Cache key includes dependencies hash
        has_cache_key = 'hashFiles' in workflow_content or 'requirements' in workflow_content
        print_test(
            "Cache key includes dependencies",
            has_cache_key,
            "hashFiles() or requirements in cache key"
        )
        if not has_cache_key:
            all_passed = False
    
    except Exception as e:
        print_test("Caching configuration", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


# ============================================================================
# TEST 7: Documentation Exists
# ============================================================================
def test_documentation_exists() -> bool:
    """Test that GitHub Actions documentation exists."""
    print_section("TEST 7: Documentation Exists")
    
    all_passed = True
    
    # Test 7.1: Setup guide exists
    setup_doc_path = Path('docs/GITHUB_ACTIONS_SETUP.md')
    doc_exists = setup_doc_path.exists()
    print_test(
        "Setup documentation exists",
        doc_exists,
        f"Path: {setup_doc_path}"
    )
    if not doc_exists:
        all_passed = False
    
    # Test 7.2: Documentation has content
    if doc_exists:
        try:
            with open(setup_doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_content = len(content) > 1000
            print_test(
                "Documentation has content",
                has_content,
                f"Size: {len(content)} characters"
            )
            if not has_content:
                all_passed = False
            
            # Test 7.3: Key sections present
            key_sections = [
                'prerequisites',
                'setup',
                'secrets',
                'schedule',
                'troubleshooting'
            ]
            content_lower = content.lower()
            
            for section in key_sections:
                has_section = section in content_lower
                print_test(
                    f"Has '{section}' section",
                    has_section,
                    f"Found in documentation"
                )
                if not has_section:
                    all_passed = False
        
        except Exception as e:
            print_test("Documentation content", False, f"Error: {e}")
            all_passed = False
    
    return all_passed


# ============================================================================
# Main
# ============================================================================
def main():
    """Run all acceptance tests."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}")
    print("Milestone 8 Acceptance Tests: GitHub Actions Deployment")
    print('=' * 70 + RESET)
    
    # Run tests
    tests = [
        ("Workflow File Exists", test_workflow_file_exists),
        ("Schedule Configuration", test_schedule_configuration),
        ("Job Configuration", test_job_configuration),
        ("Required Steps Present", test_required_steps),
        ("Secrets Usage", test_secrets_usage),
        ("Caching Configured", test_caching_configured),
        ("Documentation Exists", test_documentation_exists)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Summary
    print_section("Summary")
    
    for test_name, passed in results.items():
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"{status} {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n{BOLD}Results: {passed_count}/{total_count} tests passed{RESET}\n")
    
    if all(results.values()):
        print(f"{GREEN}{BOLD}✓ Milestone 8 COMPLETE!{RESET}")
        print("GitHub Actions workflow is properly configured.")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print("1. Push code to GitHub")
        print("2. Configure GOOGLE_SHEETS_CREDENTIALS secret")
        print("3. Manually trigger workflow to test")
        print("4. Wait for scheduled run (09:00 CET)")
        print("5. Monitor workflow runs in Actions tab")
        print(f"See {BLUE}docs/GITHUB_ACTIONS_SETUP.md{RESET} for detailed instructions.\n")
        return 0
    else:
        print(f"{RED}{BOLD}✗ Milestone 8 INCOMPLETE{RESET}")
        print("Some tests failed. Please review.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

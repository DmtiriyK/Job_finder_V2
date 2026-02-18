"""
Test script for RemoteDetector.

Tests HTML attribute parsing and pattern matching.
"""

from bs4 import BeautifulSoup
from utils.remote_detector import get_remote_detector


def test_stepstone_html():
    """Test StepStone HTML attribute detection."""
    print("=" * 80)
    print("Testing StepStone HTML Attribute Detection")
    print("=" * 80)
    
    detector = get_remote_detector()
    
    # Test case 1: "Teilweise Home-Office" (Hybrid)
    html_hybrid = """
    <div class="job-container">
        <span data-at="job-item-work-from-home">Teilweise Home-Office</span>
        <h3>Full Stack Developer</h3>
    </div>
    """
    soup_hybrid = BeautifulSoup(html_hybrid, 'html.parser')
    result_hybrid = detector.detect(
        title="Full Stack Developer",
        description="Great opportunity",
        location="Deutschland",
        html_element=soup_hybrid.find('div'),
        source="stepstone"
    )
    print(f"\nTest 1 - 'Teilweise Home-Office' attribute:")
    print(f"  Expected: Hybrid")
    print(f"  Got: {result_hybrid}")
    print(f"  ✅ PASS" if result_hybrid == "Hybrid" else f"  ❌ FAIL")
    
    # Test case 2: "Homeoffice möglich" (Remote)
    html_remote = """
    <div class="job-container">
        <span data-at="job-item-work-from-home">Homeoffice möglich</span>
        <h3>Backend Developer</h3>
    </div>
    """
    soup_remote = BeautifulSoup(html_remote, 'html.parser')
    result_remote = detector.detect(
        title="Backend Developer",
        description="100% remote position",
        location="Deutschland",
        html_element=soup_remote.find('div'),
        source="stepstone"
    )
    print(f"\nTest 2 - 'Homeoffice möglich' attribute:")
    print(f"  Expected: Remote")
    print(f"  Got: {result_remote}")
    print(f"  ✅ PASS" if result_remote == "Remote" else f"  ❌ FAIL")
    
    # Test case 3: No attribute, but "100% remote" in title (pattern matching)
    html_no_attr = """
    <div class="job-container">
        <h3>Full Stack Developer (100% remote)</h3>
    </div>
    """
    soup_no_attr = BeautifulSoup(html_no_attr, 'html.parser')
    result_pattern = detector.detect(
        title="Full Stack Developer (100% remote)",
        description="Great opportunity",
        location="Deutschland",
        html_element=soup_no_attr.find('div'),
        source="stepstone"
    )
    print(f"\nTest 3 - No attribute, '100% remote' in title (pattern):")
    print(f"  Expected: Remote")
    print(f"  Got: {result_pattern}")
    print(f"  ✅ PASS" if result_pattern == "Remote" else f"  ❌ FAIL")


def test_xing_html():
    """Test XING HTML detection."""
    print("\n" + "=" * 80)
    print("Testing XING HTML Detection")
    print("=" * 80)
    
    detector = get_remote_detector()
    
    # Test case 1: "Keine Kernarbeitszeit, Homeoffice"
    html_remote = """
    <div class="job-card">
        <ul>
            <li>Keine Kernarbeitszeit, Homeoffice und ortsunabhängiges Arbeiten</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html_remote, 'html.parser')
    result = detector.detect(
        title="Software Developer",
        description="",
        location="Berlin",
        html_element=soup.find('div'),
        source="xing"
    )
    print(f"\nTest 1 - 'Keine Kernarbeitszeit, Homeoffice' text:")
    print(f"  Expected: Remote")
    print(f"  Got: {result}")
    print(f"  ✅ PASS" if result == "Remote" else f"  ❌ FAIL")
    
    # Test case 2: "Hybrid" keyword
    html_hybrid = """
    <div class="job-card">
        <span>Hybrid working model</span>
    </div>
    """
    soup_hybrid = BeautifulSoup(html_hybrid, 'html.parser')
    result_hybrid = detector.detect(
        title="Java Developer",
        description="",
        location="München",
        html_element=soup_hybrid.find('div'),
        source="xing"
    )
    print(f"\nTest 2 - 'Hybrid' keyword:")
    print(f"  Expected: Hybrid")
    print(f"  Got: {result_hybrid}")
    print(f"  ✅ PASS" if result_hybrid == "Hybrid" else f"  ❌ FAIL")


def test_pattern_matching():
    """Test YAML pattern matching."""
    print("\n" + "=" * 80)
    print("Testing YAML Pattern Matching (No HTML)")
    print("=" * 80)
    
    detector = get_remote_detector()
    
    test_cases = [
        ("vollständig remote", "Remote"),
        ("komplett remote", "Remote"),
        ("ortsunabhängig arbeiten", "Remote"),
        ("flexible remote Arbeit", "Hybrid"),
        ("teilweise remote möglich", "Hybrid"),
        ("keine remote Arbeit", "Onsite"),
    ]
    
    for text, expected in test_cases:
        result = detector.detect(
            title=text,
            description="",
            location="Deutschland",
            html_element=None,
            source=None
        )
        status = "✅ PASS" if result == expected else f"❌ FAIL"
        print(f"\n  Text: '{text}'")
        print(f"  Expected: {expected}, Got: {result} {status}")


if __name__ == "__main__":
    test_stepstone_html()
    test_xing_html()
    test_pattern_matching()
    
    print("\n" + "=" * 80)
    print("Test Suite Complete")
    print("=" * 80)

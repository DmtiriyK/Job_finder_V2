"""
Validation script for Milestone 4: Scoring Engine Complete.

Tests acceptance criteria:
- Individual scoring components work correctly
- ScoreAggregator combines all 5 components
- Normalization logic handles edge cases
- Final scores always in range 0-100
- Component weights sum to 100
"""

from datetime import datetime
from scorers.components.tfidf_component import TfidfComponent
from scorers.components.tech_stack_component import TechStackComponent
from scorers.components.remote_component import RemoteComponent
from scorers.components.keyword_component import KeywordComponent
from scorers.components.contract_component import ContractComponent
from scorers.aggregator import ScoreAggregator
from models.job import Job
from config.settings import Settings


def print_test_header(test_name: str):
    """Print formatted test header."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")


def test_tech_stack_component():
    """Test TechStackComponent with sample job."""
    print_test_header("TechStackComponent - Individual scoring")
    
    component = TechStackComponent()
    settings = Settings()
    profile = settings.load_profile()
    
    job = Job(
        id="test_tech",
        title="Full Stack Engineer",
        company="Test Company",
        location="Berlin",
        remote_type="Full Remote",
        url="https://test.com",
        description="React, TypeScript, .NET Core, Docker, PostgreSQL",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["React", "TypeScript", ".NET Core", "Docker", "PostgreSQL"]
    )
    
    result = component.calculate(job, profile)
    
    print(f"✓ Tech Stack Score: {result.score}/{result.max_score}")
    print(f"✓ Raw Score: {result.raw_score}")
    print(f"✓ Explanation: {result.explanation}")
    print(f"✓ Details: {result.details}")
    
    # Assertions
    assert 0 <= result.score <= 30, f"Score {result.score} outside valid range [0, 30]"
    assert result.explanation != "", "Explanation should not be empty"
    assert result.max_score == 30, f"Max score should be 30, got {result.max_score}"
    
    print(f"\n✅ TechStackComponent test PASSED")
    return True


def test_remote_component():
    """Test RemoteComponent normalization."""
    print_test_header("RemoteComponent - Normalization ranges")
    
    component = RemoteComponent()
    settings = Settings()
    profile = settings.load_profile()
    
    # Test 1: Full remote (should give max score)
    job_remote = Job(
        id="test_remote",
        title="Senior Engineer - Full Remote",
        company="RemoteCo",
        location="Germany",
        remote_type="Full Remote",
        url="https://test.com",
        description="100% remote, work from anywhere",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["Python"]
    )
    
    result_remote = component.calculate(job_remote, profile)
    print(f"✓ Full Remote Score: {result_remote.score}/{result_remote.max_score}")
    print(f"  Raw: {result_remote.raw_score}, Normalized: {result_remote.score}")
    
    # Test 2: Onsite required (should give min score)
    job_onsite = Job(
        id="test_onsite",
        title="Engineer - Onsite Only",
        company="OfficeCo",
        location="Berlin",
        remote_type="Onsite",
        url="https://test.com",
        description="Onsite only, vor Ort required",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["Python"]
    )
    
    result_onsite = component.calculate(job_onsite, profile)
    print(f"✓ Onsite Required Score: {result_onsite.score}/{result_onsite.max_score}")
    print(f"  Raw: {result_onsite.raw_score}, Normalized: {result_onsite.score}")
    
    # Assertions
    assert result_remote.score == 15.0, f"Full remote should give 15, got {result_remote.score}"
    assert result_onsite.score == 0.0, f"Onsite only should give 0, got {result_onsite.score}"
    
    print(f"\n✅ RemoteComponent normalization test PASSED")
    return True


def test_score_aggregator():
    """Test ScoreAggregator with perfect match job."""
    print_test_header("ScoreAggregator - Full pipeline")
    
    settings = Settings()
    profile = settings.load_profile()
    
    # Perfect match job
    job = Job(
        id="test_perfect",
        title="Senior Full Stack Engineer - Remote",
        company="Perfect Company",
        location="Germany",
        remote_type="Full Remote",
        contract_type="Freiberuflich",
        url="https://test.com",
        description=(
            profile.profile_text + 
            " Remote-first company with flexible arbeitszeiten. "
            "Modern technologies and great team."
        ),
        posted_date=datetime.now(),
        source="test",
        tech_stack=["C#", ".NET Core", "React", "TypeScript", "Docker", 
                   "PostgreSQL", "Microservices"]
    )
    
    aggregator = ScoreAggregator()
    result = aggregator.score_job(job, profile)
    
    print(f"\n✓ Final Score: {result.score:.2f}/100")
    print(f"\n✓ Breakdown by component:")
    for component, values in result.breakdown.items():
        print(f"  • {component:12} → raw: {values['raw']:6.2f}, "
              f"normalized: {values['normalized']:5.2f}, max: {values['max']:2.0f}")
    
    # Verify component weights
    component_sum = sum(v['normalized'] for v in result.breakdown.values())
    print(f"\n✓ Component sum: {component_sum:.2f} (should equal final score)")
    
    # Assertions
    assert 0 <= result.score <= 100, f"Score {result.score} outside valid range [0, 100]"
    assert abs(component_sum - result.score) < 0.01, \
        f"Component sum {component_sum} != final score {result.score}"
    assert len(result.breakdown) == 5, f"Should have 5 components, got {len(result.breakdown)}"
    
    # Verify weights sum to 100
    weights = aggregator.get_component_weights()
    weight_sum = sum(weights.values())
    print(f"\n✓ Component weights sum: {weight_sum} (should be 100)")
    assert weight_sum == 100, f"Component weights sum to {weight_sum}, expected 100"
    
    print(f"\n✅ ScoreAggregator test PASSED")
    return True


def test_edge_cases():
    """Test edge cases for scoring."""
    print_test_header("Edge Cases - Negative scores, capping, flooring")
    
    settings = Settings()
    profile = settings.load_profile()
    
    # Job with negative keywords and negative tech
    job_poor = Job(
        id="test_poor",
        title="SAP Developer - Onsite Only",
        company="OldCo",
        location="Berlin",
        remote_type="Onsite Required",
        contract_type="Praktikum",
        url="https://test.com",
        description="SAP, ABAP, COBOL, vor Ort required, onsite only",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["SAP", "ABAP", "COBOL"]
    )
    
    aggregator = ScoreAggregator()
    result = aggregator.score_job(job_poor, profile)
    
    print(f"✓ Poor Match Score: {result.score:.2f}/100")
    print(f"\n✓ Breakdown:")
    for component, values in result.breakdown.items():
        print(f"  • {component:12} → raw: {values['raw']:6.2f}, "
              f"normalized: {values['normalized']:5.2f}")
    
    # Assertions
    assert 0 <= result.score <= 100, f"Score {result.score} outside valid range"
    assert result.score < 50, f"Poor match should score <50, got {result.score}"
    
    # Check that negative raw scores normalized to 0
    assert result.breakdown['remote']['normalized'] >= 0, "Remote score should be >= 0"
    assert result.breakdown['contract']['normalized'] >= 0, "Contract score should be >= 0"
    
    print(f"\n✅ Edge cases test PASSED")
    return True


def test_contract_component():
    """Test ContractComponent normalization."""
    print_test_header("ContractComponent - Normalization [-5, 2] → [0, 5]")
    
    component = ContractComponent()
    settings = Settings()
    profile = settings.load_profile()
    
    # Test freelance contract (should give max)
    job_freelance = Job(
        id="test_freelance",
        title="Freelance Developer",
        company="FreelanceCo",
        location="Germany",
        remote_type="Remote",
        contract_type="Freiberuflich",
        url="https://test.com",
        description="Freelance position",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["Python"]
    )
    
    result_freelance = component.calculate(job_freelance, profile)
    print(f"✓ Freelance Contract: {result_freelance.score}/{result_freelance.max_score}")
    print(f"  Raw: {result_freelance.raw_score}, Normalized: {result_freelance.score}")
    
    # Test praktikum (should give min)
    job_praktikum = Job(
        id="test_praktikum",
        title="Praktikant",
        company="InternCo",
        location="Germany",
        remote_type="Remote",
        contract_type="Praktikum",
        url="https://test.com",
        description="Praktikum position",
        posted_date=datetime.now(),
        source="test",
        tech_stack=["Python"]
    )
    
    result_praktikum = component.calculate(job_praktikum, profile)
    print(f"✓ Praktikum Contract: {result_praktikum.score}/{result_praktikum.max_score}")
    print(f"  Raw: {result_praktikum.raw_score}, Normalized: {result_praktikum.score}")
    
    # Assertions
    assert result_freelance.score == 5.0, f"Freelance should give 5, got {result_freelance.score}"
    assert result_praktikum.score == 0.0, f"Praktikum should give 0, got {result_praktikum.score}"
    
    print(f"\n✅ ContractComponent normalization test PASSED")
    return True


def main():
    """Run all Milestone 4 validation tests."""
    print(f"\n{'#'*70}")
    print(f"# MILESTONE 4 VALIDATION: Scoring Engine Complete")
    print(f"{'#'*70}")
    
    tests = [
        test_tech_stack_component,
        test_remote_component,
        test_contract_component,
        test_score_aggregator,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(tests)}")
    
    if passed == len(tests):
        print(f"\n🎉 ALL TESTS PASSED! Milestone 4 is COMPLETE!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())

"""Tests for scoring components and aggregator."""

import pytest
from datetime import datetime
from models.job import Job
from models.profile import Profile
from scorers.components import (
    TfidfComponent,
    TechStackComponent,
    RemoteComponent,
    KeywordComponent,
    ContractComponent
)
from scorers.aggregator import ScoreAggregator
from config.settings import Settings


@pytest.fixture
def settings():
    """Load settings."""
    return Settings()


@pytest.fixture
def profile(settings):
    """Load user profile."""
    return settings.load_profile()


@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    return Job(
        id="test-job-1",
        title="Full Stack Engineer",
        company="Test Company GmbH",
        location="Berlin, Germany",
        remote_type="Full Remote",
        contract_type="Festanstellung",
        url="https://test.com/job/1",
        description="""
        We're looking for a Full Stack Engineer with experience in React, 
        TypeScript, and .NET Core. You'll build scalable APIs with Docker 
        and PostgreSQL. Remote work from Germany. Flexible working hours.
        Modern technologies and great team culture.
        """,
        posted_date=datetime.now(),
        source="test",
        tech_stack=["React", "TypeScript", ".NET Core", "Docker", "PostgreSQL"]
    )


class TestTfidfComponent:
    """Tests for TF-IDF similarity component."""
    
    def test_component_initialization(self):
        """Test component initializes correctly."""
        component = TfidfComponent(max_score=40.0)
        assert component.max_score == 40.0
        assert component.matcher is not None
    
    def test_calculate_score(self, sample_job, profile):
        """Test TF-IDF score calculation."""
        component = TfidfComponent(max_score=40.0)
        result = component.calculate(sample_job, profile)
        
        assert 0 <= result.score <= 40.0
        assert 0 <= result.raw_score <= 1.0
        assert result.max_score == 40.0
        assert result.explanation != ""
        assert 'similarity' in result.details
    
    def test_high_similarity(self, profile):
        """Test job with high profile similarity."""
        job = Job(
            id="test",
            title="Senior .NET Developer",
            company="Test",
            location="Remote",
            url="https://test.com",
            description=profile.profile_text,  # Exact match
            posted_date=datetime.now(),
            source="test",
            tech_stack=[]
        )
        
        component = TfidfComponent(max_score=40.0)
        result = component.calculate(job, profile)
        
        # Should have perfect similarity
        assert result.raw_score >= 0.9
        assert result.score >= 36.0  # 0.9 * 40


class TestTechStackComponent:
    """Tests for tech stack matching component."""
    
    def test_component_initialization(self):
        """Test component initializes with scoring rules."""
        component = TechStackComponent(max_score=30.0)
        assert component.max_score == 30.0
        assert len(component.tech_scores) > 0
        
        # Check some known techs
        assert 'c#' in component.tech_scores
        assert 'react' in component.tech_scores
        assert component.tech_scores['c#'] == 5
        assert component.tech_scores['react'] == 5
    
    def test_calculate_score(self, sample_job, profile):
        """Test tech stack score calculation."""
        component = TechStackComponent(max_score=30.0)
        result = component.calculate(sample_job, profile)
        
        assert 0 <= result.score <= 30.0
        assert result.max_score == 30.0
        assert result.explanation != ""
        assert 'matched_tech' in result.details
    
    def test_high_value_tech(self, profile):
        """Test job with high-value tech stack."""
        job = Job(
            id="test",
            title=".NET Developer",
            company="Test",
            location="Remote",
            url="https://test.com",
            description="C# and .NET Core developer",
            posted_date=datetime.now(),
            source="test",
            tech_stack=["C#", ".NET Core", "React", "TypeScript", "Docker"]
        )
        
        component = TechStackComponent(max_score=30.0)
        result = component.calculate(job, profile)
        
        # C#:5 + .NET Core:5 + React:5 + TypeScript:4 + Docker:4 = 23
        assert result.raw_score >= 20
        assert result.score >= 20
        assert len(result.details['matched_tech']) == 5
    
    def test_negative_tech(self, profile):
        """Test job with negative tech (SAP, COBOL)."""
        job = Job(
            id="test",
            title="SAP Developer",
            company="Test",
            location="Remote",
            url="https://test.com",
            description="SAP and COBOL experience required",
            posted_date=datetime.now(),
            source="test",
            tech_stack=["SAP", "COBOL"]
        )
        
        component = TechStackComponent(max_score=30.0)
        result = component.calculate(job, profile)
        
        # Both SAP and COBOL are -3 each = -6
        assert result.raw_score == -6
        # Should floor at 0 after normalization
        assert result.score == 0.0
    
    def test_score_cap_at_max(self, profile):
        """Test that score caps at max_score even if raw > max."""
        # Create job with many high-value techs
        all_high_tech = ["C#", ".NET Core", "ASP.NET", "React", "TypeScript", 
                        "Docker", "Microservices", "REST API", "PostgreSQL"]
        
        job = Job(
            id="test",
            title="Full Stack",
            company="Test",
            location="Remote",
            url="https://test.com",
            description=" ".join(all_high_tech),
            posted_date=datetime.now(),
            source="test",
            tech_stack=all_high_tech
        )
        
        component = TechStackComponent(max_score=30.0)
        result = component.calculate(job, profile)
        
        # Raw score would be > 30, but normalized should cap at 30
        assert result.raw_score > 30
        assert result.score == 30.0


class TestRemoteComponent:
    """Tests for remote type component."""
    
    def test_component_initialization(self):
        """Test component initializes with patterns."""
        component = RemoteComponent(max_score=15.0)
        assert component.max_score == 15.0
        assert len(component.patterns) > 0
    
    def test_full_remote(self, profile):
        """Test full remote job."""
        job = Job(
            id="test",
            title="Developer",
            company="Test",
            location="Remote",
            remote_type="Full Remote",
            url="https://test.com",
            description="100% remote work from Germany",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = RemoteComponent(max_score=15.0)
        result = component.calculate(job, profile)
        
        # Full remote = +5 raw → 15.0 normalized
        assert result.raw_score == 5.0
        assert result.score == 15.0
    
    def test_onsite_required(self, profile):
        """Test onsite-only job."""
        job = Job(
            id="test",
            title="Developer",
            company="Test",
            location="Berlin",
            remote_type="Onsite",
            url="https://test.com",
            description="Onsite only, 5 days per week in office",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = RemoteComponent(max_score=15.0)
        result = component.calculate(job, profile)
        
        # Onsite = -3 raw → 0.0 normalized
        assert result.raw_score == -3.0
        assert result.score == 0.0
    
    def test_normalization_range(self):
        """Test normalization maps [-3, 5] to [0, 15]."""
        component = RemoteComponent(max_score=15.0)
        
        # Test normalization
        assert component.normalize_score(-3, -3, 5) == 0.0  # Min raw → 0
        assert component.normalize_score(5, -3, 5) == 15.0  # Max raw → 15
        assert abs(component.normalize_score(0, -3, 5) - 5.625) < 0.01  # Mid


class TestKeywordComponent:
    """Tests for keywords component."""
    
    def test_component_initialization(self):
        """Test component initializes with keywords."""
        component = KeywordComponent(max_score=10.0)
        assert component.max_score == 10.0
        assert len(component.keywords) > 0
    
    def test_positive_keywords(self, profile):
        """Test job with positive keywords."""
        job = Job(
            id="test",
            title="Developer",
            company="Test",
            location="Remote",
            url="https://test.com",
            description="Remote-first company with flexible Arbeitszeiten",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = KeywordComponent(max_score=10.0)
        result = component.calculate(job, profile)
        
        # remote-first:2 + flexible arbeitszeiten:1 = 3
        assert result.raw_score >= 2.0
        assert result.score > 0
    
    def test_negative_keywords(self, profile):
        """Test job with negative keywords."""
        job = Job(
            id="test",
            title="Developer",
            company="Test",
            location="Berlin",
            url="https://test.com",
            description="Onsite only, 3-5 Tage vor Ort required",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = KeywordComponent(max_score=10.0)
        result = component.calculate(job, profile)
        
        # Should have negative raw score, but normalized floors at 0
        assert result.raw_score < 0
        assert result.score == 0.0


class TestContractComponent:
    """Tests for contract type component."""
    
    def test_component_initialization(self):
        """Test component initializes with contract types."""
        component = ContractComponent(max_score=5.0)
        assert component.max_score == 5.0
        assert len(component.contract_scores) > 0
    
    def test_freelance_contract(self, profile):
        """Test freelance/contract job."""
        job = Job(
            id="test",
            title="Freelance Developer",
            company="Test",
            location="Remote",
            contract_type="Freiberuflich",
            url="https://test.com",
            description="Freelance contract position",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = ContractComponent(max_score=5.0)
        result = component.calculate(job, profile)
        
        # Freiberuflich = +2 raw → 5.0 normalized (max)
        assert result.raw_score == 2.0
        assert result.score == 5.0
    
    def test_praktikum_contract(self, profile):
        """Test internship (negative score)."""
        job = Job(
            id="test",
            title="Praktikum",
            company="Test",
            location="Berlin",
            contract_type="Praktikum",
            url="https://test.com",
            description="Internship for students",
            posted_date=datetime.now(),
            source="test"
        )
        
        component = ContractComponent(max_score=5.0)
        result = component.calculate(job, profile)
        
        # Praktikum = -5 raw → 0.0 normalized
        assert result.raw_score == -5.0
        assert result.score == 0.0


class TestScoreAggregator:
    """Tests for score aggregator."""
    
    def test_aggregator_initialization(self):
        """Test aggregator initializes all components."""
        aggregator = ScoreAggregator()
        
        assert len(aggregator.components) == 5
        assert 'tfidf' in aggregator.components
        assert 'tech_stack' in aggregator.components
        assert 'remote' in aggregator.components
        assert 'keywords' in aggregator.components
        assert 'contract' in aggregator.components
    
    def test_component_weights_sum_to_100(self):
        """Test that all component max scores sum to 100."""
        aggregator = ScoreAggregator()
        
        weights = aggregator.get_component_weights()
        total = sum(weights.values())
        
        assert abs(total - 100.0) < 0.01
        assert aggregator.verify_total_weight() is True
    
    def test_score_job(self, sample_job, profile):
        """Test full job scoring."""
        aggregator = ScoreAggregator()
        result = aggregator.score_job(sample_job, profile)
        
        assert 0 <= result.score <= 100
        assert result.breakdown is not None
        assert len(result.breakdown) == 5
        assert result.explanation != ""
        
        # Verify breakdown structure
        for component_name, scores in result.breakdown.items():
            assert 'raw' in scores
            assert 'normalized' in scores
            assert 'max' in scores
    
    def test_score_components_sum(self, sample_job, profile):
        """Test that component scores sum to final score."""
        aggregator = ScoreAggregator()
        result = aggregator.score_job(sample_job, profile)
        
        component_sum = sum(
            result.breakdown[name]['normalized']
            for name in result.breakdown
        )
        
        # Should be equal (within floating point precision)
        assert abs(component_sum - result.score) < 0.01
    
    def test_perfect_match_job(self, profile):
        """Test job with perfect match on all components."""
        job = Job(
            id="test",
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
        
        # Should have very high score (>70)
        assert result.score > 70
        
        # Remote should be maxed (15)
        assert result.breakdown['remote']['normalized'] == 15.0
        
        # Contract should be maxed (5)
        assert result.breakdown['contract']['normalized'] == 5.0
    
    def test_poor_match_job(self, profile):
        """Test job with poor match."""
        job = Job(
            id="test",
            title="Junior SAP ABAP Praktikum",
            company="Old Corp",
            location="Berlin",
            remote_type="Onsite only",
            contract_type="Praktikum",
            url="https://test.com",
            description="SAP ABAP internship, onsite only, COBOL knowledge",
            posted_date=datetime.now(),
            source="test",
            tech_stack=["SAP", "ABAP", "COBOL"]
        )
        
        aggregator = ScoreAggregator()
        result = aggregator.score_job(job, profile)
        
        # Should have very low score (<30)
        assert result.score < 30
        
        # Remote should be 0
        assert result.breakdown['remote']['normalized'] == 0.0
        
        # Contract should be 0
        assert result.breakdown['contract']['normalized'] == 0.0
        
        # Tech stack should be 0 (negative techs floor at 0)
        assert result.breakdown['tech_stack']['normalized'] == 0.0

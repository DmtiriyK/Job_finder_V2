"""Tests for LocationComponent scorer with synonym support."""

import pytest
from datetime import datetime
from models.job import Job
from models.profile import Profile
from scorers.components.location_component import LocationComponent


@pytest.fixture
def location_scorer():
    """Create LocationComponent instance."""
    return LocationComponent(max_score=15.0)


@pytest.fixture
def basic_profile():
    """Create basic profile for testing."""
    return Profile(
        name="Test User",
        roles=["Software Engineer"],
        skills={"languages": [], "frameworks": []},
        preferences={
            'locations': ['Germany', 'Remote'],
            'min_score': 0
        },
        profile_text="Experienced software engineer looking for remote opportunities in Germany with modern tech stack"
    )


def create_job(location: str, description: str = "Test job description") -> Job:
    """Helper to create test job with specific location."""
    return Job(
        id='test-123',
        title='Software Engineer',
        company='Test Company GmbH',
        location=location,
        description=description,
        url='https://example.com',
        source='test',
        posted_date=datetime.now()
    )


class TestGermanySynonyms:
    """Test Germany location synonym matching."""
    
    def test_deutschland_synonym(self, location_scorer, basic_profile):
        """Test that 'Deutschland' matches Germany and scores 15 points."""
        job = create_job(location="Berlin, Deutschland")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0
        assert "Germany" in result.explanation
        
    def test_germany_english(self, location_scorer, basic_profile):
        """Test that 'Germany' matches and scores 15 points."""
        job = create_job(location="Munich, Germany")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0
        assert "Germany" in result.explanation
    
    def test_berlin_city(self, location_scorer, basic_profile):
        """Test that 'Berlin' alone is recognized as Germany."""
        job = create_job(location="Berlin")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0
        assert "Germany" in result.explanation
    
    def test_munich_variants(self, location_scorer, basic_profile):
        """Test that München and Munich both work."""
        job_de = create_job(location="München")
        job_en = create_job(location="Munich")
        
        result_de = location_scorer.calculate(job_de, basic_profile)
        result_en = location_scorer.calculate(job_en, basic_profile)
        
        assert result_de.score == 15.0
        assert result_en.score == 15.0
    
    def test_hamburg(self, location_scorer, basic_profile):
        """Test Hamburg city recognition."""
        job = create_job(location="Hamburg")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0
        assert "Germany" in result.explanation
    
    def test_frankfurt_am_main(self, location_scorer, basic_profile):
        """Test Frankfurt am Main recognition."""
        job = create_job(location="Frankfurt am Main, Germany")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0


class TestRemoteKeywords:
    """Test remote keyword detection."""
    
    def test_remote_only(self, location_scorer, basic_profile):
        """Test 'Remote' location gives 8 points (Other:3 + remote bonus:5)."""
        job = create_job(location="Remote")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0
        assert "Other" in result.explanation or "Remote" in result.explanation
    
    def test_fully_remote(self, location_scorer, basic_profile):
        """Test 'Fully Remote' variation."""
        job = create_job(location="Fully Remote")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0  # Other:3 + Remote bonus:5
    
    def test_homeoffice(self, location_scorer, basic_profile):
        """Test German 'Homeoffice' keyword."""
        job = create_job(location="Homeoffice")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0  # Other:3 + Remote bonus:5
    
    def test_wfh(self, location_scorer, basic_profile):
        """Test 'WFH' abbreviation."""
        job = create_job(location="WFH")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0  # Other:3 + Remote bonus:5


class TestRemoteCombo:
    """Test combinations of location + remote."""
    
    def test_berlin_remote(self, location_scorer, basic_profile):
        """Test 'Berlin, Remote' gives max 15 points (not 20)."""
        job = create_job(location="Berlin, Remote")
        result = location_scorer.calculate(job, basic_profile)
        
        # Germany (15) + Remote bonus (5) = 20, but capped at max_score=15
        assert result.score == 15.0
        assert "Germany" in result.explanation
    
    def test_deutschland_homeoffice(self, location_scorer, basic_profile):
        """Test 'Deutschland, Homeoffice' combination."""
        job = create_job(location="Deutschland, Homeoffice")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0
    
    def test_remote_in_description(self, location_scorer, basic_profile):
        """Test remote keyword detection in description when location is Germany."""
        job = create_job(
            location="München",
            description="We offer full remote work from anywhere in Germany (Homeoffice möglich)"
        )
        result = location_scorer.calculate(job, basic_profile)
        
        # Germany match (15) + remote bonus from description (+5) = 20, capped at 15
        assert result.score == 15.0


class TestNeighboringCountries:
    """Test neighboring country scoring (Austria, Switzerland, Netherlands)."""
    
    def test_vienna(self, location_scorer, basic_profile):
        """Test Vienna, Austria gives 8 points."""
        job = create_job(location="Vienna, Austria")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0
        assert "Neighboring Country" in result.explanation
    
    def test_zurich(self, location_scorer, basic_profile):
        """Test Zurich, Switzerland gives 8 points."""
        job = create_job(location="Zürich, Switzerland")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0
    
    def test_amsterdam(self, location_scorer, basic_profile):
        """Test Amsterdam, Netherlands gives 8 points."""
        job = create_job(location="Amsterdam, Netherlands")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0


class TestEuropeGeneral:
    """Test Europe and EU locations."""
    
    def test_europe_keyword(self, location_scorer, basic_profile):
        """Test 'Europe' location gives 8 points."""
        job = create_job(location="Europe")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0
        assert "Europe" in result.explanation
    
    def test_eu(self, location_scorer, basic_profile):
        """Test 'EU' abbreviation."""
        job = create_job(location="EU")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 8.0


class TestOtherLocations:
    """Test that non-target locations still get scored (not excluded)."""
    
    def test_usa(self, location_scorer, basic_profile):
        """Test USA gives 3 points (not excluded)."""
        job = create_job(location="San Francisco, USA")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 3.0
        assert "Other" in result.explanation
    
    def test_uk(self, location_scorer, basic_profile):
        """Test UK gives 3 points."""
        job = create_job(location="London, UK")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 3.0
    
    def test_asia(self, location_scorer, basic_profile):
        """Test Asian location gives 3 points."""
        job = create_job(location="Tokyo, Japan")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 3.0


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_location(self, location_scorer, basic_profile):
        """Test empty location string."""
        job = create_job(location="")
        result = location_scorer.calculate(job, basic_profile)
        
        # Empty location should still get base score
        assert result.score >= 0
    
    def test_multiple_cities(self, location_scorer, basic_profile):
        """Test location with multiple German cities."""
        job = create_job(location="Berlin, München, Hamburg")
        result = location_scorer.calculate(job, basic_profile)
        
        # Should detect at least one German city
        assert result.score >= 15.0
    
    def test_case_insensitive(self, location_scorer, basic_profile):
        """Test that matching is case-insensitive."""
        job_lower = create_job(location="berlin")
        job_upper = create_job(location="BERLIN")
        job_mixed = create_job(location="BeRlIn")
        
        result_lower = location_scorer.calculate(job_lower, basic_profile)
        result_upper = location_scorer.calculate(job_upper, basic_profile)
        result_mixed = location_scorer.calculate(job_mixed, basic_profile)
        
        assert result_lower.score == 15.0
        assert result_upper.score == 15.0
        assert result_mixed.score == 15.0
    
    def test_with_special_characters(self, location_scorer, basic_profile):
        """Test locations with special characters."""
        job = create_job(location="Düsseldorf, Nordrhein-Westfalen")
        result = location_scorer.calculate(job, basic_profile)
        
        assert result.score == 15.0  # Both city and region match

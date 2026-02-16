"""Tests for data models."""

import pytest
from datetime import datetime, timedelta
from models.job import Job, ScoreResult
from models.profile import Profile, Skill


class TestScoreResult:
    """Tests for ScoreResult model."""
    
    def test_score_result_creation(self, sample_score_result):
        """Test ScoreResult instance creation."""
        assert sample_score_result.score == 75.5
        assert len(sample_score_result.breakdown) == 5
        assert sample_score_result.explanation != ""
    
    def test_score_result_validation(self):
        """Test score validation (0-100 range)."""
        # Valid scores
        result1 = ScoreResult(score=0, breakdown={}, explanation="")
        assert result1.score == 0
        
        result2 = ScoreResult(score=100, breakdown={}, explanation="")
        assert result2.score == 100
        
        # Invalid scores
        with pytest.raises(ValueError):
            ScoreResult(score=-10, breakdown={}, explanation="")
        
        with pytest.raises(ValueError):
            ScoreResult(score=150, breakdown={}, explanation="")


class TestJob:
    """Tests for Job model."""
    
    def test_job_creation(self, sample_job):
        """Test Job instance creation."""
        assert sample_job.title == "Senior Backend Developer"
        assert sample_job.company == "Test Company GmbH"
        assert "C#" in sample_job.tech_stack
    
    def test_generate_id(self):
        """Test job ID generation from URL and title."""
        job_id = Job.generate_id(
            "https://example.com/jobs/123",
            "Backend Developer"
        )
        assert isinstance(job_id, str)
        assert len(job_id) == 64  # SHA256 hex length
    
    def test_duplicate_jobs_same_id(self):
        """Test that duplicate jobs generate same ID."""
        url = "https://example.com/jobs/123"
        title = "Backend Developer"
        
        id1 = Job.generate_id(url, title)
        id2 = Job.generate_id(url, title)
        
        assert id1 == id2
    
    def test_get_age_days(self, sample_job):
        """Test job age calculation."""
        age = sample_job.get_age_days()
        assert age == 0  # Posted today
    
    def test_is_fresh(self, sample_job_data):
        """Test fresh job detection."""
        # Fresh job (posted today)
        fresh_job = Job(**sample_job_data)
        assert fresh_job.is_fresh(max_age_days=7) is True
        
        # Old job (posted 10 days ago)
        old_job_data = sample_job_data.copy()
        old_job_data["posted_date"] = datetime.now() - timedelta(days=10)
        old_job = Job(**old_job_data)
        assert old_job.is_fresh(max_age_days=7) is False
    
    def test_to_dict(self, sample_job):
        """Test job serialization to dict."""
        job_dict = sample_job.to_dict()
        
        assert job_dict["title"] == sample_job.title
        assert job_dict["company"] == sample_job.company
        assert isinstance(job_dict["posted_date"], str)  # Should be ISO format
        assert isinstance(job_dict["scraped_at"], str)
    
    def test_whitespace_stripping(self, sample_job_data):
        """Test that whitespace is stripped from fields."""
        data = sample_job_data.copy()
        data["title"] = "  Backend Developer  "
        data["company"] = "  Test Company  "
        
        job = Job(**data)
        assert job.title == "Backend Developer"
        assert job.company == "Test Company"
    
    def test_tech_stack_deduplication(self, sample_job_data):
        """Test that tech_stack is deduplicated."""
        data = sample_job_data.copy()
        data["tech_stack"] = ["C#", "c#", ".NET", ".net", "Docker"]
        
        job = Job(**data)
        # Should keep first occurrence and remove duplicates (case-insensitive)
        assert len(job.tech_stack) == 3
    
    def test_description_min_length(self, sample_job_data):
        """Test description minimum length validation."""
        data = sample_job_data.copy()
        data["description"] = "Short"  # Too short
        
        with pytest.raises(ValueError):
            Job(**data)


class TestSkill:
    """Tests for Skill model."""
    
    def test_skill_creation(self):
        """Test Skill instance creation."""
        skill = Skill(
            name="C#",
            experience_years=5,
            proficiency="Expert"
        )
        assert skill.name == "C#"
        assert skill.experience_years == 5
        assert skill.proficiency == "Expert"
    
    def test_proficiency_validation(self):
        """Test proficiency level validation."""
        # Valid proficiencies
        valid_levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
        for level in valid_levels:
            skill = Skill(name="Test", experience_years=1, proficiency=level)
            assert skill.proficiency == level
        
        # Invalid proficiency
        with pytest.raises(ValueError):
            Skill(name="Test", experience_years=1, proficiency="Master")


class TestProfile:
    """Tests for Profile model."""
    
    def test_profile_creation(self, sample_profile):
        """Test Profile instance creation."""
        assert sample_profile.name == "Test User"
        assert "Backend Developer" in sample_profile.roles
        assert "languages" in sample_profile.skills
    
    def test_get_all_skills_flat(self, sample_profile):
        """Test flattening skills from all categories."""
        skills = sample_profile.get_all_skills_flat()
        
        assert len(skills) > 0
        assert "C#" in skills
        assert ".NET" in skills
    
    def test_get_high_proficiency_skills(self, sample_profile):
        """Test filtering high proficiency skills."""
        expert_skills = sample_profile.get_high_proficiency_skills(min_level="Expert")
        
        # Should only include Expert skills (C# and .NET)
        assert len(expert_skills) == 2
        assert "C#" in expert_skills
        assert ".NET" in expert_skills
    
    def test_get_min_score(self, sample_profile):
        """Test extracting min_score from preferences."""
        min_score = sample_profile.get_min_score()
        assert min_score == 65
    
    def test_get_min_score_default(self, sample_profile_data):
        """Test default min_score when not specified."""
        data = sample_profile_data.copy()
        data["preferences"].pop("min_score", None)
        
        profile = Profile(**data)
        assert profile.get_min_score() == 60  # Default
    
    def test_get_preferred_locations(self, sample_profile):
        """Test extracting preferred locations."""
        locations = sample_profile.get_preferred_locations()
        assert "Berlin" in locations
        assert "München" in locations
    
    def test_is_remote_preferred(self, sample_profile):
        """Test checking if remote work is preferred."""
        assert sample_profile.is_remote_preferred() is True
    
    def test_is_remote_preferred_false(self, sample_profile_data):
        """Test remote preference when not 100%."""
        data = sample_profile_data.copy()
        data["preferences"]["remote"] = "Hybrid"
        
        profile = Profile(**data)
        assert profile.is_remote_preferred() is False
    
    def test_flexible_skills_structure(self, sample_profile_data):
        """Test that skills support both objects and strings."""
        data = sample_profile_data.copy()
        data["skills"]["tools"] = ["Docker", "Kubernetes"]  # Plain strings
        
        profile = Profile(**data)
        skills = profile.get_all_skills_flat()
        
        # Should include both structured and plain skills
        assert len(skills) > 0

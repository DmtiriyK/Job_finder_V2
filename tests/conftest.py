"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from config.settings import Settings
from models.job import Job, ScoreResult
from models.profile import Profile, Skill
from utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Setup logging for tests."""
    setup_logging(log_level="WARNING", log_to_file=False)


@pytest.fixture
def test_settings(tmp_path):
    """Create test settings with temporary directories."""
    return Settings(
        cache_dir=str(tmp_path / "cache"),
        log_dir=str(tmp_path / "logs"),
        log_level="DEBUG"
    )


@pytest.fixture
def sample_job_data() -> Dict[str, Any]:
    """Sample job data for testing."""
    return {
        "id": "test_job_001",
        "title": "Senior Backend Developer",
        "company": "Test Company GmbH",
        "location": "Berlin, Germany",
        "remote_type": "Hybrid",
        "contract_type": "Festanstellung",
        "url": "https://example.com/jobs/001",
        "description": "Looking for Senior Backend Developer with C# and .NET experience. Must know Docker and Kubernetes.",
        "posted_date": datetime.now(),
        "source": "test_source",
        "tech_stack": ["C#", ".NET", "Docker", "Kubernetes"]
    }


@pytest.fixture
def sample_job(sample_job_data):
    """Create sample Job instance."""
    return Job(**sample_job_data)


@pytest.fixture
def sample_profile_data() -> Dict[str, Any]:
    """Sample profile data for testing."""
    return {
        "name": "Test User",
        "roles": ["Backend Developer", "Full Stack Developer"],
        "skills": {
            "languages": [
                {"name": "C#", "experience_years": 5, "proficiency": "Expert"},
                {"name": "Python", "experience_years": 3, "proficiency": "Advanced"}
            ],
            "frameworks": [
                {"name": ".NET", "experience_years": 5, "proficiency": "Expert"},
                {"name": "React", "experience_years": 2, "proficiency": "Intermediate"}
            ]
        },
        "preferences": {
            "remote": "100%",
            "locations": ["Berlin", "München", "Remote"],
            "contract_types": ["Festanstellung", "Freiberuflich"],
            "min_score": 65
        },
        "profile_text": "Experienced backend developer with 5+ years of C# and .NET experience."
    }


@pytest.fixture
def sample_profile(sample_profile_data):
    """Create sample Profile instance."""
    return Profile(**sample_profile_data)


@pytest.fixture
def sample_score_result() -> ScoreResult:
    """Create sample ScoreResult."""
    return ScoreResult(
        score=75.5,
        breakdown={
            "tfidf_similarity": {"score": 30.0, "max": 40},
            "tech_stack": {"score": 25.0, "max": 30},
            "remote_type": {"score": 12.5, "max": 15},
            "keywords": {"score": 5.0, "max": 10},
            "contract_type": {"score": 3.0, "max": 5}
        },
        explanation="Good match: High technical alignment with C# and .NET. Hybrid remote option."
    )


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Create test profile.yaml
    profile_yaml = config_dir / "profile.yaml"
    profile_yaml.write_text("""
name: "Test User"
roles:
  - "Backend Developer"
skills:
  languages:
    - name: "C#"
      experience_years: 5
      proficiency: "Expert"
preferences:
  remote: "100%"
  min_score: 60
profile_text: "Experienced backend developer with 5+ years of C# expertise"
""")
    
    # Create test scoring_rules.yaml
    scoring_yaml = config_dir / "scoring_rules.yaml"
    scoring_yaml.write_text("""
scoring:
  max_points:
    tfidf_similarity: 40
    tech_stack: 30
    remote_type: 15
    keywords: 10
    contract_type: 5
""")
    
    # Create test tech_dictionary.json
    tech_json = config_dir / "tech_dictionary.json"
    tech_json.write_text('{"languages": ["C#", "Python"]}')
    
    return config_dir


@pytest.fixture
def mock_job_list():
    """Create list of mock jobs for testing."""
    jobs = []
    for i in range(5):
        job = Job(
            id=f"test_job_{i:03d}",
            title=f"Developer Position {i}",
            company=f"Company {i}",
            location="Berlin",
            remote_type="Remote" if i % 2 == 0 else "Hybrid",
            contract_type="Festanstellung",
            url=f"https://example.com/jobs/{i}",
            description=f"Job description {i} with C# and .NET requirements.",
            posted_date=datetime.now(),
            source="test_source",
            tech_stack=["C#", ".NET", "Docker"]
        )
        jobs.append(job)
    return jobs

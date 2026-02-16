"""Tests for configuration system."""

import pytest
from pathlib import Path
from config.settings import Settings


def test_settings_creation(test_settings):
    """Test Settings instance creation."""
    assert test_settings is not None
    assert test_settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_settings_default_values():
    """Test default settings values."""
    settings = Settings()
    assert settings.log_level == "INFO"
    assert settings.cache_enabled is True
    assert settings.cache_ttl_hours == 24
    assert settings.min_score == 60


def test_settings_validation():
    """Test settings validation."""
    # Valid log level
    settings = Settings(log_level="DEBUG")
    assert settings.log_level == "DEBUG"
    
    # Invalid log level should raise error
    with pytest.raises(ValueError):
        Settings(log_level="INVALID")


def test_settings_min_score_validation():
    """Test min_score validation (0-100 range)."""
    # Valid values
    settings1 = Settings(min_score=50)
    assert settings1.min_score == 50
    
    settings2 = Settings(min_score=0)
    assert settings2.min_score == 0
    
    settings3 = Settings(min_score=100)
    assert settings3.min_score == 100
    
    # Invalid values
    with pytest.raises(ValueError):
        Settings(min_score=-10)
    
    with pytest.raises(ValueError):
        Settings(min_score=150)


def test_load_profile_yaml(temp_config_dir):
    """Test loading profile from YAML."""
    settings = Settings(config_dir=str(temp_config_dir))
    profile = settings.load_profile()
    
    assert profile is not None
    assert profile.name == "Test User"
    assert "Backend Developer" in profile.roles
    assert profile.get_min_score() == 60


def test_load_scoring_rules(temp_config_dir):
    """Test loading scoring rules from YAML."""
    settings = Settings(config_dir=str(temp_config_dir))
    rules = settings.load_scoring_rules()
    
    assert rules is not None
    assert "scoring" in rules
    assert rules["scoring"]["max_points"]["tfidf_similarity"] == 40


def test_load_tech_dictionary(temp_config_dir):
    """Test loading tech dictionary from JSON."""
    settings = Settings(config_dir=str(temp_config_dir))
    tech_dict = settings.load_tech_dictionary()
    
    assert tech_dict is not None
    assert "languages" in tech_dict
    assert "C#" in tech_dict["languages"]


def test_directory_creation(tmp_path):
    """Test that Settings creates necessary directories."""
    cache_dir = tmp_path / "cache"
    logs_dir = tmp_path / "logs"
    
    settings = Settings(
        cache_dir=str(cache_dir),
        logs_dir=str(logs_dir)
    )
    
    assert cache_dir.exists()
    assert logs_dir.exists()


def test_get_scrapers_config():
    """Test getting scrapers config."""
    settings = Settings()
    scrapers_config = settings.get_scrapers_config()
    
    assert "timeout" in scrapers_config
    assert "max_retries" in scrapers_config
    assert "rate_limit_delay" in scrapers_config
    assert "user_agents" in scrapers_config


def test_get_cache_config(test_settings):
    """Test getting cache config."""
    cache_config = test_settings.get_cache_config()
    
    assert "enabled" in cache_config
    assert "ttl_hours" in cache_config
    assert cache_config["enabled"] == test_settings.cache_enabled

"""
Configuration loader for Job Finder.
Loads environment variables, YAML configs (profile.yaml, scoring_rules.yaml).
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    """Main settings class for Job Finder application."""
    
    # Directories
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    config_dir: Path = Field(default_factory=lambda: Path(__file__).parent)
    logs_dir: Path = Field(default="logs")
    cache_dir: Path = Field(default="cache")
    
    # Google Sheets configuration
    google_sheets_credentials_path: str = Field(
        default="./config/google_credentials.json",
        description="Path to Google Service Account credentials JSON"
    )
    google_sheets_spreadsheet_id: Optional[str] = Field(
        default=None,
        description="Google Sheets spreadsheet ID (will be created if not provided)"
    )
    
    # NLP Mode
    use_advanced_nlp: bool = Field(
        default=False,
        description="Enable advanced spaCy NER (slower, local dev only)"
    )
    
    # Scraper configuration
    scraper_timeout_seconds: int = Field(default=30)
    scraper_max_retries: int = Field(default=3)
    scraper_rate_limit_delay: float = Field(
        default=2.0,
        description="Seconds between requests to same source"
    )
    
    # Cache configuration
    cache_enabled: bool = Field(default=True)
    cache_ttl_hours: int = Field(default=24)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=True)
    log_file_path: str = Field(default="./logs/scraper.log")
    
    # Results configuration
    max_results: int = Field(
        default=20,
        description="Maximum number of jobs to write to Google Sheets"
    )
    min_score: float = Field(
        default=60.0,
        description="Minimum score threshold for results"
    )
    
    # Development mode (skip actual scraping, use mock data)
    dev_mode: bool = Field(default=False)
    
    class Config:
        env_prefix = ""  # No prefix for environment variables
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize settings from environment variables."""
        # Load from environment
        env_data = {
            "google_sheets_credentials_path": os.getenv(
                "GOOGLE_SHEETS_CREDENTIALS_PATH",
                "./config/google_credentials.json"
            ),
            "google_sheets_spreadsheet_id": os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID"),
            "use_advanced_nlp": os.getenv("USE_ADVANCED_NLP", "false").lower() == "true",
            "scraper_timeout_seconds": int(os.getenv("SCRAPER_TIMEOUT_SECONDS", "30")),
            "scraper_max_retries": int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            "scraper_rate_limit_delay": float(os.getenv("SCRAPER_RATE_LIMIT_DELAY", "2.0")),
            "cache_enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
            "cache_ttl_hours": int(os.getenv("CACHE_TTL_HOURS", "24")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_to_file": os.getenv("LOG_TO_FILE", "true").lower() == "true",
            "log_file_path": os.getenv("LOG_FILE_PATH", "./logs/scraper.log"),
            "max_results": int(os.getenv("MAX_RESULTS", "20")),
            "min_score": float(os.getenv("MIN_SCORE", "60")),
            "dev_mode": os.getenv("DEV_MODE", "false").lower() == "true",
        }
        
        # Merge with provided kwargs
        env_data.update(kwargs)
        super().__init__(**env_data)
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        for dir_path in [self.logs_dir, self.cache_dir]:
            path = self.project_root / dir_path if not Path(dir_path).is_absolute() else Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}")
        return v
    
    @validator("min_score")
    def validate_min_score(cls, v):
        """Validate min_score is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("min_score must be between 0 and 100")
        return v
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            filename: Name of YAML file in config directory
        
        Returns:
            Dictionary with parsed YAML content
        
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {filepath}\n"
                f"Please create {filename} in the config directory."
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing {filename}: {str(e)}")
    
    def load_profile(self):
        """
        Load user profile from profile.yaml.
        
        Returns:
            Profile object
        """
        from models.profile import Profile
        data = self.load_yaml("profile.yaml")
        return Profile(**data)
    
    def load_scoring_rules(self) -> Dict[str, Any]:
        """
        Load scoring rules from scoring_rules.yaml.
        
        Returns:
            Dictionary with scoring rules
        """
        return self.load_yaml("scoring_rules.yaml")
    
    def load_tech_dictionary(self) -> Dict[str, Any]:
        """
        Load tech dictionary from tech_dictionary.json.
        
        Returns:
            Dictionary with tech terms
        """
        import json
        filepath = self.config_dir / "tech_dictionary.json"
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Tech dictionary not found: {filepath}\n"
                "Please create tech_dictionary.json in the config directory."
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing tech_dictionary.json: {str(e)}")
    
    def get_scrapers_config(self) -> Dict[str, Any]:
        """
        Get scraper-specific configuration.
        
        Returns:
            Dictionary with scraper settings
        """
        return {
            "timeout": self.scraper_timeout_seconds,
            "max_retries": self.scraper_max_retries,
            "rate_limit_delay": self.scraper_rate_limit_delay,
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ]
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get cache configuration.
        
        Returns:
            Dictionary with cache settings
        """
        return {
            "enabled": self.cache_enabled,
            "ttl_hours": self.cache_ttl_hours,
            "directory": str(self.project_root / self.cache_dir)
        }
    
    def __repr__(self) -> str:
        """String representation of settings (hide sensitive data)."""
        return (
            f"Settings(\n"
            f"  use_advanced_nlp={self.use_advanced_nlp},\n"
            f"  max_results={self.max_results},\n"
            f"  min_score={self.min_score},\n"
            f"  dev_mode={self.dev_mode},\n"
            f"  log_level={self.log_level}\n"
            f")"
        )


# Global settings instance (lazy loaded)
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern).
    
    Returns:
        Settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# For convenience: allow direct import
__all__ = ["Settings", "get_settings"]

"""Job data model."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field, validator
import hashlib


class ScoreResult(BaseModel):
    """Score result for a job."""
    
    score: float = Field(..., ge=0, le=100, description="Final score (0-100)")
    max_score: float = Field(default=100, description="Maximum possible score")
    breakdown: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, 
        description="Per-component score breakdown"
    )
    explanation: str = Field(default="", description="Human-readable explanation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": 73.5,
                "max_score": 100,
                "breakdown": {
                    "tfidf": {"raw": 0.72, "normalized": 28.8, "max": 40},
                    "tech_stack": {"raw": 19, "normalized": 19.0, "max": 30},
                    "remote": {"raw": 5, "normalized": 15.0, "max": 15},
                    "keywords": {"raw": 2, "normalized": 2.0, "max": 10},
                    "contract": {"raw": 2, "normalized": 5.0, "max": 5}
                },
                "explanation": "High match: Full remote (15/15), CV similarity (28.8/40)"
            }
        }


class Job(BaseModel):
    """Job posting model with all required fields."""
    
    # Required fields
    id: str = Field(..., description="Unique job identifier (hash of URL + title)")
    title: str = Field(..., min_length=1, description="Job title")
    company: str = Field(..., min_length=1, description="Company name")
    location: str = Field(..., description="Job location")
    url: HttpUrl = Field(..., description="Job posting URL")
    description: str = Field(..., min_length=10, description="Job description")
    posted_date: datetime = Field(..., description="Job posting date")
    source: str = Field(..., description="Source platform (e.g., 'RemoteOK', 'StepStone')")
    
    # Optional fields
    remote_type: str = Field(default="Not specified", description="Remote type (Full Remote, Hybrid, Onsite)")
    contract_type: Optional[str] = Field(default=None, description="Contract type (Festanstellung, Freelance, etc.)")
    salary_range: Optional[str] = Field(default=None, description="Salary range if available")
    tech_stack: List[str] = Field(default_factory=list, description="Extracted tech keywords")
    
    # Scoring fields (populated after scoring)
    score: Optional[float] = Field(default=None, ge=0, le=100, description="Final job score (0-100)")
    score_result: Optional[ScoreResult] = Field(default=None, description="Detailed score breakdown")
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.now, description="When job was scraped")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }
        json_schema_extra = {
            "example": {
                "id": "abc123def456",
                "title": "Full Stack Engineer",
                "company": "Tech Startup GmbH",
                "location": "Berlin, Germany",
                "remote_type": "Full Remote",
                "contract_type": "Festanstellung",
                "url": "https://example.com/job/12345",
                "description": "We're looking for a Full Stack Engineer with React and .NET experience...",
                "posted_date": "2026-02-16T09:00:00",
                "source": "RemoteOK",
                "tech_stack": ["React", "TypeScript", ".NET Core", "Docker"],
                "score": 85.5
            }
        }
    
    @classmethod
    def generate_id(cls, url: str, title: str) -> str:
        """
        Generate unique ID for job based on URL and title.
        
        Args:
            url: Job posting URL
            title: Job title
        
        Returns:
            Unique hash string (SHA256, 64 chars)
        """
        content = f"{url}{title}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    @validator('title', 'company', 'location')
    def strip_whitespace(cls, v):
        """Strip leading/trailing whitespace from text fields."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @validator('description')
    def validate_description_length(cls, v):
        """Ensure description has minimum length."""
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v.strip()
    
    @validator('tech_stack')
    def deduplicate_tech_stack(cls, v):
        """Remove duplicate tech terms (case-insensitive)."""
        if not v:
            return []
        # Keep original case of first occurrence
        seen = {}
        result = []
        for term in v:
            lower_term = term.lower()
            if lower_term not in seen:
                seen[lower_term] = True
                result.append(term)
        return result
    
    def get_age_days(self) -> int:
        """
        Calculate job age in days.
        
        Returns:
            Number of days since posting
        """
        return (datetime.now() - self.posted_date).days
    
    def is_fresh(self, max_age_days: int = 7) -> bool:
        """
        Check if job is fresh (posted within max_age_days).
        
        Args:
            max_age_days: Maximum age in days
        
        Returns:
            True if job is fresh
        """
        return self.get_age_days() <= max_age_days
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary with serialized fields.
        
        Returns:
            Dictionary representation
        """
        data = self.dict()
        # Convert datetime to ISO format
        data['posted_date'] = self.posted_date.isoformat()
        data['scraped_at'] = self.scraped_at.isoformat()
        # Convert URL to string
        data['url'] = str(self.url)
        return data
    
    def __str__(self) -> str:
        """String representation of job."""
        score_str = f" [{self.score:.1f}]" if self.score is not None else ""
        return f"{score_str} {self.title} @ {self.company} - {self.location} ({self.source})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Job(id={self.id}, title='{self.title}', company='{self.company}', score={self.score})"

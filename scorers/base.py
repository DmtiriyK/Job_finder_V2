"""Base classes for scoring components."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
from models.job import Job
from models.profile import Profile


@dataclass
class ComponentScore:
    """
    Result from a scoring component.
    
    Attributes:
        score: Normalized score (0 to max_score)
        raw_score: Raw score before normalization
        max_score: Maximum possible score for this component
        explanation: Human-readable explanation of how score was calculated
        details: Additional metadata (matched terms, etc.)
    """
    score: float
    raw_score: float
    max_score: float
    explanation: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate score ranges."""
        if self.details is None:
            self.details = {}
        
        # Ensure score is within bounds
        self.score = max(0.0, min(self.score, self.max_score))


class ScoreComponent(ABC):
    """
    Abstract base class for scoring components.
    
    Each component evaluates one aspect of job matching:
    - TF-IDF similarity (40 points)
    - Tech stack match (30 points)
    - Remote type preference (15 points)
    - Keywords match (10 points)
    - Contract type preference (5 points)
    """
    
    def __init__(self, max_score: float):
        """
        Initialize scoring component.
        
        Args:
            max_score: Maximum points this component can award
        """
        self.max_score = max_score
    
    @abstractmethod
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate score for this component.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with normalized score and explanation
        """
        pass
    
    def normalize_score(
        self,
        raw_score: float,
        raw_min: float,
        raw_max: float
    ) -> float:
        """
        Normalize raw score to 0-max_score range.
        
        Maps [raw_min, raw_max] → [0, max_score]
        
        Args:
            raw_score: Raw score to normalize
            raw_min: Minimum possible raw score
            raw_max: Maximum possible raw score
        
        Returns:
            Normalized score (0 to max_score)
        
        Examples:
            >>> self.max_score = 15
            >>> self.normalize_score(5, -3, 5)  # Remote: full remote
            15.0
            >>> self.normalize_score(-3, -3, 5)  # Remote: onsite
            0.0
            >>> self.normalize_score(0, -3, 5)  # Remote: hybrid 2 days
            5.625
        """
        # Clamp raw score to valid range
        raw_score = max(raw_min, min(raw_score, raw_max))
        
        # Avoid division by zero
        if raw_max == raw_min:
            return self.max_score / 2
        
        # Linear interpolation: (x - min) / (max - min) * max_score
        normalized = ((raw_score - raw_min) / (raw_max - raw_min)) * self.max_score
        
        # Ensure within bounds
        return max(0.0, min(normalized, self.max_score))

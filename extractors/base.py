"""Base extractor class for all extractors."""

from abc import ABC, abstractmethod
from typing import Any, Set


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    
    Extractors parse job descriptions and extract structured data
    (tech stack, skills, requirements, etc.).
    """
    
    @abstractmethod
    def extract(self, text: str) -> Any:
        """
        Extract data from text.
        
        Args:
            text: Input text to extract from
        
        Returns:
            Extracted data (type depends on extractor)
        """
        pass
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before extraction.
        
        Args:
            text: Raw text
        
        Returns:
            Preprocessed text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text

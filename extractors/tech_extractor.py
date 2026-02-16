"""Tech stack extractor using FlashText."""

import json
from pathlib import Path
from typing import Set, Optional
import re

from flashtext import KeywordProcessor

from extractors.base import BaseExtractor
from utils.logger import get_logger


class TechStackExtractor(BaseExtractor):
    """
    Extract tech stack (languages, frameworks, tools) from job descriptions.
    
    Uses FlashText for fast keyword extraction with case-insensitive matching.
    Handles edge cases like C#, .NET, C++, etc.
    """
    
    def __init__(self, tech_dictionary_path: Optional[str] = None):
        """
        Initialize tech stack extractor.
        
        Args:
            tech_dictionary_path: Path to tech_dictionary.json (optional)
        """
        self.logger = get_logger("extractor.tech")
        
        # Load tech dictionary
        if tech_dictionary_path is None:
            tech_dictionary_path = Path(__file__).parent.parent / "config" / "tech_dictionary.json"
        
        self.tech_dict = self._load_tech_dictionary(tech_dictionary_path)
        
        # Initialize FlashText processor
        self.keyword_processor = KeywordProcessor(case_sensitive=False)
        
        # Add keywords from dictionary
        self._build_keyword_processor()
        
        # Regex patterns for special cases
        self._special_patterns = self._build_special_patterns()
    
    def _load_tech_dictionary(self, path: Path) -> dict:
        """
        Load tech dictionary from JSON file.
        
        Args:
            path: Path to tech_dictionary.json
        
        Returns:
            Tech dictionary
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load tech dictionary from {path}: {e}")
            return {
                "languages": [],
                "frameworks": [],
                "databases": [],
                "tools": [],
                "cloud": [],
                "concepts": []
            }
    
    def _build_keyword_processor(self):
        """Build FlashText keyword processor from tech dictionary."""
        # Add all tech terms to processor
        for category, terms in self.tech_dict.items():
            for term in terms:
                # Add term and common variations
                self.keyword_processor.add_keyword(term, term)
                
                # Add case variations for better matching
                if term.lower() != term:
                    self.keyword_processor.add_keyword(term.lower(), term)
                if term.upper() != term:
                    self.keyword_processor.add_keyword(term.upper(), term)
    
    def _build_special_patterns(self) -> dict:
        """
        Build regex patterns for special cases.
        
        Returns:
            Dict of pattern name -> compiled regex
        """
        return {
            # C# with optional space
            'csharp': re.compile(r'\bC\s*#\b', re.IGNORECASE),
            # C++ with optional space
            'cplusplus': re.compile(r'\bC\s*\+\+\b', re.IGNORECASE),
            # .NET variants
            'dotnet': re.compile(r'\.NET(?:\s+Core|\s+Framework|\s+\d+)?', re.IGNORECASE),
            # F# 
            'fsharp': re.compile(r'\bF\s*#\b', re.IGNORECASE),
            # Node.js variants (including NodeJS written as one word)
            'nodejs': re.compile(r'\b(?:Node(?:\.js)?|NodeJS)\b', re.IGNORECASE),
            # Vue.js variants
            'vuejs': re.compile(r'\bVue(?:\.js)?\b', re.IGNORECASE),
        }
    
    def _extract_special_cases(self, text: str) -> Set[str]:
        """
        Extract tech terms with special characters using regex.
        
        Args:
            text: Text to extract from
        
        Returns:
            Set of extracted special tech terms
        """
        found = set()
        
        # Map pattern matches to canonical names
        special_mappings = {
            'csharp': 'C#',
            'cplusplus': 'C++',
            'dotnet': '.NET',
            'fsharp': 'F#',
            'nodejs': 'Node.js',
            'vuejs': 'Vue.js',
        }
        
        for pattern_name, pattern in self._special_patterns.items():
            if pattern.search(text):
                canonical_name = special_mappings.get(pattern_name)
                if canonical_name:
                    found.add(canonical_name)
        
        return found
    
    def extract(self, text: str) -> Set[str]:
        """
        Extract tech stack from text.
        
        Args:
            text: Job description or any text
        
        Returns:
            Set of tech terms found
        """
        if not text:
            return set()
        
        # Preprocess text
        text = self.preprocess_text(text)
        
        # Extract using FlashText
        flashtext_results = set(self.keyword_processor.extract_keywords(text))
        
        # Extract special cases (C#, .NET, etc.)
        special_results = self._extract_special_cases(text)
        
        # Combine results
        all_results = flashtext_results | special_results
        
        self.logger.debug(f"Extracted {len(all_results)} tech terms: {all_results}")
        
        return all_results
    
    def extract_by_category(self, text: str) -> dict:
        """
        Extract tech stack grouped by category.
        
        Args:
            text: Job description or any text
        
        Returns:
            Dict of category -> set of tech terms
        """
        all_tech = self.extract(text)
        
        # Initialize categorized dict dynamically from tech_dictionary keys
        categorized = {category: set() for category in self.tech_dict.keys()}
        categorized["other"] = set()  # Add 'other' for uncategorized terms
        
        # Categorize found tech terms
        for tech in all_tech:
            found_category = False
            for category, terms in self.tech_dict.items():
                # Case-insensitive match
                if any(tech.lower() == term.lower() for term in terms):
                    categorized[category].add(tech)
                    found_category = True
                    break
            
            if not found_category:
                categorized["other"].add(tech)
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}

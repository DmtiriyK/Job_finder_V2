"""Unified Remote work type detector.

Uses patterns from scoring_rules.yaml and HTML attributes for accurate detection.
"""

import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

from config.settings import Settings
from utils.logger import get_logger


class RemoteDetector:
    """
    Detect remote work type from various sources.
    
    Priority:
    1. HTML attributes (highest accuracy)
    2. Regex patterns from scoring_rules.yaml
    3. Simple keyword matching (fallback)
    
    Usage:
        detector = RemoteDetector()
        remote_type = detector.detect(
            title="Full Stack Developer (100% remote)",
            description="...",
            location="Deutschland",
            html_element=job_card  # Optional BeautifulSoup element
        )
    """
    
    def __init__(self):
        """Initialize remote detector."""
        self.logger = get_logger("utils.remote_detector")
        
        # Load patterns from scoring_rules.yaml
        self.patterns = self._load_patterns()
        
        # HTML attribute matchers for different sources
        self.html_matchers = {
            'stepstone': self._detect_stepstone_html,
            'xing': self._detect_xing_html,
        }
        
        self.logger.info(
            f"RemoteDetector initialized with {len(self.patterns)} pattern groups"
        )
    
    def _load_patterns(self) -> Dict[str, Dict]:
        """
        Load remote patterns from scoring_rules.yaml.
        
        Returns:
            Dict of {type_name: {'score': float, 'patterns': [compiled_regex]}}
        """
        try:
            settings = Settings()
            rules = settings.load_scoring_rules()
            
            patterns = {}
            remote_rules = rules.get('remote', {}).get('patterns', {})
            
            for type_name, config in remote_rules.items():
                pattern_strings = config.get('patterns', [])
                
                # Compile regex patterns (case-insensitive)
                compiled_patterns = []
                for pattern in pattern_strings:
                    try:
                        compiled_patterns.append(
                            re.compile(pattern, re.IGNORECASE)
                        )
                    except re.error as e:
                        self.logger.warning(
                            f"Invalid regex pattern '{pattern}': {e}"
                        )
                
                patterns[type_name] = {
                    'score': config.get('score', 0),
                    'patterns': compiled_patterns
                }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to load patterns: {e}")
            return {}
    
    def detect(
        self,
        title: str,
        description: str,
        location: str,
        html_element: Optional[BeautifulSoup] = None,
        source: Optional[str] = None
    ) -> str:
        """
        Detect remote work type.
        
        Args:
            title: Job title
            description: Job description
            location: Job location
            html_element: Optional BeautifulSoup element for attribute parsing
            source: Source name (stepstone, xing, etc.) for source-specific parsing
        
        Returns:
            Remote type: "Remote", "Hybrid", or "Onsite"
        """
        # Priority 1: HTML attributes (source-specific)
        if html_element and source:
            source_lower = source.lower()
            if source_lower in self.html_matchers:
                html_result = self.html_matchers[source_lower](html_element)
                if html_result:
                    self.logger.debug(
                        f"Detected via HTML attribute: {html_result}"
                    )
                    return html_result
        
        # Priority 2: Regex patterns from YAML
        combined_text = f"{title} {description} {location}"
        pattern_result = self._match_patterns(combined_text)
        if pattern_result:
            self.logger.debug(f"Detected via pattern: {pattern_result}")
            return pattern_result
        
        # Priority 3: Fallback simple keywords
        fallback_result = self._fallback_detection(combined_text)
        self.logger.debug(f"Detected via fallback: {fallback_result}")
        return fallback_result
    
    def _detect_stepstone_html(self, element: BeautifulSoup) -> Optional[str]:
        """
        Detect remote type from StepStone HTML attributes.
        
        Args:
            element: BeautifulSoup job card element
        
        Returns:
            Remote type or None
        """
        # Check for work-from-home attribute
        wfh_elem = element.select_one('[data-at="job-item-work-from-home"]')
        if wfh_elem:
            wfh_text = wfh_elem.text.strip().lower()
            
            # "Teilweise Home-Office" = Hybrid
            if 'teilweise' in wfh_text:
                return "Hybrid"
            
            # "Homeoffice möglich" = Remote
            if 'homeoffice' in wfh_text or 'remote' in wfh_text:
                return "Remote"
        
        # Check metadata-work-type attribute
        metadata_elem = element.select_one('[data-at="metadata-work-type"]')
        if metadata_elem:
            metadata_text = metadata_elem.text.strip().lower()
            
            if 'teilweise' in metadata_text:
                return "Hybrid"
            
            if 'homeoffice' in metadata_text or 'remote' in metadata_text:
                return "Remote"
        
        return None
    
    def _detect_xing_html(self, element: BeautifulSoup) -> Optional[str]:
        """
        Detect remote type from XING HTML attributes.
        
        Args:
            element: BeautifulSoup job card element
        
        Returns:
            Remote type or None
        """
        # XING has less structured data, check for specific text patterns
        text = element.get_text(separator=' ', strip=True).lower()
        
        # Check for explicit markers
        if 'hybrid' in text:
            return "Hybrid"
        
        # "Keine Kernarbeitszeit, Homeoffice" = Remote
        if 'keine kernarbeitszeit' in text and 'homeoffice' in text:
            return "Remote"
        
        if 'ortsunabhängig' in text:
            return "Remote"
        
        return None
    
    def _match_patterns(self, text: str) -> Optional[str]:
        """
        Match text against regex patterns from YAML.
        
        Args:
            text: Combined text (title + description + location)
        
        Returns:
            Remote type or None
        """
        # Check patterns in priority order
        # Order: full_remote > hybrid_flexible > hybrid_1day > hybrid_2days > onsite_required
        
        priority_order = [
            ('full_remote', 'Remote'),
            ('hybrid_flexible', 'Hybrid'),
            ('hybrid_1day', 'Hybrid'),
            ('hybrid_2days', 'Hybrid'),
            ('onsite_required', 'Onsite'),
        ]
        
        for pattern_key, result_type in priority_order:
            if pattern_key not in self.patterns:
                continue
            
            patterns = self.patterns[pattern_key]['patterns']
            
            for pattern in patterns:
                if pattern.search(text):
                    return result_type
        
        return None
    
    def _fallback_detection(self, text: str) -> str:
        """
        Fallback detection using simple keywords.
        
        Args:
            text: Combined text
        
        Returns:
            Remote type (default: "Onsite")
        """
        text_lower = text.lower()
        
        # Simple remote keywords
        remote_keywords = [
            'remote', '100%', 'homeoffice', 'home office',
            'work from home', 'wfh', 'fully remote', 'full remote',
            'ortsunabhängig', 'deutschlandweit remote'
        ]
        
        # Hybrid keywords
        hybrid_keywords = [
            'hybrid', 'teilweise', 'flexible', 'remote möglich'
        ]
        
        # Check for remote
        if any(kw in text_lower for kw in remote_keywords):
            # But check if it's actually hybrid
            if any(kw in text_lower for kw in hybrid_keywords):
                return "Hybrid"
            return "Remote"
        
        # Check for hybrid only
        if any(kw in text_lower for kw in hybrid_keywords):
            return "Hybrid"
        
        # Default: Onsite
        return "Onsite"


# Singleton instance for reuse
_detector_instance: Optional[RemoteDetector] = None


def get_remote_detector() -> RemoteDetector:
    """
    Get singleton RemoteDetector instance.
    
    Returns:
        RemoteDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = RemoteDetector()
    return _detector_instance

"""Location scoring component (15 points max)."""

from pathlib import Path
from typing import Dict, List, Set
import yaml

from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from config.settings import Settings
from utils.logger import get_logger


class LocationComponent(ScoreComponent):
    """
    Score job based on location match with synonym support.
    
    Max score: 15 points
    
    Scoring logic:
    - Germany match (city/country synonym): 15 points
    - Remote keyword: +5 bonus (can stack with location)
    - Europe (non-Germany): 8 points
    - Austria/Switzerland: 8 points
    - Other locations: 3 points (don't exclude!)
    
    Uses config/location_synonyms.yaml for synonym mapping.
    """
    
    def __init__(self, max_score: float = 15.0):
        """Initialize location component."""
        super().__init__(max_score)
        self.logger = get_logger("scorer.location")
        
        # Load location synonyms
        self.synonyms = self._load_synonyms()
        
        # Build lookup sets for fast matching
        self.germany_terms = self._build_germany_terms()
        self.remote_terms = self._build_remote_terms()
        self.europe_terms = self._build_europe_terms()
        self.neighbor_terms = self._build_neighbor_terms()
        
        self.logger.info(
            f"Loaded location synonyms: "
            f"{len(self.germany_terms)} Germany terms, "
            f"{len(self.remote_terms)} remote terms, "
            f"{len(self.europe_terms)} Europe terms"
        )
    
    def _load_synonyms(self) -> dict:
        """
        Load location synonyms from YAML file.
        
        Returns:
            Dict with synonym mappings
        """
        try:
            synonyms_path = Path(__file__).parent.parent.parent / "config" / "location_synonyms.yaml"
            
            if not synonyms_path.exists():
                self.logger.warning(f"location_synonyms.yaml not found at {synonyms_path}")
                return self._get_default_synonyms()
            
            with open(synonyms_path, 'r', encoding='utf-8') as f:
                synonyms = yaml.safe_load(f)
            
            self.logger.info(f"Loaded location synonyms from {synonyms_path}")
            return synonyms
            
        except Exception as e:
            self.logger.error(f"Failed to load location synonyms: {e}")
            return self._get_default_synonyms()
    
    def _get_default_synonyms(self) -> dict:
        """Fallback synonyms if file not found."""
        return {
            'Germany': {
                'country_names': ['Germany', 'Deutschland', 'DE'],
                'cities': ['Berlin', 'München', 'Munich', 'Hamburg', 'Frankfurt'],
                'regions': ['Bayern', 'NRW', 'Baden-Württemberg']
            },
            'Remote': ['Remote', 'Fernarbeit', 'Homeoffice', 'Work from Home', 'WFH'],
            'Europe': ['Europe', 'Europa', 'EU']
        }
    
    def _build_germany_terms(self) -> Set[str]:
        """Build set of all Germany-related terms (lowercase)."""
        terms = set()
        
        germany_dict = self.synonyms.get('Germany', {})
        
        # Add country names
        for name in germany_dict.get('country_names', []):
            terms.add(name.lower())
        
        # Add cities
        for city in germany_dict.get('cities', []):
            terms.add(city.lower())
        
        # Add regions
        for region in germany_dict.get('regions', []):
            terms.add(region.lower())
        
        return terms
    
    def _build_remote_terms(self) -> Set[str]:
        """Build set of remote work terms (lowercase)."""
        remote_list = self.synonyms.get('Remote', [])
        return {term.lower() for term in remote_list}
    
    def _build_europe_terms(self) -> Set[str]:
        """Build set of Europe terms (lowercase)."""
        europe_list = self.synonyms.get('Europe', [])
        return {term.lower() for term in europe_list}
    
    def _build_neighbor_terms(self) -> Set[str]:
        """Build set of neighboring country terms (Austria, Switzerland)."""
        terms = set()
        
        # Austria
        austria_dict = self.synonyms.get('Austria', {})
        for name in austria_dict.get('country_names', []):
            terms.add(name.lower())
        for city in austria_dict.get('cities', []):
            terms.add(city.lower())
        
        # Switzerland
        swiss_dict = self.synonyms.get('Switzerland', {})
        for name in swiss_dict.get('country_names', []):
            terms.add(name.lower())
        for city in swiss_dict.get('cities', []):
            terms.add(city.lower())
        
        # Netherlands
        netherlands_dict = self.synonyms.get('Netherlands', {})
        for name in netherlands_dict.get('country_names', []):
            terms.add(name.lower())
        for city in netherlands_dict.get('cities', []):
            terms.add(city.lower())
        
        return terms
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate location score based on job location and user preferences.
        
        Args:
            job: Job posting to score
            profile: User profile (contains preferred locations)
        
        Returns:
            ComponentScore with score, explanation, and breakdown
        """
        # Combine location and remote_type for matching
        location_text = f"{job.location} {job.remote_type or ''}".lower()
        
        # Check for matches
        is_germany = self._matches_any(location_text, self.germany_terms)
        is_remote = self._matches_any(location_text, self.remote_terms)
        is_europe = self._matches_any(location_text, self.europe_terms)
        is_neighbor = self._matches_any(location_text, self.neighbor_terms)
        
        # Calculate base score
        base_score = 0.0
        location_type = "Unknown"
        
        if is_germany:
            base_score = 15.0
            location_type = "Germany"
        elif is_neighbor:
            base_score = 8.0
            location_type = "Neighboring Country"
        elif is_europe:
            base_score = 8.0
            location_type = "Europe"
        else:
            base_score = 3.0
            location_type = "Other"
        
        # Remote bonus (can stack with location score, but capped at max_score)
        remote_bonus = 0.0
        if is_remote and base_score < self.max_score:
            remote_bonus = min(5.0, self.max_score - base_score)
            base_score += remote_bonus
        
        # Cap at max_score
        final_score = min(base_score, self.max_score)
        
        # Build explanation
        explanation_parts = [f"{location_type}: {base_score:.1f}pts"]
        if remote_bonus > 0:
            explanation_parts.append(f"Remote bonus: +{remote_bonus:.1f}pts")
        
        explanation = ", ".join(explanation_parts)
        
        # Build details
        details = {
            'location_type': location_type,
            'is_germany': is_germany,
            'is_remote': is_remote,
            'is_europe': is_europe,
            'base_score': base_score,
            'remote_bonus': remote_bonus,
            'final_score': final_score
        }
        
        self.logger.debug(
            f"Location score for '{job.location}' ({job.remote_type}): "
            f"{final_score:.1f}/{self.max_score} - {explanation}"
        )
        
        return ComponentScore(
            score=final_score,
            raw_score=final_score,
            max_score=self.max_score,
            explanation=explanation,
            details=details
        )
    
    def _matches_any(self, text: str, terms: Set[str]) -> bool:
        """
        Check if any term from set appears in text.
        
        Args:
            text: Text to search in (already lowercase)
            terms: Set of terms to search for (already lowercase)
        
        Returns:
            True if any term found
        """
        for term in terms:
            if term in text:
                return True
        return False

"""Remote type scoring component (15 points max)."""

import re
from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from config.settings import Settings
from utils.logger import get_logger


class RemoteComponent(ScoreComponent):
    """
    Score job based on remote work preferences.
    
    Max score: 15 points
    
    Scoring based on scoring_rules.yaml:
    - Full remote (100%): +5 raw → 15 points
    - Hybrid 1 day/week: +3 raw → ~10 points
    - Hybrid 2 days/week: 0 raw → ~5.6 points
    - Onsite required: -3 raw → 0 points
    
    Normalization: Maps [-3, 5] → [0, 15]
    """
    
    def __init__(self, max_score: float = 15.0):
        """Initialize remote component."""
        super().__init__(max_score)
        self.logger = get_logger("scorer.remote")
        
        # Load scoring rules from config
        settings = Settings()
        rules = settings.load_scoring_rules()
        
        # Build remote patterns
        self.patterns = self._build_patterns(rules)
        
        # Define raw score range for normalization
        self.raw_min = -3.0
        self.raw_max = 5.0
    
    def _build_patterns(self, rules: dict) -> dict:
        """
        Build remote type patterns from scoring rules.
        
        Args:
            rules: Loaded scoring_rules.yaml
        
        Returns:
            Dict of {type_name: {'score': float, 'patterns': [compiled_regex]}}
        """
        patterns = {}
        
        remote_rules = rules.get('remote', {}).get('patterns', {})
        
        for type_name, config in remote_rules.items():
            score = config.get('score', 0)
            pattern_strings = config.get('patterns', [])
            
            # Compile regex patterns
            compiled_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in pattern_strings
            ]
            
            patterns[type_name] = {
                'score': score,
                'patterns': compiled_patterns
            }
        
        self.logger.info(f"Loaded {len(patterns)} remote type patterns")
        return patterns
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate remote preference score.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with remote match score
        """
        try:
            # Check if profile prefers remote
            is_remote_preferred = profile.is_remote_preferred()
            
            # Get remote type from job
            remote_type = job.remote_type or ""
            
            # Match against patterns
            raw_score, matched_type = self._match_patterns(
                job.description,
                remote_type
            )
            
            # If not remote preferred, use neutral score
            if not is_remote_preferred:
                raw_score = 0.0
                matched_type = "neutral (remote not preferred in profile)"
            
            # Normalize score: [-3, 5] → [0, max_score]
            normalized_score = self.normalize_score(
                raw_score,
                self.raw_min,
                self.raw_max
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                matched_type,
                raw_score,
                is_remote_preferred
            )
            
            return ComponentScore(
                score=normalized_score,
                raw_score=raw_score,
                max_score=self.max_score,
                explanation=explanation,
                details={
                    'matched_type': matched_type,
                    'remote_type_field': remote_type,
                    'is_remote_preferred': is_remote_preferred
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating remote score: {e}")
            return ComponentScore(
                score=0.0,
                raw_score=0.0,
                max_score=self.max_score,
                explanation=f"Error: {str(e)}",
                details={}
            )
    
    def _match_patterns(self, description: str, remote_type: str) -> tuple:
        """
        Match job description against remote patterns.
        
        Args:
            description: Job description text
            remote_type: Remote type field
        
        Returns:
            Tuple of (score, matched_type_name)
        """
        combined_text = f"{remote_type} {description}"
        
        # Try to match each pattern type (order matters: check negative first)
        # Check in order: onsite, hybrid_2days, hybrid_1day, full_remote
        match_order = ['onsite_required', 'hybrid_2days', 'hybrid_1day', 'full_remote']
        
        for type_name in match_order:
            if type_name not in self.patterns:
                continue
            
            config = self.patterns[type_name]
            
            for pattern in config['patterns']:
                if pattern.search(combined_text):
                    return config['score'], type_name
        
        # No match: assume hybrid 2 days (neutral)
        return 0.0, "unknown (assumed hybrid)"
    
    def _generate_explanation(
        self,
        matched_type: str,
        raw_score: float,
        is_remote_preferred: bool
    ) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            matched_type: Matched remote type name
            raw_score: Raw score
            is_remote_preferred: Whether profile prefers remote
        
        Returns:
            Explanation text
        """
        if not is_remote_preferred:
            return "Remote work not specified as preference in profile."
        
        score_text = "positive" if raw_score > 0 else "negative" if raw_score < 0 else "neutral"
        
        return (
            f"Remote type: {matched_type.replace('_', ' ')} "
            f"({score_text}, {raw_score:+.0f} raw score)."
        )

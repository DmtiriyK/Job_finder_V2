"""Keywords scoring component (10 points max)."""

from typing import Dict, List
from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from config.settings import Settings
from utils.logger import get_logger


class KeywordComponent(ScoreComponent):
    """
    Score job based on keyword matches (urgency, positive/negative signals).
    
    Max score: 10 points
    
    Scoring based on scoring_rules.yaml:
    - Urgency keywords: "sofort", "asap" (+2), "dringend" (+1)
    - Positive keywords: "remote-first" (+2), "flexible Arbeitszeiten" (+1)
    - Negative keywords: "vor Ort" (-2), "Onsite only" (-5)
    
    Normalization:
    - Raw score is sum of matched keyword scores
    - If sum > 10 → capped at 10
    - If sum < 0 → floored at 0
    """
    
    def __init__(self, max_score: float = 10.0):
        """Initialize keyword component."""
        super().__init__(max_score)
        self.logger = get_logger("scorer.keywords")
        
        # Load scoring rules from config
        settings = Settings()
        rules = settings.load_scoring_rules()
        
        # Build keyword scoring lookup
        self.keywords = self._build_keywords(rules)
    
    def _build_keywords(self, rules: dict) -> Dict[str, float]:
        """
        Build keyword → score mapping from scoring rules.
        
        Args:
            rules: Loaded scoring_rules.yaml
        
        Returns:
            Dict mapping keyword (lowercase) to score
        """
        keywords = {}
        
        keyword_rules = rules.get('keywords', {})
        
        # Urgency keywords
        for item in keyword_rules.get('urgency', []):
            term = item['term'].lower()
            keywords[term] = item['score']
        
        # Positive keywords
        for item in keyword_rules.get('positive', []):
            term = item['term'].lower()
            keywords[term] = item['score']
        
        # Negative keywords
        for item in keyword_rules.get('negative', []):
            term = item['term'].lower()
            keywords[term] = item['score']
        
        self.logger.info(f"Loaded {len(keywords)} keyword scoring rules")
        return keywords
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate keyword match score.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with keyword match score
        """
        try:
            # Search for keywords in job description and title
            combined_text = f"{job.title} {job.description}".lower()
            
            # Match keywords
            raw_score = 0.0
            matched_keywords = {}
            
            for keyword, score in self.keywords.items():
                if keyword in combined_text:
                    raw_score += score
                    matched_keywords[keyword] = score
            
            # Normalize: cap at max_score, floor at 0
            normalized_score = max(0.0, min(raw_score, self.max_score))
            
            # Generate explanation
            explanation = self._generate_explanation(matched_keywords)
            
            return ComponentScore(
                score=normalized_score,
                raw_score=raw_score,
                max_score=self.max_score,
                explanation=explanation,
                details={
                    'matched_keywords': matched_keywords,
                    'total_keywords_checked': len(self.keywords)
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating keyword score: {e}")
            return ComponentScore(
                score=0.0,
                raw_score=0.0,
                max_score=self.max_score,
                explanation=f"Error: {str(e)}",
                details={}
            )
    
    def _generate_explanation(self, matched_keywords: Dict[str, float]) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            matched_keywords: Dict of matched keyword → score
        
        Returns:
            Explanation text
        """
        if not matched_keywords:
            return "No significant keywords matched."
        
        # Sort by score (descending by absolute value)
        sorted_matches = sorted(
            matched_keywords.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Count positives and negatives
        positives = [(k, v) for k, v in matched_keywords.items() if v > 0]
        negatives = [(k, v) for k, v in matched_keywords.items() if v < 0]
        
        explanation_parts = []
        
        if positives:
            pos_text = ", ".join(f"'{k}' ({v:+.0f})" for k, v in positives[:3])
            explanation_parts.append(f"Positive: {pos_text}")
        
        if negatives:
            neg_text = ", ".join(f"'{k}' ({v:.0f})" for k, v in negatives[:2])
            explanation_parts.append(f"Negative: {neg_text}")
        
        return "; ".join(explanation_parts) + "."

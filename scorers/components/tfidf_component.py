"""TF-IDF similarity scoring component (40 points max)."""

from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from matchers.tfidf_matcher import TfidfMatcher
from utils.logger import get_logger


class TfidfComponent(ScoreComponent):
    """
    Score job based on TF-IDF cosine similarity with profile text.
    
    Max score: 40 points
    
    Scoring:
    - Raw score: Cosine similarity (0.0 to 1.0)
    - Normalized: similarity * max_score
    - High similarity (>0.7) → 28-40 points
    - Medium similarity (0.4-0.7) → 16-28 points
    - Low similarity (<0.4) → 0-16 points
    """
    
    def __init__(self, max_score: float = 40.0):
        """Initialize TF-IDF component."""
        super().__init__(max_score)
        self.matcher = TfidfMatcher()
        self.logger = get_logger("scorer.tfidf")
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate TF-IDF similarity score.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with similarity-based score
        """
        try:
            # Calculate cosine similarity
            similarity = self.matcher.calculate_similarity(
                job.description,
                profile.profile_text
            )
            
            # Raw score is the similarity (0.0 to 1.0)
            raw_score = similarity
            
            # Normalized score: similarity * max_score
            normalized_score = similarity * self.max_score
            
            # Generate explanation
            explanation = self._generate_explanation(similarity)
            
            # Get top TF-IDF terms for details
            job_tfidf = self.matcher.get_tfidf_scores(job.description)
            top_job_terms = list(job_tfidf.keys())[:10] if job_tfidf else []
            
            return ComponentScore(
                score=normalized_score,
                raw_score=raw_score,
                max_score=self.max_score,
                explanation=explanation,
                details={
                    'similarity': similarity,
                    'top_job_terms': top_job_terms
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating TF-IDF score: {e}")
            return ComponentScore(
                score=0.0,
                raw_score=0.0,
                max_score=self.max_score,
                explanation=f"Error: {str(e)}",
                details={}
            )
    
    def _generate_explanation(self, similarity: float) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            similarity: Cosine similarity (0-1)
        
        Returns:
            Explanation text
        """
        if similarity >= 0.7:
            level = "Very high"
        elif similarity >= 0.5:
            level = "High"
        elif similarity >= 0.3:
            level = "Medium"
        elif similarity >= 0.15:
            level = "Low"
        else:
            level = "Very low"
        
        return (
            f"{level} text similarity ({similarity:.2%}). "
            f"Job description significantly matches your profile."
            if similarity >= 0.5
            else f"{level} text similarity ({similarity:.2%}). "
                 f"Some overlap with your profile."
        )

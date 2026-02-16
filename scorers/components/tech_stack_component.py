"""Tech stack scoring component (30 points max)."""

from typing import Dict, Set
from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from config.settings import Settings
from utils.logger import get_logger


class TechStackComponent(ScoreComponent):
    """
    Score job based on tech stack match with profile skills.
    
    Max score: 30 points
    
    Scoring based on scoring_rules.yaml:
    - High priority techs: 5, 4, 3 points each
    - Medium priority techs: 2, 1 points each
    - Negative techs: -3 points each (SAP, COBOL, etc.)
    
    Normalization:
    - Raw score is sum of matched tech scores
    - If sum > 30 → capped at 30
    - If sum < 0 → floored at 0
    """
    
    def __init__(self, max_score: float = 30.0):
        """Initialize tech stack component."""
        super().__init__(max_score)
        self.logger = get_logger("scorer.tech_stack")
        
        # Load scoring rules from config
        settings = Settings()
        rules = settings.load_scoring_rules()
        
        # Build tech scoring lookup table
        self.tech_scores = self._build_tech_scores(rules)
    
    def _build_tech_scores(self, rules: dict) -> Dict[str, float]:
        """
        Build tech term → score mapping from scoring rules.
        
        Args:
            rules: Loaded scoring_rules.yaml
        
        Returns:
            Dict mapping tech term (lowercase) to score
        """
        tech_scores = {}
        
        tech_rules = rules.get('tech_stack', {})
        
        # High priority tech
        for item in tech_rules.get('high_priority', []):
            term = item['term'].lower()
            tech_scores[term] = item['score']
        
        # Medium priority tech
        for item in tech_rules.get('medium_priority', []):
            term = item['term'].lower()
            tech_scores[term] = item['score']
        
        # Negative tech
        for item in tech_rules.get('negative', []):
            term = item['term'].lower()
            tech_scores[term] = item['score']
        
        self.logger.info(f"Loaded {len(tech_scores)} tech scoring rules")
        return tech_scores
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate tech stack match score.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with tech match score
        """
        try:
            # Get tech stack from job
            job_tech = set(t.lower() for t in job.tech_stack)
            
            # Get profile skills (already returns list of strings)
            profile_skills = set(
                skill.lower()
                for skill in profile.get_all_skills_flat()
            )
            
            # Calculate raw score
            raw_score = 0.0
            matched_tech = {}
            
            for tech in job_tech:
                if tech in self.tech_scores:
                    score = self.tech_scores[tech]
                    raw_score += score
                    matched_tech[tech] = score
            
            # Normalize: cap at max_score, floor at 0
            normalized_score = max(0.0, min(raw_score, self.max_score))
            
            # Generate explanation
            explanation = self._generate_explanation(matched_tech, job_tech, profile_skills)
            
            return ComponentScore(
                score=normalized_score,
                raw_score=raw_score,
                max_score=self.max_score,
                explanation=explanation,
                details={
                    'matched_tech': matched_tech,
                    'total_job_tech': len(job_tech),
                    'total_profile_skills': len(profile_skills)
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating tech stack score: {e}")
            return ComponentScore(
                score=0.0,
                raw_score=0.0,
                max_score=self.max_score,
                explanation=f"Error: {str(e)}",
                details={}
            )
    
    def _generate_explanation(
        self,
        matched_tech: Dict[str, float],
        job_tech: Set[str],
        profile_skills: Set[str]
    ) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            matched_tech: Dict of matched tech → score
            job_tech: All tech in job posting
            profile_skills: All skills in profile
        
        Returns:
            Explanation text
        """
        if not matched_tech:
            return (
                f"No scored technologies matched. "
                f"Job requires {len(job_tech)} technologies."
            )
        
        # Sort matched tech by score (descending)
        sorted_matches = sorted(
            matched_tech.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Top 3 matches
        top_3 = sorted_matches[:3]
        top_3_text = ", ".join(f"{tech} ({score:+.0f})" for tech, score in top_3)
        
        # Count positives and negatives
        positives = sum(1 for s in matched_tech.values() if s > 0)
        negatives = sum(1 for s in matched_tech.values() if s < 0)
        
        explanation = (
            f"Matched {len(matched_tech)}/{len(job_tech)} technologies "
            f"({positives} positive, {negatives} negative). "
        )
        
        if top_3:
            explanation += f"Top matches: {top_3_text}."
        
        return explanation

"""Score aggregator that combines all scoring components."""

from typing import Dict, Any
from models.job import Job
from models.profile import Profile
from models.job import ScoreResult
from scorers.components import (
    TfidfComponent,
    TechStackComponent,
    LocationComponent,
    RemoteComponent,
    KeywordComponent,
    ContractComponent
)
from utils.logger import get_logger


class ScoreAggregator:
    """
    Aggregate scores from all components into final score (0-100).
    
    Components:
    - TF-IDF similarity: 35 points
    - Tech stack match: 25 points
    - Location match: 15 points
    - Remote preference: 15 points
    - Keywords: 8 points
    - Contract type: 2 points
    
    Total: 100 points
    """
    
    def __init__(self):
        """Initialize score aggregator with all components."""
        self.logger = get_logger("scorer.aggregator")
        
        # Initialize all scoring components
        self.components = {
            'tfidf': TfidfComponent(max_score=35.0),
            'tech_stack': TechStackComponent(max_score=25.0),
            'location': LocationComponent(max_score=15.0),
            'remote': RemoteComponent(max_score=15.0),
            'keywords': KeywordComponent(max_score=8.0),
            'contract': ContractComponent(max_score=2.0)
        }
        
        self.logger.info(
            f"Initialized {len(self.components)} scoring components "
            f"(total max: 100 points)"
        )
    
    def score_job(self, job: Job, profile: Profile) -> ScoreResult:
        """
        Calculate final score for job against profile.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ScoreResult with final score (0-100) and breakdown
        """
        try:
            # Calculate score from each component
            component_scores = {}
            breakdown = {}
            explanations = []
            
            for name, component in self.components.items():
                try:
                    result = component.calculate(job, profile)
                    
                    component_scores[name] = result
                    
                    breakdown[name] = {
                        'raw': result.raw_score,
                        'normalized': result.score,
                        'max': result.max_score
                    }
                    
                    explanations.append(f"{name.upper()}: {result.explanation}")
                
                except Exception as e:
                    self.logger.error(f"Error in {name} component: {e}")
                    # Assign 0 score if component fails
                    breakdown[name] = {
                        'raw': 0.0,
                        'normalized': 0.0,
                        'max': component.max_score
                    }
                    explanations.append(f"{name.upper()}: Error - {str(e)}")
            
            # Calculate final score (sum of normalized scores)
            final_score = sum(
                breakdown[name]['normalized']
                for name in breakdown
            )
            
            # Ensure within bounds
            final_score = max(0.0, min(final_score, 100.0))
            
            # Generate combined explanation
            explanation = "\n".join(explanations)
            
            # Create ScoreResult
            score_result = ScoreResult(
                score=final_score,
                breakdown=breakdown,
                explanation=explanation
            )
            
            self.logger.debug(
                f"Scored job '{job.title}': {final_score:.1f}/100 "
                f"(TFIDF: {breakdown['tfidf']['normalized']:.1f}, "
                f"Tech: {breakdown['tech_stack']['normalized']:.1f}, "
                f"Remote: {breakdown['remote']['normalized']:.1f}, "
                f"Keywords: {breakdown['keywords']['normalized']:.1f}, "
                f"Contract: {breakdown['contract']['normalized']:.1f})"
            )
            
            return score_result
        
        except Exception as e:
            self.logger.error(f"Error in score aggregator: {e}")
            
            # Return zero score with error explanation
            return ScoreResult(
                score=0.0,
                breakdown={
                    name: {'raw': 0.0, 'normalized': 0.0, 'max': comp.max_score}
                    for name, comp in self.components.items()
                },
                explanation=f"Error calculating score: {str(e)}"
            )
    
    def get_component_weights(self) -> Dict[str, float]:
        """
        Get weight (max score) for each component.
        
        Returns:
            Dict of component_name → max_score
        """
        return {
            name: component.max_score
            for name, component in self.components.items()
        }
    
    def verify_total_weight(self) -> bool:
        """
        Verify that sum of all component max scores equals 100.
        
        Returns:
            True if total equals 100, False otherwise
        """
        weights = self.get_component_weights()
        total = sum(weights.values())
        
        if abs(total - 100.0) > 0.01:
            self.logger.warning(
                f"Component weights sum to {total}, expected 100.0"
            )
            return False
        
        return True

"""Contract type scoring component (5 points max)."""

from scorers.base import ScoreComponent, ComponentScore
from models.job import Job
from models.profile import Profile
from config.settings import Settings
from utils.logger import get_logger


class ContractComponent(ScoreComponent):
    """
    Score job based on contract type preferences.
    
    Max score: 5 points
    
    Scoring based on scoring_rules.yaml:
    - Freiberuflich/Contract: +2 raw
    - Unbefristet: +1 raw
    - Befristet: 0 raw
    - Junior: -2 raw
    - Praktikum: -5 raw
    
    Normalization: Maps [-5, 2] → [0, 5]
    """
    
    def __init__(self, max_score: float = 5.0):
        """Initialize contract component."""
        super().__init__(max_score)
        self.logger = get_logger("scorer.contract")
        
        # Load scoring rules from config
        settings = Settings()
        rules = settings.load_scoring_rules()
        
        # Build contract type scoring
        self.contract_scores = self._build_contract_scores(rules)
        
        # Define raw score range for normalization
        self.raw_min = -5.0
        self.raw_max = 2.0
    
    def _build_contract_scores(self, rules: dict) -> dict:
        """
        Build contract type → score mapping from scoring rules.
        
        Args:
            rules: Loaded scoring_rules.yaml
        
        Returns:
            Dict mapping contract type (lowercase) to score
        """
        contract_scores = {}
        
        contract_rules = rules.get('contract', {}).get('types', [])
        
        for item in contract_rules:
            name = item['name'].lower()
            contract_scores[name] = item['score']
        
        self.logger.info(f"Loaded {len(contract_scores)} contract type scoring rules")
        return contract_scores
    
    def calculate(self, job: Job, profile: Profile) -> ComponentScore:
        """
        Calculate contract type score.
        
        Args:
            job: Job posting to score
            profile: User profile to match against
        
        Returns:
            ComponentScore with contract type score
        """
        try:
            # Get contract type from job
            contract_type = job.contract_type or ""
            
            # Match against known contract types
            raw_score, matched_type = self._match_contract_type(
                contract_type,
                job.title,
                job.description
            )
            
            # Normalize score: [-5, 2] → [0, max_score]
            normalized_score = self.normalize_score(
                raw_score,
                self.raw_min,
                self.raw_max
            )
            
            # Generate explanation
            explanation = self._generate_explanation(matched_type, raw_score)
            
            return ComponentScore(
                score=normalized_score,
                raw_score=raw_score,
                max_score=self.max_score,
                explanation=explanation,
                details={
                    'matched_type': matched_type,
                    'contract_type_field': contract_type
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating contract score: {e}")
            return ComponentScore(
                score=0.0,
                raw_score=0.0,
                max_score=self.max_score,
                explanation=f"Error: {str(e)}",
                details={}
            )
    
    def _match_contract_type(
        self,
        contract_type: str,
        title: str,
        description: str
    ) -> tuple:
        """
        Match contract type against scoring rules.
        
        Args:
            contract_type: Contract type field
            title: Job title
            description: Job description
        
        Returns:
            Tuple of (score, matched_type_name)
        """
        # Combine all text for matching
        combined_text = f"{contract_type} {title} {description}".lower()
        
        # Try to match each contract type
        for contract_name, score in self.contract_scores.items():
            if contract_name in combined_text:
                return score, contract_name
        
        # No match: assume standard contract (0 score)
        return 0.0, "standard contract (unspecified)"
    
    def _generate_explanation(self, matched_type: str, raw_score: float) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            matched_type: Matched contract type name
            raw_score: Raw score
        
        Returns:
            Explanation text
        """
        score_text = "favorable" if raw_score > 0 else "unfavorable" if raw_score < 0 else "neutral"
        
        return (
            f"Contract type: {matched_type} "
            f"({score_text}, {raw_score:+.0f} raw score)."
        )

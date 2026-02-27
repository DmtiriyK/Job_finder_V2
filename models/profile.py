"""Profile data model."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class Skill(BaseModel):
    """Skill with experience and proficiency level."""
    
    name: str = Field(..., min_length=1, description="Skill name")
    experience_years: Optional[int] = Field(default=None, ge=0, description="Years of experience")
    proficiency: Optional[str] = Field(
        default=None,
        description="Proficiency level (Beginner, Intermediate, Advanced, Expert)"
    )
    
    @validator('proficiency')
    def validate_proficiency(cls, v):
        """Validate proficiency level."""
        if v is None:
            return v
        allowed = ["Beginner", "Intermediate", "Advanced", "Expert"]
        if v not in allowed:
            raise ValueError(f"proficiency must be one of {allowed}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Python",
                "experience_years": 5,
                "proficiency": "Expert"
            }
        }


class Profile(BaseModel):
    """User profile model loaded from profile.yaml."""
    
    # Identity
    name: str = Field(..., description="User's name")
    
    # Career targets
    roles: List[str] = Field(default_factory=list, description="Target job roles")
    
    # Skills (organized by category)
    skills: Dict[str, List[Any]] = Field(
        default_factory=dict,
        description="Skills organized by category (languages, frameworks, tools, concepts)"
    )
    
    # Preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="Job preferences (remote, locations, contract types)"
    )
    
    # Profile text for TF-IDF matching
    profile_text: str = Field(
        ..., 
        min_length=50,
        description="Natural language profile description for TF-IDF similarity matching"
    )
    
    # Optional: CV metadata
    cv: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed CV data for reference"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "roles": ["Full Stack Engineer", "Backend Developer"],
                "skills": {
                    "languages": [
                        {"name": "Python", "experience_years": 5, "proficiency": "Expert"},
                        {"name": "TypeScript", "experience_years": 3, "proficiency": "Advanced"}
                    ],
                    "frameworks": [
                        {"name": "React", "experience_years": 3},
                        {"name": ".NET Core", "experience_years": 4}
                    ],
                    "tools": [
                        {"name": "Docker", "experience_years": 4},
                        {"name": "AWS", "experience_years": 3}
                    ],
                    "concepts": [
                        "Microservices", "REST API", "CI/CD"
                    ]
                },
                "preferences": {
                    "remote": "100% preferred",
                    "contract_types": ["Festanstellung", "Freelance"],
                    "locations": ["Germany", "Remote"],
                    "min_score": 60
                },
                "profile_text": "Full Stack Engineer with 5+ years of experience..."
            }
        }
    
    @validator('profile_text')
    def strip_profile_text(cls, v):
        """Strip whitespace from profile text."""
        return v.strip()
    
    def get_all_skills_flat(self) -> List[str]:
        """
        Get flat list of all skill names.
        
        Returns:
            List of skill names
        """
        skills = []
        for category, items in self.skills.items():
            if not items:
                continue
            
            for item in items:
                if isinstance(item, dict):
                    # Skill object with name field
                    if 'name' in item:
                        skills.append(item['name'])
                elif isinstance(item, str):
                    # Plain string skill
                    skills.append(item)
        
        return skills
    
    def get_high_proficiency_skills(self, min_level: str = "Advanced") -> List[str]:
        """
        Get skills with high proficiency level.
        
        Args:
            min_level: Minimum proficiency level (default: Advanced)
        
        Returns:
            List of high-proficiency skill names
        """
        levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
        min_idx = levels.index(min_level) if min_level in levels else 2
        
        high_skills = []
        for category, items in self.skills.items():
            if not items:
                continue
            
            for item in items:
                if isinstance(item, dict) and 'name' in item:
                    proficiency = item.get('proficiency')
                    if proficiency and proficiency in levels:
                        if levels.index(proficiency) >= min_idx:
                            high_skills.append(item['name'])
        
        return high_skills
    
    def get_min_score(self) -> float:
        """
        Get minimum acceptable job score from preferences.
        
        Returns:
            Minimum score (default: 60.0)
        """
        return self.preferences.get('min_score', 60.0)
    
    def get_preferred_locations(self) -> List[str]:
        """
        Get preferred job locations from preferences.
        
        Returns:
            List of preferred locations
        """
        return self.preferences.get('locations', ['Germany', 'Remote'])
    
    def get_preferred_contract_types(self) -> List[str]:
        """
        Get preferred contract types from preferences.
        
        Returns:
            List of preferred contract types
        """
        return self.preferences.get('contract_types', [])
    
    def is_remote_preferred(self) -> bool:
        """
        Check if remote work is preferred.
        
        Returns:
            True if remote is strongly preferred
        """
        remote_pref = self.preferences.get('remote', '').lower()
        return '100%' in remote_pref or 'preferred' in remote_pref or 'only' in remote_pref
    
    def __str__(self) -> str:
        """String representation of profile."""
        skill_count = len(self.get_all_skills_flat())
        return f"Profile({self.name}, {len(self.roles)} roles, {skill_count} skills)"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Profile(name='{self.name}', roles={len(self.roles)}, skills={len(self.get_all_skills_flat())})"

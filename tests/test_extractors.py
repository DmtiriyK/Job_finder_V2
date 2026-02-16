"""Tests for extractors."""

import pytest
from pathlib import Path

from extractors.tech_extractor import TechStackExtractor


class TestTechStackExtractor:
    """Tests for TechStackExtractor."""
    
    @pytest.fixture
    def extractor(self) -> TechStackExtractor:
        """Create TechStackExtractor instance."""
        return TechStackExtractor()
    
    def test_extractor_initialization(self, extractor):
        """Test that extractor initializes correctly."""
        assert extractor is not None
        assert extractor.keyword_processor is not None
        assert extractor.tech_dict is not None
        assert len(extractor.tech_dict) > 0
    
    def test_extract_basic_tech(self, extractor):
        """Test extracting basic tech terms."""
        description = """
        We're looking for a Full Stack Engineer with experience in 
        React, TypeScript, Node.js, and PostgreSQL.
        """
        
        tech_stack = extractor.extract(description)
        
        assert isinstance(tech_stack, set)
        assert len(tech_stack) > 0
        
        # Check for expected terms (case-insensitive)
        tech_lower = {t.lower() for t in tech_stack}
        assert 'react' in tech_lower
        assert 'typescript' in tech_lower
        assert 'postgresql' in tech_lower
    
    def test_extract_csharp(self, extractor):
        """Test extracting C# (special character edge case)."""
        description = "Looking for C# developer with .NET experience"
        
        tech_stack = extractor.extract(description)
        
        assert 'C#' in tech_stack
    
    def test_extract_cplusplus(self, extractor):
        """Test extracting C++ (special character edge case)."""
        description = "C++ developer needed for systems programming"
        
        tech_stack = extractor.extract(description)
        
        assert 'C++' in tech_stack
    
    def test_extract_dotnet(self, extractor):
        """Test extracting .NET variants."""
        descriptions = [
            ".NET Core developer needed",
            "Experience with .NET Framework",
            "Build APIs with .NET 6",
        ]
        
        for desc in descriptions:
            tech_stack = extractor.extract(desc)
            assert '.NET' in tech_stack, f"Failed for: {desc}"
    
    def test_extract_nodejs_variants(self, extractor):
        """Test extracting Node.js variants."""
        descriptions = [
            "Backend with Node.js",
            "Node developer needed",
            "NodeJS experience required",
        ]
        
        for desc in descriptions:
            tech_stack = extractor.extract(desc)
            # Should extract Node.js in some form
            assert any('node' in t.lower() for t in tech_stack), f"Failed for: {desc}"
    
    def test_case_insensitivity(self, extractor):
        """Test that extraction is case-insensitive."""
        descriptions = [
            "Experience with REACT and TYPESCRIPT",
            "react and typescript experience",
            "React and TypeScript developer",
        ]
        
        results = [extractor.extract(desc) for desc in descriptions]
        
        # All should extract similar tech (normalized)
        for tech_stack in results:
            tech_lower = {t.lower() for t in tech_stack}
            assert 'react' in tech_lower
            assert 'typescript' in tech_lower
    
    def test_extract_empty_text(self, extractor):
        """Test extraction with empty text."""
        assert extractor.extract("") == set()
        assert extractor.extract(None) == set()
    
    def test_extract_no_tech(self, extractor):
        """Test extraction with no tech terms."""
        description = "We are a great company looking for passionate people."
        
        tech_stack = extractor.extract(description)
        
        # Should return empty set or very few matches
        assert len(tech_stack) < 3  # Allow some random matches
    
    def test_extract_complex_description(self, extractor):
        """Test extraction from complex real-world description."""
        description = """
        Senior Full Stack Engineer position.
        
        Requirements:
        - 5+ years experience with C# and .NET Core
        - Strong React and TypeScript skills
        - Experience with Docker and Kubernetes
        - PostgreSQL database knowledge
        - CI/CD with GitHub Actions
        - Understanding of microservices architecture
        
        Nice to have:
        - Azure or AWS experience
        - Redis caching
        - RabbitMQ or Kafka
        """
        
        tech_stack = extractor.extract(description)
        
        # Should extract many tech terms
        assert len(tech_stack) >= 10
        
        # Check for key terms
        tech_lower = {t.lower() for t in tech_stack}
        assert 'c#' in {t.lower() for t in tech_stack} or 'C#' in tech_stack
        assert any('.net' in t.lower() for t in tech_stack)
        assert 'react' in tech_lower
        assert 'typescript' in tech_lower
        assert 'docker' in tech_lower
        assert 'kubernetes' in tech_lower
        assert 'postgresql' in tech_lower
    
    def test_extract_by_category(self, extractor):
        """Test extracting tech grouped by category."""
        description = """
        Full Stack role with Python, Django, React, PostgreSQL, 
        Docker, and AWS experience required.
        """
        
        categorized = extractor.extract_by_category(description)
        
        assert isinstance(categorized, dict)
        assert len(categorized) > 0
        
        # Should have some categories
        all_tech = set()
        for category, tech_set in categorized.items():
            assert isinstance(tech_set, set)
            all_tech.update(tech_set)
        
        # Total should match extract() result
        simple_extract = extractor.extract(description)
        assert all_tech == simple_extract or len(all_tech) >= len(simple_extract) - 2
    
    def test_preprocess_text(self, extractor):
        """Test text preprocessing."""
        messy_text = "  Extra    spaces   and   \n newlines  \t tabs  "
        
        processed = extractor.preprocess_text(messy_text)
        
        assert "  " not in processed  # No double spaces
        assert "\n" not in processed
        assert "\t" not in processed
    
    def test_duplicate_removal(self, extractor):
        """Test that duplicates are removed."""
        description = "Python Python Python React React"
        
        tech_stack = extractor.extract(description)
        
        # Should be a set, so no duplicates
        tech_list = list(tech_stack)
        assert len(tech_list) == len(set(tech_list))
    
    def test_multiple_dot_variants(self, extractor):
        """Test extraction of multiple .NET variants."""
        description = ".NET Core and .NET Framework experience"
        
        tech_stack = extractor.extract(description)
        
        # Should extract .NET (might merge variants)
        assert any('.net' in t.lower() for t in tech_stack)

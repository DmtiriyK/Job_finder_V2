"""Tests for matchers."""

import pytest
import numpy as np

from matchers.tfidf_matcher import TfidfMatcher


class TestTfidfMatcher:
    """Tests for TfidfMatcher."""
    
    @pytest.fixture
    def matcher(self) -> TfidfMatcher:
        """Create TfidfMatcher instance."""
        return TfidfMatcher()
    
    def test_matcher_initialization(self, matcher):
        """Test that matcher initializes correctly."""
        assert matcher is not None
        assert matcher.vectorizer is not None
        assert matcher._is_fitted is False
    
    def test_calculate_similarity_identical_texts(self, matcher):
        """Test similarity of identical texts."""
        text = "Python developer with Django experience"
        
        similarity = matcher.calculate_similarity(text, text)
        
        assert 0.99 <= similarity <= 1.0  # Should be very close to 1.0
    
    def test_calculate_similarity_similar_texts(self, matcher):
        """Test similarity of similar texts."""
        text1 = "Python developer with Django and Flask experience"
        text2 = "Looking for Python engineer with Django knowledge"
        
        similarity = matcher.calculate_similarity(text1, text2)
        
        # Should be moderately similar (some common keywords after stopwords removal)
        assert 0.1 <= similarity <= 0.9
    
    def test_calculate_similarity_different_texts(self, matcher):
        """Test similarity of completely different texts."""
        text1 = "Python Django Flask backend development"
        text2 = "Marketing manager with sales experience"
        
        similarity = matcher.calculate_similarity(text1, text2)
        
        # Should be low similarity (no common tech terms)
        assert 0.0 <= similarity <= 0.3
    
    def test_calculate_similarity_empty_texts(self, matcher):
        """Test similarity with empty texts."""
        assert matcher.calculate_similarity("", "some text") == 0.0
        assert matcher.calculate_similarity("some text", "") == 0.0
        assert matcher.calculate_similarity("", "") == 0.0
    
    def test_similarity_range(self, matcher):
        """Test that similarity is always in [0, 1] range."""
        text1 = "Python developer"
        text2 = "React frontend"
        
        similarity = matcher.calculate_similarity(text1, text2)
        
        assert 0.0 <= similarity <= 1.0
    
    def test_fit_on_corpus(self, matcher):
        """Test fitting matcher on corpus."""
        corpus = [
            "Python developer with Django",
            "React frontend engineer",
            "Full stack developer",
        ]
        
        matcher.fit(corpus)
        
        assert matcher._is_fitted is True
        assert matcher._corpus_vectors is not None
    
    def test_calculate_similarity_to_corpus(self, matcher):
        """Test calculating similarity to corpus."""
        corpus = [
            "Python Django backend developer",
            "React TypeScript frontend",
            "Full stack with Python and React",
        ]
        
        query = "Python Django experience"
        
        similarities = matcher.calculate_similarity_to_corpus(query, corpus)
        
        assert len(similarities) == len(corpus)
        assert all(0.0 <= s <= 1.0 for s in similarities)
        # First doc should be most similar (Python Django)
        assert similarities[0] > similarities[1]
    
    def test_find_most_similar(self, matcher):
        """Test finding most similar documents."""
        corpus = [
            "Python Django REST API",
            "React frontend development",
            "Python Flask microservices",
            "Java Spring Boot",
            "Python data science",
        ]
        
        query = "Python backend development"
        
        results = matcher.find_most_similar(query, corpus, top_k=3)
        
        assert len(results) == 3
        # Results should be (index, similarity) tuples
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        # Similarities should be sorted descending
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_get_feature_names(self, matcher):
        """Test getting feature names after fitting."""
        corpus = ["Python Django", "React TypeScript"]
        
        matcher.fit(corpus)
        
        features = matcher.get_feature_names()
        
        assert isinstance(features, list)
        assert len(features) > 0
        # Should contain some expected words
        features_lower = [f.lower() for f in features]
        assert any('python' in f for f in features_lower)
    
    def test_get_tfidf_scores(self, matcher):
        """Test getting TF-IDF scores for text."""
        text = "Python developer with Python and Django experience"
        
        scores = matcher.get_tfidf_scores(text)
        
        assert isinstance(scores, dict)
        assert len(scores) > 0
        # All scores should be positive
        assert all(v > 0 for v in scores.values())
        # Should contain expected words
        words = [k.lower() for k in scores.keys()]
        assert any('python' in w for w in words)
    
    def test_job_profile_similarity(self, matcher):
        """Test realistic job description vs profile similarity."""
        job_description = """
        Senior Full Stack Developer position.
        We're building scalable web applications using React, TypeScript, 
        and .NET Core. Experience with Docker, PostgreSQL, and CI/CD required.
        Remote work from Germany available.
        """
        
        profile_text = """
        Experienced Full Stack Engineer with 5+ years of C# and .NET expertise.
        Strong React and TypeScript skills. Built microservices with Docker.
        Located in Germany, open to remote positions.
        """
        
        similarity = matcher.calculate_similarity(job_description, profile_text)
        
        # Should have reasonable similarity (matching terms with stopwords removed)
        assert similarity > 0.08, f"Expected > 0.08, got {similarity:.4f}"
    
    def test_ngram_extraction(self, matcher):
        """Test that bigrams are extracted."""
        # Create matcher with explicit ngram_range
        matcher_bigram = TfidfMatcher(ngram_range=(1, 2))
        
        text = "machine learning engineer with deep learning experience"
        
        scores = matcher_bigram.get_tfidf_scores(text)
        
        # Should have both unigrams and bigrams
        assert any(' ' in word for word in scores.keys()), "No bigrams found"
    
    def test_stopwords_removal(self, matcher):
        """Test that stopwords are removed."""
        text = "the developer with the experience in the programming"
        
        scores = matcher.get_tfidf_scores(text)
        
        # Stopwords like 'the', 'with', 'in' should not be in scores
        words = [k.lower() for k in scores.keys()]
        assert 'the' not in words
        assert 'with' not in words
        assert 'in' not in words
    
    def test_empty_corpus(self, matcher):
        """Test fitting on empty corpus."""
        matcher.fit([])
        
        # Should not crash, but warn
        assert matcher._is_fitted is False
    
    def test_single_word_similarity(self, matcher):
        """Test similarity with single words."""
        similarity = matcher.calculate_similarity("Python", "Python")
        
        # Should be 1.0 for identical words
        assert 0.99 <= similarity <= 1.0

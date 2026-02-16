"""TF-IDF based text similarity matcher."""

from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.logger import get_logger


class TfidfMatcher:
    """
    Calculate text similarity using TF-IDF and cosine similarity.
    
    Used to match job descriptions against user profile text.
    """
    
    def __init__(
        self,
        max_features: int = 1000,
        ngram_range: tuple = (1, 2),
        min_df: int = 1,
        max_df: float = 0.9
    ):
        """
        Initialize TF-IDF matcher.
        
        Args:
            max_features: Maximum number of features (words)
            ngram_range: Range of n-grams (1,2) = unigrams + bigrams
            min_df: Minimum document frequency
            max_df: Maximum document frequency (ignore common words)
        """
        self.logger = get_logger("matcher.tfidf")
        
        # Vectorizer for large corpus (with max_df filtering)
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
        
        # Vectorizer for small corpus/pairwise comparison (no max_df filtering)
        self._small_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=1,
            max_df=1.0,  # Don't filter common words in small corpus
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
        
        self._is_fitted = False
        self._corpus_vectors = None
    
    def fit(self, corpus: List[str]):
        """
        Fit vectorizer on a corpus of documents.
        
        Args:
            corpus: List of text documents
        """
        if not corpus:
            self.logger.warning("Empty corpus provided to fit()")
            return
        
        self.logger.info(f"Fitting TF-IDF vectorizer on {len(corpus)} documents")
        
        self._corpus_vectors = self.vectorizer.fit_transform(corpus)
        self._is_fitted = True
    
    def calculate_similarity(
        self,
        text1: str,
        text2: str,
        fit_on_texts: bool = True
    ) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text (e.g., job description)
            text2: Second text (e.g., profile text)
            fit_on_texts: Whether to fit vectorizer on these texts
        
        Returns:
            Cosine similarity (0-1, higher is more similar)
        """
        if not text1 or not text2:
            self.logger.warning("Empty text provided to calculate_similarity()")
            return 0.0
        
        # Use small vectorizer for pairwise comparison (no max_df filtering)
        vectorizer = self._small_vectorizer
        
        # Fit vectorizer if needed
        if fit_on_texts:
            vectorizer.fit([text1, text2])
        elif not self._is_fitted:
            # If not fitting and vectorizer not ready, fit now
            vectorizer.fit([text1, text2])
        else:
            # Use corpus-fitted vectorizer
            vectorizer = self.vectorizer
        
        # Transform texts to TF-IDF vectors
        try:
            vec1 = vectorizer.transform([text1])
            vec2 = vectorizer.transform([text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(vec1, vec2)[0][0]
            
            # Ensure range [0, 1]
            similarity = max(0.0, min(1.0, similarity))
            
            self.logger.debug(f"TF-IDF similarity: {similarity:.4f}")
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate similarity: {e}", exc_info=True)
            return 0.0
    
    def calculate_similarity_to_corpus(
        self,
        query_text: str,
        corpus: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Calculate similarity of query text to all documents in corpus.
        
        Args:
            query_text: Query text to compare
            corpus: Corpus of documents (if None, uses fitted corpus)
        
        Returns:
            Array of similarity scores (one per corpus document)
        """
        if corpus is not None:
            # Fit on new corpus
            self.fit(corpus)
        
        if not self._is_fitted:
            raise ValueError("Vectorizer not fitted. Provide corpus or call fit() first.")
        
        if not query_text:
            return np.zeros(self._corpus_vectors.shape[0])
        
        # Transform query to TF-IDF vector
        query_vector = self.vectorizer.transform([query_text])
        
        # Calculate similarity to all corpus documents
        similarities = cosine_similarity(query_vector, self._corpus_vectors)[0]
        
        return similarities
    
    def find_most_similar(
        self,
        query_text: str,
        corpus: List[str],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar documents from corpus.
        
        Args:
            query_text: Query text
            corpus: Corpus of documents
            top_k: Number of top results to return
        
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        similarities = self.calculate_similarity_to_corpus(query_text, corpus)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return (index, score) tuples
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        
        return results
    
    def get_feature_names(self) -> List[str]:
        """
        Get feature names (words) from fitted vectorizer.
        
        Returns:
            List of feature names
        """
        if not self._is_fitted:
            return []
        
        return self.vectorizer.get_feature_names_out().tolist()
    
    def get_tfidf_scores(self, text: str) -> dict:
        """
        Get TF-IDF scores for words in text.
        
        Args:
            text: Input text
        
        Returns:
            Dict of word -> TF-IDF score
        """
        # Use small vectorizer for single document (no max_df filtering)
        vectorizer = self._small_vectorizer
        vectorizer.fit([text])
        
        vector = vectorizer.transform([text])
        feature_names = vectorizer.get_feature_names_out()
        
        # Get non-zero scores
        scores = {}
        for idx in vector.nonzero()[1]:
            scores[feature_names[idx]] = vector[0, idx]
        
        # Sort by score
        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

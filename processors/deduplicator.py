"""Job deduplication - removes duplicate job postings."""

from typing import List, Set, Tuple, Optional
from difflib import SequenceMatcher

from models.job import Job
from utils.logger import get_logger


class Deduplicator:
    """
    Remove duplicate job postings based on similarity.
    
    Uses multiple strategies:
    1. Exact ID match (same URL)
    2. Title + Company similarity
    3. Description similarity (optional)
    """
    
    def __init__(
        self,
        title_company_threshold: float = 0.85,
        description_threshold: float = 0.90
    ):
        """
        Initialize deduplicator.
        
        Args:
            title_company_threshold: Similarity threshold for title+company (0-1)
            description_threshold: Similarity threshold for descriptions (0-1)
        """
        self.title_company_threshold = title_company_threshold
        self.description_threshold = description_threshold
        self.logger = get_logger("processor.deduplicator")
    
    def remove_duplicates(
        self,
        jobs: List[Job],
        use_description: bool = False
    ) -> List[Job]:
        """
        Remove duplicate jobs from list.
        
        Args:
            jobs: List of jobs to deduplicate
            use_description: If True, also compare descriptions
        
        Returns:
            List of unique jobs
        """
        if not jobs:
            return []
        
        initial_count = len(jobs)
        
        # Step 1: Remove exact ID duplicates
        unique_jobs = self._remove_exact_duplicates(jobs)
        
        self.logger.debug(
            f"Exact ID deduplication: {initial_count} → {len(unique_jobs)} jobs"
        )
        
        # Step 2: Remove similar title+company duplicates
        unique_jobs = self._remove_similar_duplicates(
            unique_jobs,
            use_description=use_description
        )
        
        duplicates_removed = initial_count - len(unique_jobs)
        
        self.logger.info(
            f"Deduplication complete: {initial_count} → {len(unique_jobs)} jobs "
            f"({duplicates_removed} duplicates removed, "
            f"{len(unique_jobs)/initial_count*100:.1f}% retained)"
        )
        
        return unique_jobs
    
    def _remove_exact_duplicates(self, jobs: List[Job]) -> List[Job]:
        """
        Remove jobs with exact same ID.
        
        Args:
            jobs: List of jobs
        
        Returns:
            List with exact duplicates removed
        """
        seen_ids: Set[str] = set()
        unique_jobs = []
        
        for job in jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _remove_similar_duplicates(
        self,
        jobs: List[Job],
        use_description: bool = False
    ) -> List[Job]:
        """
        Remove jobs with similar title + company.
        
        Args:
            jobs: List of jobs
            use_description: If True, also compare descriptions
        
        Returns:
            List with similar duplicates removed
        """
        unique_jobs = []
        seen_signatures: List[Tuple[str, str]] = []
        
        for job in jobs:
            # Create signature from title + company
            signature = (
                job.title.lower().strip(),
                job.company.lower().strip()
            )
            
            # Check if similar to any seen signature
            is_duplicate = False
            
            for seen_sig in seen_signatures:
                similarity = self._calculate_signature_similarity(
                    signature,
                    seen_sig
                )
                
                if similarity >= self.title_company_threshold:
                    # Potential duplicate - check description if requested
                    if use_description:
                        # Find the corresponding job for this signature
                        for unique_job in unique_jobs:
                            unique_sig = (
                                unique_job.title.lower().strip(),
                                unique_job.company.lower().strip()
                            )
                            if unique_sig == seen_sig:
                                desc_similarity = self._calculate_text_similarity(
                                    job.description,
                                    unique_job.description
                                )
                                if desc_similarity >= self.description_threshold:
                                    is_duplicate = True
                                    self.logger.debug(
                                        f"Duplicate found: '{job.title}' at {job.company} "
                                        f"(similarity: {similarity:.2f})"
                                    )
                                break
                    else:
                        is_duplicate = True
                        self.logger.debug(
                            f"Duplicate found: '{job.title}' at {job.company} "
                            f"(similarity: {similarity:.2f})"
                        )
                    break
            
            if not is_duplicate:
                unique_jobs.append(job)
                seen_signatures.append(signature)
        
        return unique_jobs
    
    def _calculate_signature_similarity(
        self,
        sig1: Tuple[str, str],
        sig2: Tuple[str, str]
    ) -> float:
        """
        Calculate similarity between two job signatures.
        
        Args:
            sig1: First signature (title, company)
            sig2: Second signature (title, company)
        
        Returns:
            Similarity score (0-1)
        """
        title1, company1 = sig1
        title2, company2 = sig2
        
        # Calculate title similarity
        title_sim = self._calculate_text_similarity(title1, title2)
        
        # Calculate company similarity
        company_sim = self._calculate_text_similarity(company1, company2)
        
        # Weighted average (title more important)
        similarity = 0.7 * title_sim + 0.3 * company_sim
        
        return similarity
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using SequenceMatcher.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0-1)
        """
        # Use SequenceMatcher for fast similarity calculation
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_duplicates(
        self,
        jobs: List[Job],
        threshold: Optional[float] = None
    ) -> List[Tuple[Job, Job, float]]:
        """
        Find duplicate pairs without removing them.
        
        Args:
            jobs: List of jobs
            threshold: Similarity threshold (uses default if None)
        
        Returns:
            List of (job1, job2, similarity) tuples for duplicates
        """
        if threshold is None:
            threshold = self.title_company_threshold
        
        duplicates = []
        
        for i, job1 in enumerate(jobs):
            for job2 in jobs[i+1:]:
                # Calculate signature similarity
                sig1 = (job1.title.lower().strip(), job1.company.lower().strip())
                sig2 = (job2.title.lower().strip(), job2.company.lower().strip())
                
                similarity = self._calculate_signature_similarity(sig1, sig2)
                
                if similarity >= threshold:
                    duplicates.append((job1, job2, similarity))
        
        return duplicates
    
    def get_deduplication_stats(self, jobs: List[Job]) -> dict:
        """
        Get statistics about potential duplicates without removing them.
        
        Args:
            jobs: List of jobs
        
        Returns:
            Dict with deduplication statistics
        """
        # Find exact ID duplicates
        seen_ids = set()
        exact_duplicates = 0
        for job in jobs:
            if job.id in seen_ids:
                exact_duplicates += 1
            else:
                seen_ids.add(job.id)
        
        # Find similar duplicates
        similar_pairs = self.find_duplicates(jobs)
        
        stats = {
            'total_jobs': len(jobs),
            'exact_duplicates': exact_duplicates,
            'similar_duplicate_pairs': len(similar_pairs),
            'estimated_unique': len(jobs) - exact_duplicates - len(similar_pairs),
            'threshold': self.title_company_threshold
        }
        
        return stats

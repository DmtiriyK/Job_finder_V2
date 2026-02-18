"""Job filtering logic - pre-filters jobs before scoring."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from models.job import Job
from utils.logger import get_logger


class JobFilter:
    """
    Filter jobs based on various criteria.
    
    Applies pre-filtering before scoring to reduce the number
    of jobs that need to be processed.
    """
    
    def __init__(self):
        """Initialize job filter."""
        self.logger = get_logger("processor.filter")
    
    def apply(
        self,
        jobs: List[Job],
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Job]:
        """
        Apply filters to job list.
        
        Args:
            jobs: List of jobs to filter
            criteria: Filter criteria dict with keys:
                - locations: List of acceptable locations (checks if any match)
                - min_description_length: Minimum description length
                - max_age_days: Maximum job age in days
                - role_keywords: Keywords that must appear in title/description
                - exclude_keywords: Keywords to exclude jobs
                - remote_only: If True, only include remote jobs
                - contract_types: List of acceptable contract types
        
        Returns:
            Filtered list of jobs
        """
        if not criteria:
            return jobs
        
        filtered = jobs
        initial_count = len(filtered)
        
        # Apply location filter
        if criteria.get('locations'):
            filtered = self._filter_by_location(
                filtered,
                criteria['locations']
            )
            self.logger.debug(
                f"Location filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply description length filter
        if criteria.get('min_description_length'):
            filtered = self._filter_by_description_length(
                filtered,
                criteria['min_description_length']
            )
            self.logger.debug(
                f"Description length filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply age filter
        if criteria.get('max_age_days'):
            filtered = self._filter_by_age(
                filtered,
                criteria['max_age_days']
            )
            self.logger.debug(
                f"Age filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply role keywords filter (must match)
        if criteria.get('role_keywords'):
            filtered = self._filter_by_keywords(
                filtered,
                criteria['role_keywords'],
                must_match=True
            )
            self.logger.debug(
                f"Role keywords filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply exclude keywords filter (must not match)
        if criteria.get('exclude_keywords'):
            filtered = self._filter_by_keywords(
                filtered,
                criteria['exclude_keywords'],
                must_match=False
            )
            self.logger.debug(
                f"Exclude keywords filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply seniority filter (exclude Senior/Lead in title)
        if criteria.get('exclude_senior_lead'):
            filtered = self._filter_by_seniority(filtered)
            self.logger.debug(
                f"Seniority filter (exclude Senior/Lead): {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply remote-only filter
        if criteria.get('remote_only'):
            filtered = self._filter_by_remote(filtered)
            self.logger.debug(
                f"Remote-only filter: {initial_count} → {len(filtered)} jobs"
            )
        
        # Apply contract type filter
        if criteria.get('contract_types'):
            filtered = self._filter_by_contract_type(
                filtered,
                criteria['contract_types']
            )
            self.logger.debug(
                f"Contract type filter: {initial_count} → {len(filtered)} jobs"
            )
        
        self.logger.info(
            f"Total filtering: {initial_count} → {len(filtered)} jobs "
            f"({len(filtered)/initial_count*100:.1f}% retained)"
        )
        
        return filtered
    
    def _filter_by_location(
        self,
        jobs: List[Job],
        locations: List[str]
    ) -> List[Job]:
        """
        Filter jobs by location.
        
        Args:
            jobs: List of jobs
            locations: List of acceptable locations (case-insensitive partial match)
        
        Returns:
            Filtered jobs
        """
        locations_lower = [loc.lower() for loc in locations]
        
        filtered = []
        for job in jobs:
            job_location = job.location.lower()
            remote_type = (job.remote_type or '').lower()
            
            # Check if any location matches
            matches = any(
                loc in job_location or loc in remote_type
                for loc in locations_lower
            )
            
            if matches:
                filtered.append(job)
        
        return filtered
    
    def _filter_by_description_length(
        self,
        jobs: List[Job],
        min_length: int
    ) -> List[Job]:
        """
        Filter jobs by minimum description length.
        
        Args:
            jobs: List of jobs
            min_length: Minimum description length
        
        Returns:
            Filtered jobs
        """
        return [
            job for job in jobs
            if len(job.description) >= min_length
        ]
    
    def _filter_by_age(
        self,
        jobs: List[Job],
        max_age_days: int
    ) -> List[Job]:
        """
        Filter jobs by maximum age.
        
        Args:
            jobs: List of jobs
            max_age_days: Maximum age in days
        
        Returns:
            Filtered jobs
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        return [
            job for job in jobs
            if job.posted_date >= cutoff_date
        ]
    
    def _filter_by_keywords(
        self,
        jobs: List[Job],
        keywords: List[str],
        must_match: bool = True
    ) -> List[Job]:
        """
        Filter jobs by keywords.
        
        Args:
            jobs: List of jobs
            keywords: List of keywords
            must_match: If True, jobs must match at least one keyword.
                       If False, jobs must NOT match any keyword.
        
        Returns:
            Filtered jobs
        """
        keywords_lower = [kw.lower() for kw in keywords]
        
        filtered = []
        for job in jobs:
            searchable = f"{job.title} {job.description}".lower()
            
            # Check if any keyword matches
            matches = any(kw in searchable for kw in keywords_lower)
            
            # Include based on must_match flag
            if must_match and matches:
                filtered.append(job)
            elif not must_match and not matches:
                filtered.append(job)
        
        return filtered
    
    def _filter_by_remote(self, jobs: List[Job]) -> List[Job]:
        """
        Filter to only remote jobs.
        
        Args:
            jobs: List of jobs
        
        Returns:
            Filtered jobs (only remote)
        """
        remote_keywords = ['remote', 'full remote', 'fully remote', 'work from home']
        
        filtered = []
        for job in jobs:
            remote_type = (job.remote_type or '').lower()
            location = job.location.lower()
            
            # Check if remote type or location indicates remote
            is_remote = any(
                kw in remote_type or kw in location
                for kw in remote_keywords
            )
            
            if is_remote:
                filtered.append(job)
        
        return filtered
    
    def _filter_by_contract_type(
        self,
        jobs: List[Job],
        contract_types: List[str]
    ) -> List[Job]:
        """
        Filter jobs by contract type.
        
        Args:
            jobs: List of jobs
            contract_types: List of acceptable contract types
        
        Returns:
            Filtered jobs
        """
        contract_types_lower = [ct.lower() for ct in contract_types]
        
        filtered = []
        for job in jobs:
            if job.contract_type:
                job_contract = job.contract_type.lower()
                
                # Check if contract type matches
                if any(ct in job_contract for ct in contract_types_lower):
                    filtered.append(job)
            else:
                # If no contract type specified, include job
                filtered.append(job)
        
        return filtered
    
    def _filter_by_seniority(self, jobs: List[Job]) -> List[Job]:
        """
        Filter out Senior/Lead positions by checking title.
        
        Args:
            jobs: List of jobs
        
        Returns:
            Jobs without Senior/Lead in title
        """
        senior_keywords = [
            'senior', 'sr.', 'sr', 'lead', 'tech lead', 'team lead',
            'principal', 'staff', 'architect', 'head of'
        ]
        
        filtered = []
        for job in jobs:
            title_lower = job.title.lower()
            
            # Exclude if any senior keyword found in title
            has_senior = any(keyword in title_lower for keyword in senior_keywords)
            
            if not has_senior:
                filtered.append(job)
        
        return filtered
    
    def get_filter_stats(
        self,
        jobs: List[Job],
        criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about filtering without applying filters.
        
        Args:
            jobs: List of jobs
            criteria: Filter criteria
        
        Returns:
            Dict with filter statistics
        """
        stats = {
            'total_jobs': len(jobs),
            'filters_applied': [],
            'estimated_retained': len(jobs)
        }
        
        if not criteria:
            return stats
        
        # Simulate each filter
        current_jobs = jobs
        
        if criteria.get('locations'):
            filtered = self._filter_by_location(current_jobs, criteria['locations'])
            stats['filters_applied'].append({
                'name': 'locations',
                'before': len(current_jobs),
                'after': len(filtered)
            })
            current_jobs = filtered
        
        if criteria.get('min_description_length'):
            filtered = self._filter_by_description_length(
                current_jobs,
                criteria['min_description_length']
            )
            stats['filters_applied'].append({
                'name': 'description_length',
                'before': len(current_jobs),
                'after': len(filtered)
            })
            current_jobs = filtered
        
        if criteria.get('max_age_days'):
            filtered = self._filter_by_age(current_jobs, criteria['max_age_days'])
            stats['filters_applied'].append({
                'name': 'age',
                'before': len(current_jobs),
                'after': len(filtered)
            })
            current_jobs = filtered
        
        stats['estimated_retained'] = len(current_jobs)
        stats['retention_rate'] = len(current_jobs) / len(jobs) if jobs else 0
        
        return stats

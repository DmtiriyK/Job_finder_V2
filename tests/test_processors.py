"""Tests for processors (filter, deduplicator)."""

import pytest
from datetime import datetime, timedelta

from models.job import Job
from processors.filter import JobFilter
from processors.deduplicator import Deduplicator


# ============================================================================
# JobFilter Tests
# ============================================================================

class TestJobFilter:
    """Tests for JobFilter."""
    
    @pytest.fixture
    def filter(self):
        """Create JobFilter instance."""
        return JobFilter()
    
    @pytest.fixture
    def sample_jobs(self):
        """Create sample jobs for testing."""
        jobs = [
            Job(
                id="job1",
                title="Senior Full Stack Engineer",
                company="TechCorp",
                location="Berlin, Germany",
                remote_type="Full Remote",
                url="https://example.com/job1",
                description="We are looking for a senior full stack engineer with React and .NET experience. " * 5,
                posted_date=datetime.now() - timedelta(days=2),
                source="test"
            ),
            Job(
                id="job2",
                title="Junior Frontend Developer",
                company="StartupX",
                location="Munich, Germany",
                remote_type="Hybrid",
                url="https://example.com/job2",
                description="Join our team as a junior frontend developer. Short description.",
                posted_date=datetime.now() - timedelta(days=10),
                source="test"
            ),
            Job(
                id="job3",
                title="Backend Engineer Python",
                company="DataCo",
                location="Remote Worldwide",
                remote_type="Full Remote",
                url="https://example.com/job3",
                description="We need a backend engineer with Python and Django expertise. " * 10,
                posted_date=datetime.now() - timedelta(days=20),
                source="test"
            ),
            Job(
                id="job4",
                title="DevOps Engineer",
                company="CloudTech",
                location="San Francisco, USA",
                remote_type="Onsite",
                url="https://example.com/job4",
                description="Looking for DevOps engineer with Kubernetes and AWS experience. " * 8,
                posted_date=datetime.now() - timedelta(days=5),
                source="test"
            ),
        ]
        return jobs
    
    def test_filter_initialization(self, filter):
        """Test filter initialization."""
        assert filter is not None
        assert hasattr(filter, 'logger')
    
    def test_no_criteria(self, filter, sample_jobs):
        """Test that no criteria returns all jobs."""
        filtered = filter.apply(sample_jobs, criteria=None)
        assert len(filtered) == len(sample_jobs)
    
    def test_filter_by_location(self, filter, sample_jobs):
        """Test location filtering."""
        criteria = {'locations': ['Germany']}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs 1 and 2 (Berlin, Munich)
        assert len(filtered) == 2
        assert all('Germany' in job.location for job in filtered)
    
    def test_filter_by_remote(self, filter, sample_jobs):
        """Test remote-only filtering."""
        criteria = {'locations': ['Remote']}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs 1 and 3
        assert len(filtered) >= 2
    
    def test_filter_by_description_length(self, filter, sample_jobs):
        """Test description length filtering."""
        criteria = {'min_description_length': 200}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should filter out job2 (short description)
        assert len(filtered) == 3
        assert all(len(job.description) >= 200 for job in filtered)
    
    def test_filter_by_age(self, filter, sample_jobs):
        """Test age filtering."""
        criteria = {'max_age_days': 7}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs 1, 4 (posted within 7 days)
        assert len(filtered) == 2
        cutoff = datetime.now() - timedelta(days=7)
        assert all(job.posted_date >= cutoff for job in filtered)
    
    def test_filter_by_role_keywords(self, filter, sample_jobs):
        """Test role keywords filtering."""
        criteria = {'role_keywords': ['Full Stack', 'Backend']}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs 1 and 3
        assert len(filtered) == 2
    
    def test_filter_by_exclude_keywords(self, filter, sample_jobs):
        """Test exclude keywords filtering."""
        criteria = {'exclude_keywords': ['Junior']}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should exclude job2
        assert len(filtered) == 3
        assert all('Junior' not in job.title for job in filtered)
    
    def test_filter_remote_only(self, filter, sample_jobs):
        """Test remote-only filter."""
        criteria = {'remote_only': True}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs 1 and 3
        assert len(filtered) == 2
        assert all('remote' in job.remote_type.lower() for job in filtered)
    
    def test_filter_by_contract_type(self, filter, sample_jobs):
        """Test contract type filtering."""
        # Add contract types to some jobs
        sample_jobs[0].contract_type = "Full-time"
        sample_jobs[1].contract_type = "Contract"
        
        criteria = {'contract_types': ['Full-time']}
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should include jobs with Full-time or None contract_type
        assert len(filtered) >= 1
    
    def test_multiple_criteria(self, filter, sample_jobs):
        """Test applying multiple criteria."""
        criteria = {
            'locations': ['Germany', 'Remote'],
            'max_age_days': 14,
            'min_description_length': 150
        }
        filtered = filter.apply(sample_jobs, criteria)
        
        # Should apply all filters
        assert all(
            any(loc in job.location or loc in job.remote_type 
                for loc in ['Germany', 'Remote'])
            for job in filtered
        )
        assert all(len(job.description) >= 150 for job in filtered)
        cutoff = datetime.now() - timedelta(days=14)
        assert all(job.posted_date >= cutoff for job in filtered)
    
    def test_get_filter_stats(self, filter, sample_jobs):
        """Test getting filter statistics."""
        criteria = {
            'locations': ['Germany'],
            'max_age_days': 7
        }
        stats = filter.get_filter_stats(sample_jobs, criteria)
        
        assert stats['total_jobs'] == len(sample_jobs)
        assert 'filters_applied' in stats
        assert 'estimated_retained' in stats
        assert 'retention_rate' in stats


# ============================================================================
# Deduplicator Tests
# ============================================================================

class TestDeduplicator:
    """Tests for Deduplicator."""
    
    @pytest.fixture
    def deduplicator(self):
        """Create Deduplicator instance."""
        return Deduplicator()
    
    @pytest.fixture
    def jobs_with_duplicates(self):
        """Create jobs with some duplicates."""
        jobs = [
            Job(
                id="job1",
                title="Senior Full Stack Engineer",
                company="TechCorp",
                location="Berlin",
                remote_type="Remote",
                url="https://example.com/job1",
                description="Looking for senior full stack engineer",
                posted_date=datetime.now(),
                source="source1"
            ),
            Job(
                id="job2",
                title="Senior Full Stack Engineer",
                company="TechCorp",
                location="Berlin",
                remote_type="Remote",
                url="https://example.com/job2",  # Different URL
                description="Looking for senior full stack developer",  # Slightly different
                posted_date=datetime.now(),
                source="source2"
            ),
            Job(
                id="job3",
                title="Backend Engineer Python",
                company="DataCo",
                location="Munich",
                remote_type="Remote",
                url="https://example.com/job3",
                description="Python backend engineer needed",
                posted_date=datetime.now(),
                source="source1"
            ),
            Job(
                id="job1",  # Exact duplicate ID
                title="Senior Full Stack Engineer",
                company="TechCorp",
                location="Berlin",
                remote_type="Remote",
                url="https://example.com/job1",
                description="Looking for senior full stack engineer",
                posted_date=datetime.now(),
                source="source1"
            ),
        ]
        return jobs
    
    def test_deduplicator_initialization(self, deduplicator):
        """Test deduplicator initialization."""
        assert deduplicator is not None
        assert deduplicator.title_company_threshold == 0.85
        assert deduplicator.description_threshold == 0.90
    
    def test_remove_exact_duplicates(self, deduplicator, jobs_with_duplicates):
        """Test removal of exact ID duplicates."""
        unique = deduplicator.remove_duplicates(jobs_with_duplicates)
        
        # Should remove job with duplicate ID
        assert len(unique) < len(jobs_with_duplicates)
        
        # All IDs should be unique
        ids = [job.id for job in unique]
        assert len(ids) == len(set(ids))
    
    def test_remove_similar_duplicates(self, deduplicator, jobs_with_duplicates):
        """Test removal of similar duplicates."""
        unique = deduplicator.remove_duplicates(jobs_with_duplicates)
        
        # Should remove similar jobs (job1 and job2 are similar)
        assert len(unique) <= 2  # At most 2 unique jobs
    
    def test_similarity_threshold(self):
        """Test custom similarity threshold."""
        dedup = Deduplicator(title_company_threshold=0.95)
        
        jobs = [
            Job(
                id="j1",
                title="Full Stack Engineer",
                company="TechCorp",
                location="Berlin",
                remote_type="Remote",
                url="https://example.com/1",
                description="Job description for Full Stack Engineer position at TechCorp",
                posted_date=datetime.now(),
                source="test"
            ),
            Job(
                id="j2",
                title="Full Stack Developer",  # Slightly different
                company="TechCorp",
                location="Berlin",
                remote_type="Remote",
                url="https://example.com/2",
                description="Job description for Full Stack Developer position at TechCorp",
                posted_date=datetime.now(),
                source="test"
            ),
        ]
        
        unique = dedup.remove_duplicates(jobs)
        
        # With high threshold (0.95), these might not be considered duplicates
        assert len(unique) >= 1
    
    def test_find_duplicates(self, deduplicator, jobs_with_duplicates):
        """Test finding duplicate pairs."""
        duplicates = deduplicator.find_duplicates(jobs_with_duplicates)
        
        # Should find at least one duplicate pair
        assert len(duplicates) >= 1
        
        # Each duplicate is a tuple of (job1, job2, similarity)
        for dup in duplicates:
            assert len(dup) == 3
            job1, job2, similarity = dup
            assert isinstance(job1, Job)
            assert isinstance(job2, Job)
            assert 0 <= similarity <= 1
    
    def test_get_deduplication_stats(self, deduplicator, jobs_with_duplicates):
        """Test getting deduplication statistics."""
        stats = deduplicator.get_deduplication_stats(jobs_with_duplicates)
        
        assert 'total_jobs' in stats
        assert 'exact_duplicates' in stats
        assert 'similar_duplicate_pairs' in stats
        assert 'estimated_unique' in stats
        assert stats['total_jobs'] == len(jobs_with_duplicates)
        assert stats['exact_duplicates'] >= 1  # At least one exact duplicate
    
    def test_empty_list(self, deduplicator):
        """Test deduplication with empty list."""
        unique = deduplicator.remove_duplicates([])
        assert len(unique) == 0
    
    def test_single_job(self, deduplicator):
        """Test deduplication with single job."""
        job = Job(
            id="job1",
            title="Engineer",
            company="Company",
            location="Location",
            remote_type="Remote",
            url="https://example.com",
            description="Description",
            posted_date=datetime.now(),
            source="test"
        )
        
        unique = deduplicator.remove_duplicates([job])
        assert len(unique) == 1
        assert unique[0] == job

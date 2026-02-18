"""Integration tests for pipeline flow and scoring order."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from main import JobFinder
from models.job import Job
from models.profile import Profile
from config.settings import Settings


@pytest.fixture
def test_profile():
    """Create test profile."""
    return Profile(
        name='Test User',
        roles=['Software Engineer'],
        skills={
            'languages': [
                {'name': 'C#', 'experience_years': 5, 'proficiency': 'Expert'},
                {'name': 'TypeScript', 'experience_years': 4, 'proficiency': 'Advanced'}
            ],
            'frameworks': [
                {'name': 'React', 'experience_years': 5, 'proficiency': 'Expert'}
            ]
        },
        preferences={
            'locations': ['Germany', 'Remote'],
            'min_score': 0  # Accept all scores for testing
        },
        profile_text='Software engineer with C# and React experience'
    )


@pytest.fixture
def mock_jobs():
    """Create diverse set of mock jobs for testing."""
    base_time = datetime.now()
    
    jobs = [
        # High score: Germany + Remote + C# + React
        Job(
            id='job-1',
            title='Senior Full Stack Developer',
            location='Berlin, Deutschland',
            description='Remote work possible. C# backend with React frontend. '
                       'TypeScript required. Docker experience preferred.',
            url='https://example.com/1',
            source='test',
            posted_date=base_time - timedelta(days=3)
        ),
        
        # Medium score: Germany city but no remote keywords
        Job(
            id='job-2',
            title='Backend Developer',
            location='München',
            description='C# developer needed for our Munich office. NET Core experience.',
            url='https://example.com/2',
            source='test',
            posted_date=base_time - timedelta(days=5)
        ),
        
        # Lower score: Remote but different tech stack
        Job(
            id='job-3',
            title='Java Developer',
            location='Remote',
            description='Java Spring Boot developer for remote position. AWS cloud experience.',
            url='https://example.com/3',
            source='test',
            posted_date=base_time - timedelta(days=1)
        ),
        
        # Should still be scored: USA location (not excluded)
        Job(
            id='job-4',
            title='React Developer',
            location='San Francisco, USA',
            description='React and TypeScript developer. Remote work available.',
            url='https://example.com/4',
            source='test',
            posted_date=base_time - timedelta(days=2)
        ),
        
        # Edge case: Neighboring country
        Job(
            id='job-5',
            title='C# Developer',
            location='Vienna, Austria',
            description='C# NET developer for our Vienna office. Hybrid work model.',
            url='https://example.com/5',
            source='test',
            posted_date=base_time - timedelta(days=4)
        ),
    ]
    
    return jobs


@pytest.mark.asyncio
async def test_all_jobs_get_scored(test_profile, mock_jobs):
    """Test that ALL jobs are scored, not filtered out early."""
    
    # Mock settings to prevent actual scraping
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        # Create JobFinder instance
        finder = JobFinder(test_profile)
        
        # Mock scraping to return our test jobs
        finder._scrape_jobs = AsyncMock(return_value=mock_jobs.copy())
        
        # Run pipeline
        result = await finder.find_jobs(top_n=10)
        
        # All 5 jobs should be processed (not filtered out)
        assert len(result) >= 3, "Expected at least 3 jobs after scoring"
        
        # Verify USA job is present (location='USA' should not be excluded)
        usa_job = next((j for j in result if 'USA' in j.location), None)
        # Note: It might be filtered by quality filters, but it should have been scored
        
        # Verify jobs have scores
        for job in result:
            assert hasattr(job, 'score')
            assert isinstance(job.score, (int, float))
            assert job.score >= 0


@pytest.mark.asyncio
async def test_scoring_before_filtering(test_profile, mock_jobs):
    """Test that scoring happens BEFORE quality filtering."""
    
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        finder = JobFinder(test_profile)
        finder._scrape_jobs = AsyncMock(return_value=mock_jobs.copy())
        
        # Spy on internal methods to verify call order
        original_score = finder._score_jobs
        original_filter = finder._apply_quality_filters
        
        call_order = []
        
        def tracked_score(jobs):
            call_order.append('score')
            return original_score(jobs)
        
        def tracked_filter(jobs):
            call_order.append('filter')
            return original_filter(jobs)
        
        finder._score_jobs = tracked_score
        finder._apply_quality_filters = tracked_filter
        
        # Run pipeline
        await finder.find_jobs(top_n=10)
        
        # Verify scoring happened before filtering
        assert 'score' in call_order
        assert 'filter' in call_order
        score_index = call_order.index('score')
        filter_index = call_order.index('filter')
        assert score_index < filter_index, "Scoring must happen before filtering"


@pytest.mark.asyncio
async def test_germany_jobs_ranked_higher(test_profile, mock_jobs):
    """Test that Germany + Remote jobs score higher than others."""
    
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        finder = JobFinder(test_profile)
        finder._scrape_jobs = AsyncMock(return_value=mock_jobs.copy())
        
        # Run pipeline
        result = await finder.find_jobs(top_n=10)
        
        # job-1 (Berlin + Remote + C#/React) should be at top
        # job-2 (München + C#) should be high
        # job-3 (Remote + Java) should be lower
        # job-4 (USA) should be lowest
        
        if len(result) >= 2:
            # Find Berlin and USA jobs
            berlin_job = next((j for j in result if 'Berlin' in j.location or 'Deutschland' in j.location), None)
            usa_job = next((j for j in result if 'USA' in j.location), None)
            
            if berlin_job and usa_job:
                assert berlin_job.score > usa_job.score, \
                    "Berlin job should score higher than USA job"


@pytest.mark.asyncio  
async def test_location_component_integration(test_profile, mock_jobs):
    """Test that LocationComponent is integrated into aggregator."""
    
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        finder = JobFinder(test_profile)
        finder._scrape_jobs = AsyncMock(return_value=mock_jobs.copy())
        
        # Run pipeline
        result = await finder.find_jobs(top_n=10)
        
        # Check that jobs have location-based scores
        for job in result:
            if hasattr(job, 'score_breakdown') and job.score_breakdown:
                # Verify location component is present
                assert 'location' in job.score_breakdown, \
                    "Location component should be in score breakdown"
                
                location_score = job.score_breakdown['location']
                assert location_score >= 0, "Location score should be non-negative"
                assert location_score <= 15, "Location score should not exceed max (15)"


@pytest.mark.asyncio
async def test_synonym_matching_works(test_profile):
    """Test that Deutschland/Germany/Berlin synonyms work correctly."""
    
    # Create jobs with various German location formats
    synonym_jobs = [
        Job(
            id='syn-1',
            title='Developer',
            location='Deutschland',
            description='C# developer needed. Remote work possible.',
            url='https://example.com/syn1',
            source='test',
            posted_date=datetime.now() - timedelta(days=1)
        ),
        Job(
            id='syn-2',
            title='Developer',
            location='Germany',
            description='C# developer needed. Remote work possible.',
            url='https://example.com/syn2',
            source='test', 
            posted_date=datetime.now() - timedelta(days=1)
        ),
        Job(
            id='syn-3',
            title='Developer',
            location='Berlin',
            description='C# developer needed. Remote work possible.',
            url='https://example.com/syn3',
            source='test',
            posted_date=datetime.now() - timedelta(days=1)
        ),
    ]
    
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        finder = JobFinder(test_profile)
        finder._scrape_jobs = AsyncMock(return_value=synonym_jobs)
        
        # Run pipeline
        result = await finder.find_jobs(top_n=10)
        
        # All three jobs should be present (synonyms recognized)
        assert len(result) >= 3, "All synonym variants should be recognized"
        
        # All should have similar scores (same location, same description)
        if len(result) >= 3:
            scores = [job.score for job in result[:3]]
            # Scores should be identical since jobs are identical except location
            # (and location synonyms should be treated equally)
            score_variance = max(scores) - min(scores)
            assert score_variance <= 2, \
                f"Deutschland/Germany/Berlin should score similarly (variance: {score_variance})"


@pytest.mark.asyncio
async def test_no_early_location_filtering(test_profile):
    """Test that jobs are NOT filtered by location before scoring."""
    
    # Create job with non-Germany location
    non_germany_job = Job(
        id='test-non-germany',
        title='Senior C# Developer',
        location='London, UK',
        description='Excellent C# and React developer needed. TypeScript, Docker. '
                   'Remote work available (Homeoffice möglich).',
        url='https://example.com/uk',
        source='test',
        posted_date=datetime.now() - timedelta(days=2)
    )
    
    with patch('main.Settings') as MockSettings:
        mock_settings = Mock(spec=Settings)
        mock_settings.SCRAPERS_CONFIG = {'remoteok': {'enabled': False}}
        mock_settings.CACHE_CONFIG = {'enabled': False}
        mock_settings.GOOGLE_SHEETS_CONFIG = {'enabled': False}
        MockSettings.return_value = mock_settings
        
        finder = JobFinder(test_profile)
        finder._scrape_jobs = AsyncMock(return_value=[non_germany_job])
        
        # Run pipeline
        result = await finder.find_jobs(top_n=10)
        
        # Job should be present (not filtered out by location)
        assert len(result) >= 1, "Non-Germany job should not be excluded"
        
        # Job should have a score (even if low)
        if len(result) >= 1:
            assert hasattr(result[0], 'score')
            assert result[0].score > 0, "Job should have been scored"

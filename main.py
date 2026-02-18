"""Main entry point for Job Finder pipeline."""

import asyncio
import argparse
import sys
from datetime import datetime
from typing import List, Optional

from models.job import Job
from config.settings import Settings
from scrapers.remoteok import RemoteOKScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.hackernews import HackerNewsScraper
from scrapers.adzuna import AdzunaScraper
from scrapers.indeed import IndeedScraper
from scrapers.stackoverflow import StackOverflowScraper
from scrapers.github_jobs import GitHubJobsScraper
from scrapers.stepstone import StepStoneScraper
from scrapers.xing import XINGScraper
from extractors.tech_extractor import TechStackExtractor
from processors.filter import JobFilter
from processors.deduplicator import Deduplicator
from scorers.aggregator import ScoreAggregator
from integrations.google_sheets import GoogleSheetsWriter
from utils.logger import get_logger


class JobFinderPipeline:
    """
    Main pipeline for scraping, filtering, and scoring jobs.
    """
    
    # Available scrapers (all 9)
    SCRAPERS = {
        'remoteok': RemoteOKScraper,
        'weworkremotely': WeWorkRemotelyScraper,
        'hackernews': HackerNewsScraper,
        'adzuna': AdzunaScraper,
        'indeed': IndeedScraper,
        'stackoverflow': StackOverflowScraper,
        'github': GitHubJobsScraper,
        'stepstone': StepStoneScraper,
        'xing': XINGScraper,
    }
    
    def __init__(
        self,
        scrapers: Optional[List[str]] = None,
        dev_mode: bool = False
    ):
        """
        Initialize pipeline.
        
        Args:
            scrapers: List of scraper names to use (default: all)
            dev_mode: If True, enables development mode (verbose logging)
        """
        self.logger = get_logger("pipeline")
        self.settings = Settings()
        self.dev_mode = dev_mode
        
        # Load profile
        self.profile = self.settings.load_profile()
        self.logger.info(f"Loaded profile: {self.profile.name}")
        
        # Initialize scrapers
        if scrapers:
            self.scrapers = [
                self.SCRAPERS[name]()
                for name in scrapers
                if name in self.SCRAPERS
            ]
        else:
            self.scrapers = [scraper() for scraper in self.SCRAPERS.values()]
        
        self.logger.info(
            f"Initialized {len(self.scrapers)} scrapers: "
            f"{', '.join(s.name for s in self.scrapers)}"
        )
        
        # Initialize processors
        self.tech_extractor = TechStackExtractor()
        self.job_filter = JobFilter()
        self.deduplicator = Deduplicator()
        self.scorer = ScoreAggregator()
    
    async def run(
        self,
        keywords: Optional[List[str]] = None,
        top_n: int = 20
    ) -> List[Job]:
        """
        Run full pipeline.
        
        Args:
            keywords: Optional keywords to filter jobs
            top_n: Number of top jobs to return
        
        Returns:
            List of top N scored jobs
        """
        start_time = datetime.now()
        self.logger.info(f"Starting job scraper at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Scrape jobs from all sources
        all_jobs = await self._scrape_jobs(keywords)
        
        if not all_jobs:
            self.logger.warning("No jobs found after scraping")
            return []
        
        # Step 2: Extract tech stack
        jobs_with_tech = self._extract_tech_stack(all_jobs)
        
        # Step 3: Deduplicate
        unique_jobs = self._deduplicate_jobs(jobs_with_tech)
        
        if not unique_jobs:
            self.logger.warning("No jobs remaining after deduplication")
            return []
        
        # Step 4: Score all jobs (before filtering)
        scored_jobs = self._score_jobs(unique_jobs)
        
        # Step 5: Apply quality filters (age, length)
        quality_filtered = self._apply_quality_filters(scored_jobs)
        
        if not quality_filtered:
            self.logger.warning("No jobs remaining after quality filtering")
            return []
        
        # Step 6: Sort and filter by minimum score
        top_jobs = self._get_top_jobs(quality_filtered, top_n)
        
        # Log summary
        elapsed = (datetime.now() - start_time).total_seconds()
        self._log_summary(top_jobs, elapsed)
        
        return top_jobs
    
    async def _scrape_jobs(self, keywords: Optional[List[str]] = None) -> List[Job]:
        """Scrape jobs from all configured scrapers."""
        self.logger.info(f"Scraping jobs from {len(self.scrapers)} sources...")
        
        all_jobs = []
        
        # Run scrapers in parallel
        tasks = [
            scraper.fetch_jobs(keywords=keywords)
            for scraper in self.scrapers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                self.logger.error(f"Scraper {scraper.name} failed: {result}")
                continue
            
            jobs = result
            all_jobs.extend(jobs)
            self.logger.info(f"Scraping {scraper.name}... Found {len(jobs)} jobs")
        
        self.logger.info(f"Total scraped: {len(all_jobs)} jobs")
        
        return all_jobs
    
    def _apply_quality_filters(self, jobs: List[Job]) -> List[Job]:
        """Apply quality filters (age, description length, location, seniority) to jobs."""
        # Build filter criteria - quality metrics + location filtering + seniority
        criteria = {
            'min_description_length': 50,
            'max_age_days': 14,  # Last 2 weeks
            'locations': self.profile.preferences.get('locations', []),
            'exclude_senior_lead': True  # Exclude Senior/Lead positions
        }
        
        initial_count = len(jobs)
        filtered = self.job_filter.apply(jobs, criteria)
        
        self.logger.info(
            f"Quality, location & seniority filtering: "
            f"{initial_count} → {len(filtered)} jobs"
        )
        
        return filtered
    
    def _extract_tech_stack(self, jobs: List[Job]) -> List[Job]:
        """Extract tech stack from job descriptions."""
        self.logger.info("Extracting tech stack...")
        
        for job in jobs:
            if not job.tech_stack:
                # Extract tech stack from description
                tech_stack = self.tech_extractor.extract(
                    f"{job.title} {job.description}"
                )
                if tech_stack:
                    job.tech_stack = tech_stack
        
        self.logger.info(f"Extracting tech stack... Done ({len(jobs)} jobs)")
        
        return jobs
    
    def _deduplicate_jobs(self, jobs: List[Job]) -> List[Job]:
        """Remove duplicate jobs."""
        initial_count = len(jobs)
        unique_jobs = self.deduplicator.remove_duplicates(jobs)
        
        duplicates_removed = initial_count - len(unique_jobs)
        self.logger.info(
            f"Deduplicating... {initial_count} → {len(unique_jobs)} jobs "
            f"({duplicates_removed} duplicates removed)"
        )
        
        return unique_jobs
    
    def _score_jobs(self, jobs: List[Job]) -> List[Job]:
        """Score all jobs."""
        self.logger.info("Scoring jobs...")
        
        for job in jobs:
            result = self.scorer.score_job(job, self.profile)
            
            # Attach score to job
            job.score_result = result
        
        self.logger.info("Scoring jobs... Done")
        
        return jobs
    
    def _get_top_jobs(self, jobs: List[Job], top_n: int) -> List[Job]:
        """Get top N jobs by score with Remote priority."""
        # Filter by minimum score from profile
        min_score = self.profile.get_min_score()
        
        # Filter scored jobs
        scored_jobs = [
            job for job in jobs
            if hasattr(job, 'score_result') and job.score_result.score >= min_score
        ]
        
        # Define remote priority (higher = better)
        def get_remote_priority(job: Job) -> int:
            remote_type = (job.remote_type or '').lower()
            
            # Full Remote: highest priority
            if any(kw in remote_type for kw in ['remote', '100%', 'homeoffice', 'fully']):
                return 3
            # Hybrid: medium priority
            elif 'hybrid' in remote_type:
                return 2
            # Onsite: lowest priority
            else:
                return 1
        
        # Sort by: 1) Remote priority (desc), 2) Score (desc)
        scored_jobs.sort(
            key=lambda j: (get_remote_priority(j), j.score_result.score),
            reverse=True
        )
        
        return scored_jobs[:top_n]
    
    def _log_summary(self, top_jobs: List[Job], elapsed_seconds: float):
        """Log pipeline summary."""
        if not top_jobs:
            self.logger.info("No jobs passed minimum score threshold")
            return
        
        # Get score range
        scores = [job.score_result.score for job in top_jobs]
        min_score = min(scores)
        max_score = max(scores)
        
        self.logger.info(
            f"Top {len(top_jobs)} jobs (score range: {min_score:.0f}-{max_score:.0f}):"
        )
        
        # Log top jobs
        for i, job in enumerate(top_jobs[:10], 1):
            score = job.score_result.score
            tech = ', '.join(list(job.tech_stack)[:5]) if job.tech_stack else 'N/A'
            
            self.logger.info(
                f"  {i}. [{score:.0f}] {job.title} - {job.company} - {tech}"
            )
        
        if len(top_jobs) > 10:
            self.logger.info(f"  ... and {len(top_jobs) - 10} more")
        
        self.logger.info(f"Pipeline completed in {elapsed_seconds:.0f} seconds")


async def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Job Finder - Scrape, filter, and score job postings'
    )
    
    parser.add_argument(
        '--scrapers',
        type=str,
        help='Comma-separated list of scrapers to use (default: all)',
        default=None
    )
    
    parser.add_argument(
        '--keywords',
        type=str,
        help='Comma-separated list of keywords to filter jobs',
        default=None
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        help='Number of top jobs to show (default: 20)',
        default=20
    )
    
    parser.add_argument(
        '--dev-mode',
        action='store_true',
        help='Enable development mode (verbose logging)'
    )
    
    parser.add_argument(
        '--export-sheets',
        action='store_true',
        help='Export results to Google Sheets'
    )
    
    parser.add_argument(
        '--sheets-name',
        type=str,
        help='Custom Google Sheets name (optional)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Parse scrapers
    scrapers = None
    if args.scrapers:
        scrapers = [s.strip() for s in args.scrapers.split(',')]
    
    # Parse keywords
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',')]
    
    # Initialize pipeline
    pipeline = JobFinderPipeline(
        scrapers=scrapers,
        dev_mode=args.dev_mode
    )
    
    # Run pipeline
    try:
        top_jobs = await pipeline.run(keywords=keywords, top_n=args.top_n)
        
        if not top_jobs:
            print("\nNo jobs found matching criteria.")
            return 0
        
        # Print results
        print(f"\n{'='*80}")
        print(f"TOP {len(top_jobs)} JOBS")
        print(f"{'='*80}\n")
        
        for i, job in enumerate(top_jobs, 1):
            score = job.score_result.score
            print(f"{i}. [{score:.0f}] {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location} ({job.remote_type})")
            if job.tech_stack:
                print(f"   Tech: {', '.join(list(job.tech_stack)[:8])}")
            print(f"   URL: {job.url}")
            print()
        
        # Export to Google Sheets if requested
        if args.export_sheets:
            print(f"\n{'='*80}")
            print("EXPORTING TO GOOGLE SHEETS")
            print(f"{'='*80}\n")
            
            try:
                # Initialize Google Sheets writer
                writer = GoogleSheetsWriter(spreadsheet_name=args.sheets_name)
                
                if not writer.is_enabled():
                    print("⚠️  Google Sheets integration not enabled.")
                    print("   See docs/GOOGLE_SHEETS_SETUP.md for setup instructions.")
                else:
                    # Create scores dict
                    scores_dict = {
                        job.id: job.score_result
                        for job in top_jobs
                    }
                    
                    # Write to sheets
                    success = writer.write_jobs(top_jobs, scores_dict)
                    
                    if success:
                        print("✅ Jobs exported to Google Sheets successfully!")
                    else:
                        print("❌ Failed to export jobs to Google Sheets.")
                        print("   Check logs for details.")
            
            except Exception as e:
                print(f"❌ Error exporting to Google Sheets: {e}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

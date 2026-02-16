"""WeWorkRemotely scraper - parses HTML pages for remote jobs."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.job import Job


class WeWorkRemotelyScraper(BaseScraper):
    """
    Scraper for WeWorkRemotely.com.
    
    WeWorkRemotely provides job listings organized by categories.
    We'll focus on tech/programming categories.
    """
    
    BASE_URL = "https://weworkremotely.com"
    
    # Category URLs for tech jobs
    CATEGORIES = {
        "programming": "/categories/remote-programming-jobs",
        "devops": "/categories/remote-devops-sysadmin-jobs",
        "full-stack": "/categories/remote-full-stack-programming-jobs",
    }
    
    def __init__(self, **kwargs):
        """Initialize WeWorkRemotely scraper."""
        super().__init__(
            name="WeWorkRemotely",
            base_url=self.BASE_URL,
            **kwargs
        )
    
    async def fetch_jobs(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        categories: Optional[List[str]] = None,
        **kwargs
    ) -> List[Job]:
        """
        Fetch jobs from WeWorkRemotely categories.
        
        Args:
            keywords: Keywords to filter jobs (applied to title/description)
            location: Location filter (mostly ignored for remote jobs)
            categories: List of category keys to scrape (default: all)
            **kwargs: Additional parameters
        
        Returns:
            List of Job objects
        """
        try:
            # Determine which categories to scrape
            if categories:
                category_urls = {k: v for k, v in self.CATEGORIES.items() if k in categories}
            else:
                category_urls = self.CATEGORIES
            
            self.logger.info(f"Scraping {len(category_urls)} categories from WeWorkRemotely")
            
            all_jobs = []
            
            # Scrape each category
            for category_name, category_path in category_urls.items():
                try:
                    url = f"{self.BASE_URL}{category_path}"
                    self.logger.debug(f"Fetching category: {category_name} ({url})")
                    
                    # Fetch page HTML
                    response = await self._fetch_url(url)
                    html_content = response.text
                    
                    # Parse HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Find job listings
                    job_listings = soup.find_all('li', class_='feature')
                    
                    if not job_listings:
                        self.logger.warning(f"No job listings found in category: {category_name}")
                        continue
                    
                    self.logger.debug(f"Found {len(job_listings)} listings in {category_name}")
                    
                    # Parse each listing
                    for listing in job_listings:
                        try:
                            job = self._parse_listing(listing, category_name)
                            
                            if job is None:
                                continue
                            
                            # Apply keyword filter
                            if keywords and not self._matches_keywords(job, keywords):
                                continue
                            
                            all_jobs.append(job)
                            
                        except Exception as e:
                            self.logger.error(f"Failed to parse listing: {e}", exc_info=True)
                            continue
                    
                except Exception as e:
                    self.logger.error(f"Failed to scrape category {category_name}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Successfully scraped {len(all_jobs)} jobs from WeWorkRemotely")
            return all_jobs
            
        except Exception as e:
            self.logger.error(f"Failed to fetch jobs from WeWorkRemotely: {e}", exc_info=True)
            return []
    
    def _parse_listing(self, listing: Any, category: str) -> Optional[Job]:
        """
        Parse job listing element into Job model.
        
        Args:
            listing: BeautifulSoup element for job listing
            category: Category name
        
        Returns:
            Job object or None if parsing failed
        """
        try:
            # Find job link
            link_elem = listing.find('a', class_='browse_feature_job_item')
            if not link_elem:
                self.logger.warning("No job link found in listing")
                return None
            
            # Extract URL
            job_path = link_elem.get('href', '').strip()
            if not job_path:
                self.logger.warning("Empty job URL")
                return None
            
            url = f"{self.BASE_URL}{job_path}" if job_path.startswith('/') else job_path
            
            # Extract title
            title_elem = link_elem.find('span', class_='title')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            if not title:
                self.logger.warning("Empty job title")
                return None
            
            # Extract company
            company_elem = link_elem.find('span', class_='company')
            company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
            
            # Extract region/location (optional)
            region_elem = link_elem.find('span', class_='region')
            location = region_elem.get_text(strip=True) if region_elem else 'Worldwide'
            
            # Extract job type tags (contract type, etc.)
            tags = []
            tag_elements = link_elem.find_all('span', class_='tag')
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            
            # Determine contract type from tags
            contract_type = None
            for tag in tags:
                tag_lower = tag.lower()
                if 'full-time' in tag_lower or 'full time' in tag_lower:
                    contract_type = 'Full-time'
                    break
                elif 'contract' in tag_lower:
                    contract_type = 'Contract'
                    break
                elif 'part-time' in tag_lower or 'part time' in tag_lower:
                    contract_type = 'Part-time'
                    break
            
            # Posted date - WeWorkRemotely doesn't provide dates in listings
            # Default to current date (will be filtered if too old)
            posted_date = datetime.now()
            
            # Description placeholder (will need to fetch detail page for full description)
            # For now, use title and tags as description
            description = f"{title}. Category: {category}. "
            if tags:
                description += f"Tags: {', '.join(tags)}."
            
            # Generate unique ID
            job_id = Job.generate_id(url=url, title=title)
            
            # Create Job object
            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location,
                remote_type="Full Remote",  # WeWorkRemotely is remote-only
                url=url,
                description=description,
                posted_date=posted_date,
                source=self.name,
                source_id=url,
                tech_stack=None,  # Will be extracted later by TechStackExtractor
                salary_min=None,
                salary_max=None,
                contract_type=contract_type
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to parse listing: {e}", exc_info=True)
            return None
    
    def parse_job(self, raw_data: Dict[str, Any]) -> Optional[Job]:
        """
        Parse raw job data into Job model.
        
        For WeWorkRemotely, we use _parse_listing() instead.
        This method is here for BaseScraper compatibility.
        
        Args:
            raw_data: Raw job data
        
        Returns:
            Job object or None
        """
        # Not used for WeWorkRemotely (we parse HTML directly)
        return None
    
    def _matches_keywords(self, job: Job, keywords: List[str]) -> bool:
        """
        Check if job matches any of the keywords.
        
        Args:
            job: Job object
            keywords: List of keywords
        
        Returns:
            True if job matches any keyword
        """
        # Combine searchable fields
        searchable = f"{job.title} {job.description} {job.company}".lower()
        
        # Check if any keyword matches
        return any(keyword.lower() in searchable for keyword in keywords)

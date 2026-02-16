"""Scrapers for job boards."""

from scrapers.base import BaseScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.hackernews import HackerNewsScraper
from scrapers.adzuna import AdzunaScraper
from scrapers.indeed import IndeedScraper
from scrapers.stackoverflow import StackOverflowScraper
from scrapers.github_jobs import GitHubJobsScraper
from scrapers.stepstone import StepStoneScraper
from scrapers.xing import XINGScraper

__all__ = [
    "BaseScraper",
    "RemoteOKScraper",
    "WeWorkRemotelyScraper",
    "HackerNewsScraper",
    "AdzunaScraper",
    "IndeedScraper",
    "StackOverflowScraper",
    "GitHubJobsScraper",
    "StepStoneScraper",
    "XINGScraper",
]


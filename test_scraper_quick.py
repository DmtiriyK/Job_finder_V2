"""Quick test for RemoteOK scraper."""

import asyncio
from scrapers.remoteok import RemoteOKScraper


async def main():
    scraper = RemoteOKScraper()
    
    print("Fetching jobs from RemoteOK...")
    jobs = await scraper.fetch_jobs(keywords=["Python"])
    
    print(f"\nFound {len(jobs)} jobs")
    
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job.title}")
        print(f"   Company: {job.company}")
        print(f"   URL: {job.url}")
        print(f"   Location: {job.location}")
        print(f"   Source: {job.source}")
    
    await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())

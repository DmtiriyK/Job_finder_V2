"""Quick test to see RSS feed structure."""

import asyncio
import feedparser
import httpx


async def main():
    client = httpx.AsyncClient(timeout=30.0)
    response = await client.get("https://remoteok.com/remote-jobs.rss")
    
    feed = feedparser.parse(response.text)
    
    print(f"Feed has {len(feed.entries)} entries\n")
    
    # Show first entry structure
    if feed.entries:
        entry = feed.entries[0]
        print("First entry structure:")
        print(f"  title: {entry.get('title', 'N/A')}")
        print(f"  link: {entry.get('link', 'N/A')}")
        print(f"  summary (first 200 chars): {entry.get('summary', 'N/A')[:200]}")
        print(f"  published: {entry.get('published', 'N/A')}")
        print(f"  tags: {entry.get('tags', 'N/A')}")
        print("\nAll keys:", list(entry.keys()))
    
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

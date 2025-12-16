"""
Quick script to run all Playwright scrapers and update latest_jobs.json
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.playwright_scraper import PlaywrightScraper
from normalizer import JobNormalizer


async def run_all_scrapers():
    """Run all scrapers and save results"""
    print("="*70)
    print("PILOT JOBS SCRAPER - FULL RUN")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    scraper = PlaywrightScraper(headless=True)
    normalizer = JobNormalizer()

    all_jobs = []

    # Run all scrapers
    try:
        jobs = await scraper.scrape_all()
        all_jobs.extend(jobs)
    except Exception as e:
        print(f"Error running scrapers: {e}")

    print(f"\n{'='*70}")
    print(f"RAW RESULTS: {len(all_jobs)} jobs found")
    print(f"{'='*70}")

    # Normalize jobs
    normalized_jobs = []
    for job in all_jobs:
        try:
            normalized = normalizer.normalize_job(job)
            normalized_jobs.append(normalized)
        except Exception as e:
            print(f"Error normalizing job: {e}")
            normalized_jobs.append(job)

    # Deduplicate by URL
    seen_urls = set()
    unique_jobs = []
    for job in normalized_jobs:
        url = job.get('application_url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            unique_jobs.append(job)

    print(f"After deduplication: {len(unique_jobs)} unique jobs")

    # Add IDs
    for i, job in enumerate(unique_jobs, 1):
        if 'id' not in job:
            job['id'] = f'scraped-{i}'

    # Save to output
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    # Save timestamped version
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamped_file = output_dir / f'jobs_{timestamp}.json'
    with open(timestamped_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'total_jobs': len(unique_jobs),
            },
            'jobs': unique_jobs
        }, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {timestamped_file}")

    # Update latest_jobs.json (used by frontend)
    latest_file = output_dir / 'latest_jobs.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump({'jobs': unique_jobs}, f, indent=2, ensure_ascii=False)

    print(f"Updated: {latest_file}")

    # Print summary
    print(f"\n{'='*70}")
    print("SCRAPING COMPLETE")
    print(f"{'='*70}")

    # By company
    companies = {}
    for job in unique_jobs:
        company = job.get('company', 'Unknown')
        companies[company] = companies.get(company, 0) + 1

    print("\nJobs by company:")
    for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True):
        print(f"  {company}: {count}")

    # By region
    regions = {}
    for job in unique_jobs:
        region = job.get('region', 'unknown')
        regions[region] = regions.get(region, 0) + 1

    print("\nJobs by region:")
    for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {region}: {count}")

    return unique_jobs


if __name__ == '__main__':
    asyncio.run(run_all_scrapers())

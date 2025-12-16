"""
Upload Scraped Jobs to Supabase

This script runs the scrapers and uploads the results to Supabase.
Run locally to populate the database with real, scraped job data.

Usage:
    python upload_to_supabase.py                    # Run all scrapers
    python upload_to_supabase.py --airline qatar    # Run specific airline
    python upload_to_supabase.py --test             # Test mode (no upload)
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load .env.local from parent directory (use override=True to overwrite any existing env vars)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env.local')
load_dotenv(env_path, override=True)

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Supabase Python client
from supabase import create_client, Client

# Import scrapers
from scrapers.qatar_scraper import QatarAirwaysScraper


def get_supabase_client() -> Client:
    """Create Supabase client with service role key"""
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise ValueError("Missing Supabase credentials in .env.local")

    return create_client(url, key)


def prepare_job_for_upload(job: Dict) -> Dict:
    """Prepare job dict for Supabase insert/upsert"""
    # Map scraped fields to database columns
    return {
        'title': job.get('title', ''),
        'company': job.get('company', ''),
        'location': job.get('location', ''),
        'region': job.get('region', ''),
        'position_type': job.get('position_type', 'pilot'),
        'aircraft_type': job.get('aircraft_type'),
        'type_rating_required': job.get('type_rating_required', False),
        'type_rating_provided': job.get('type_rating_provided', False),
        'min_total_hours': job.get('min_total_hours'),
        'min_pic_hours': job.get('min_pic_hours'),
        'contract_type': job.get('contract_type', 'permanent'),
        'salary_info': job.get('salary_info'),
        'application_url': job.get('application_url', ''),
        'source': job.get('source', 'Scraper'),
        'date_scraped': datetime.now().isoformat(),
        'is_active': True,
        'is_entry_level': job.get('is_entry_level', False),
        'visa_sponsorship': job.get('visa_sponsorship', False),
    }


async def scrape_qatar_airways() -> List[Dict]:
    """Scrape Qatar Airways jobs"""
    scraper = QatarAirwaysScraper()
    return await scraper.fetch_all_jobs()


async def run_all_scrapers() -> List[Dict]:
    """Run all scrapers and collect jobs"""
    all_jobs = []

    # Qatar Airways
    print("\n" + "="*60)
    print("Scraping Qatar Airways...")
    print("="*60)
    qatar_jobs = await scrape_qatar_airways()
    all_jobs.extend(qatar_jobs)

    # TODO: Add more scrapers here as we build them
    # emirates_jobs = await scrape_emirates()
    # all_jobs.extend(emirates_jobs)

    return all_jobs


def upload_jobs_to_supabase(jobs: List[Dict], test_mode: bool = False):
    """Upload jobs to Supabase"""
    if not jobs:
        print("No jobs to upload")
        return

    if test_mode:
        print(f"\n[TEST MODE] Would upload {len(jobs)} jobs:")
        for job in jobs:
            print(f"  - {job.get('title')} ({job.get('company')}) - {job.get('min_total_hours', 'N/A')} hrs")
        return

    try:
        supabase = get_supabase_client()

        # Prepare jobs for upload
        prepared_jobs = [prepare_job_for_upload(job) for job in jobs]

        print(f"\nUploading {len(prepared_jobs)} jobs to Supabase...")

        # Upsert jobs (update if URL exists, insert if not)
        result = supabase.table('pilot_jobs').upsert(
            prepared_jobs,
            on_conflict='application_url'
        ).execute()

        print(f"Successfully uploaded {len(result.data)} jobs")

        # Print summary
        print("\nUploaded jobs:")
        for job in prepared_jobs:
            hours_str = f"{job.get('min_total_hours')} hrs" if job.get('min_total_hours') else "N/A"
            print(f"  ✓ {job['title']} ({job['company']}) - {hours_str}")

    except Exception as e:
        print(f"Error uploading to Supabase: {e}")
        raise


def deactivate_old_jobs(company: str):
    """Mark old jobs from this company as inactive before uploading new ones"""
    try:
        supabase = get_supabase_client()

        # Mark all jobs from this company as inactive
        result = supabase.table('pilot_jobs').update({
            'is_active': False
        }).eq('company', company).execute()

        print(f"Marked {len(result.data)} old {company} jobs as inactive")

    except Exception as e:
        print(f"Error deactivating old jobs: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape and upload pilot jobs to Supabase')
    parser.add_argument('--test', action='store_true', help='Test mode (no upload)')
    parser.add_argument('--airline', type=str, help='Scrape specific airline only')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("PILOT JOBS SCRAPER - SUPABASE UPLOAD")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_jobs = []

    if args.airline:
        airline_lower = args.airline.lower()
        if airline_lower == 'qatar':
            jobs = await scrape_qatar_airways()
            if not args.test:
                deactivate_old_jobs('Qatar Airways')
            all_jobs.extend(jobs)
        else:
            print(f"Unknown airline: {args.airline}")
            print("Available: qatar")
            return
    else:
        # Run all scrapers
        all_jobs = await run_all_scrapers()

    # Upload to Supabase
    upload_jobs_to_supabase(all_jobs, test_mode=args.test)

    print("\n" + "="*70)
    print("SCRAPING COMPLETE")
    print("="*70)
    print(f"Total jobs processed: {len(all_jobs)}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    asyncio.run(main())

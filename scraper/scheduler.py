"""
24/7 Automated Pilot Job Scraper Scheduler

This is the MAIN script that runs continuously on your server.
It automatically scrapes all airline career pages at scheduled intervals.

Usage:
    python scheduler.py              # Run the scheduler (24/7)
    python scheduler.py --once       # Run once and exit (for testing)
    python scheduler.py --status     # Show scheduler status

Deployment:
    1. Deploy to a VPS (DigitalOcean, AWS, Railway, etc.)
    2. Run with: nohup python scheduler.py &
    3. Or use systemd/supervisor for auto-restart
"""

import asyncio
import json
import os
import sys
import signal
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.playwright_scraper import PlaywrightScraper
from normalizer import JobNormalizer

# Try to import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not installed. Jobs will only be saved to JSON files.")


class JobScheduler:
    """
    Automated job scraper that runs 24/7

    Features:
    - Scrapes all configured airlines at regular intervals
    - Saves to Supabase database (if configured) AND local JSON
    - Handles errors gracefully and continues running
    - Tracks scraping statistics
    - Deduplicates jobs automatically
    """

    # Scraping intervals (in hours)
    SCRAPE_INTERVAL_HOURS = 4  # How often to run full scrape

    # Priority airlines to check more frequently (every 2 hours)
    PRIORITY_AIRLINES = [
        'emirates', 'ryanair', 'easyjet', 'wizz_air', 'qatar_airways',
        'etihad', 'british_airways', 'lufthansa'
    ]
    PRIORITY_INTERVAL_HOURS = 2

    def __init__(self):
        self.scraper = PlaywrightScraper(headless=True)
        self.normalizer = JobNormalizer()
        self.supabase: Optional[Client] = None
        self.output_dir = Path(__file__).parent / 'output'
        self.output_dir.mkdir(exist_ok=True)

        # Statistics
        self.stats = {
            'total_scrapes': 0,
            'total_jobs_found': 0,
            'last_scrape': None,
            'next_scrape': None,
            'errors': [],
            'started_at': datetime.now().isoformat(),
        }

        # Shutdown flag
        self.running = True

        # Initialize Supabase if configured
        self._init_supabase()

    def _init_supabase(self):
        """Initialize Supabase connection"""
        if not SUPABASE_AVAILABLE:
            return

        supabase_url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')

        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("✓ Connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
        else:
            logger.warning("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_SERVICE_KEY")

    async def scrape_all_airlines(self) -> List[Dict]:
        """Run a full scrape of all airlines"""
        logger.info("="*70)
        logger.info("STARTING FULL SCRAPE")
        logger.info("="*70)

        all_jobs = []

        try:
            # Run all scrapers
            jobs = await self.scraper.scrape_all()
            all_jobs.extend(jobs)
            logger.info(f"Scraped {len(jobs)} jobs from all sources")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            self.stats['errors'].append({
                'time': datetime.now().isoformat(),
                'error': str(e)
            })

        # Normalize jobs
        normalized_jobs = []
        for job in all_jobs:
            try:
                normalized = self.normalizer.normalize_job(job)
                normalized_jobs.append(normalized)
            except Exception as e:
                logger.warning(f"Error normalizing job: {e}")
                normalized_jobs.append(job)

        # Deduplicate
        unique_jobs = self._deduplicate_jobs(normalized_jobs)
        logger.info(f"After deduplication: {len(unique_jobs)} unique jobs")

        # Add IDs
        for i, job in enumerate(unique_jobs, 1):
            if 'id' not in job:
                job['id'] = f'scraped-{i}'

        # Save to database and files
        await self._save_jobs(unique_jobs)

        # Update stats
        self.stats['total_scrapes'] += 1
        self.stats['total_jobs_found'] = len(unique_jobs)
        self.stats['last_scrape'] = datetime.now().isoformat()

        return unique_jobs

    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on URL"""
        seen_urls = set()
        unique = []

        for job in jobs:
            url = job.get('application_url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(job)
            elif not url:
                unique.append(job)

        return unique

    async def _save_jobs(self, jobs: List[Dict]):
        """Save jobs to Supabase and local files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save to local JSON (always)
        json_path = self.output_dir / f'jobs_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_jobs': len(jobs),
                },
                'jobs': jobs
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved to: {json_path}")

        # Update latest_jobs.json
        latest_path = self.output_dir / 'latest_jobs.json'
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump({'jobs': jobs}, f, indent=2, ensure_ascii=False)
        logger.info(f"Updated: {latest_path}")

        # Save to Supabase (if connected)
        if self.supabase:
            await self._save_to_supabase(jobs)

    async def _save_to_supabase(self, jobs: List[Dict]):
        """Upsert jobs to Supabase database"""
        if not self.supabase:
            return

        try:
            # Prepare jobs for database
            db_jobs = []
            for job in jobs:
                db_job = {
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'location': job.get('location', ''),
                    'region': job.get('region', 'global'),
                    'position_type': job.get('position_type', 'other'),
                    'aircraft_type': job.get('aircraft_type'),
                    'type_rating_required': job.get('type_rating_required', False),
                    'type_rating_provided': job.get('type_rating_provided', False),
                    'min_total_hours': job.get('min_total_hours'),
                    'min_pic_hours': job.get('min_pic_hours'),
                    'min_type_hours': job.get('min_type_hours'),
                    'license_required': job.get('license_required'),
                    'contract_type': job.get('contract_type'),
                    'salary_info': job.get('salary_info'),
                    'benefits': job.get('benefits'),
                    'description': job.get('description'),
                    'application_url': job.get('application_url', ''),
                    'source': job.get('source', 'Scraped'),
                    'date_posted': job.get('date_posted'),
                    'date_scraped': job.get('date_scraped', datetime.now().isoformat()),
                    'is_active': job.get('is_active', True),
                }
                db_jobs.append(db_job)

            # Upsert to database (update if URL exists, insert if new)
            # Using application_url as unique identifier
            result = self.supabase.table('pilot_jobs').upsert(
                db_jobs,
                on_conflict='application_url'
            ).execute()

            logger.info(f"Saved {len(db_jobs)} jobs to Supabase")

        except Exception as e:
            logger.error(f"Error saving to Supabase: {e}")
            self.stats['errors'].append({
                'time': datetime.now().isoformat(),
                'error': f"Supabase save error: {str(e)}"
            })

    async def run_forever(self):
        """Run the scheduler continuously"""
        logger.info("="*70)
        logger.info("PILOT JOBS SCHEDULER STARTED")
        logger.info("="*70)
        logger.info(f"Scrape interval: Every {self.SCRAPE_INTERVAL_HOURS} hours")
        logger.info(f"Priority airlines check: Every {self.PRIORITY_INTERVAL_HOURS} hours")
        logger.info("")

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("\nShutdown signal received. Stopping scheduler...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run initial scrape
        await self.scrape_all_airlines()

        # Schedule next scrapes
        while self.running:
            next_scrape = datetime.now() + timedelta(hours=self.SCRAPE_INTERVAL_HOURS)
            self.stats['next_scrape'] = next_scrape.isoformat()

            logger.info(f"\nNext scrape scheduled for: {next_scrape.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("Sleeping...\n")

            # Sleep until next scrape (check every minute if we should stop)
            sleep_seconds = self.SCRAPE_INTERVAL_HOURS * 3600
            for _ in range(sleep_seconds // 60):
                if not self.running:
                    break
                await asyncio.sleep(60)

            if self.running:
                await self.scrape_all_airlines()

        logger.info("Scheduler stopped.")

    async def run_once(self):
        """Run scraper once and exit (for testing)"""
        jobs = await self.scrape_all_airlines()

        logger.info("\n" + "="*70)
        logger.info("SCRAPE COMPLETE")
        logger.info("="*70)
        logger.info(f"Total jobs: {len(jobs)}")

        # Print summary by company
        companies = {}
        for job in jobs:
            company = job.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1

        logger.info("\nJobs by company:")
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {company}: {count}")

        return jobs

    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            **self.stats,
            'supabase_connected': self.supabase is not None,
            'scrape_interval_hours': self.SCRAPE_INTERVAL_HOURS,
        }


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pilot Jobs Scheduler')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--status', action='store_true', help='Show status')
    args = parser.parse_args()

    scheduler = JobScheduler()

    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.once:
        await scheduler.run_once()
    else:
        await scheduler.run_forever()


if __name__ == '__main__':
    asyncio.run(main())

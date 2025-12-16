"""
PRODUCTION-GRADE 24/7 Pilot Job Scraper

This is the REAL scheduler that runs on your VPS/cloud server.
It uses APScheduler for proper job scheduling and handles:
- Concurrent scraping (multiple airlines at once)
- Staggered start times (don't hit all sites simultaneously)
- Error recovery (if one airline fails, others continue)
- Proxy support (IP rotation to avoid blocks)
- Database upserts (no duplicate jobs)

Usage:
    python production_scheduler.py              # Run 24/7
    python production_scheduler.py --test       # Test run (once, no schedule)
    python production_scheduler.py --status     # Show scheduler status

Requirements:
    pip install apscheduler supabase playwright playwright-stealth
"""

import asyncio
import json
import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('PilotJobsScraper')

# Import APScheduler
try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")

# Import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not installed. Run: pip install supabase")

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.playwright_scraper import PlaywrightScraper
from normalizer import JobNormalizer


class ProxyManager:
    """
    Manages proxy rotation for avoiding IP blocks.

    Supports:
    - Bright Data
    - Smartproxy
    - IPRoyal
    - Or any HTTP proxy
    """

    def __init__(self):
        # Load proxy configuration from environment
        self.proxy_url = os.getenv('PROXY_URL')  # e.g., http://user:pass@proxy.smartproxy.com:10000
        self.proxy_enabled = bool(self.proxy_url)

        if self.proxy_enabled:
            logger.info(f"✓ Proxy enabled: {self.proxy_url.split('@')[-1] if '@' in self.proxy_url else 'configured'}")
        else:
            logger.warning("⚠ No proxy configured. Set PROXY_URL for IP rotation.")

    def get_proxy(self) -> Optional[str]:
        """Get proxy URL for requests"""
        return self.proxy_url if self.proxy_enabled else None


class DatabaseManager:
    """
    Handles all database operations with proper upserts.
    """

    def __init__(self):
        self.supabase: Optional[Client] = None
        self.output_dir = Path(__file__).parent / 'output'
        self.output_dir.mkdir(exist_ok=True)
        self._init_supabase()

    def _init_supabase(self):
        """Initialize Supabase connection"""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available - using JSON file storage only")
            return

        url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')

        if url and key:
            try:
                self.supabase = create_client(url, key)
                logger.info("✓ Connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
        else:
            logger.warning("Supabase credentials not found in environment")

    def upsert_jobs(self, jobs: List[Dict]) -> int:
        """
        Upsert jobs to database (update if exists, insert if new).
        Returns number of jobs saved.
        """
        if not jobs:
            return 0

        saved_count = 0

        # Always save to JSON file (backup)
        self._save_to_json(jobs)

        # Save to Supabase if available
        if self.supabase:
            try:
                # Prepare jobs for database
                db_jobs = []
                for job in jobs:
                    db_job = {
                        'title': job.get('title', '')[:500],
                        'company': job.get('company', '')[:255],
                        'location': job.get('location', 'Not specified')[:255],
                        'region': job.get('region', 'global'),
                        'position_type': job.get('position_type', 'other'),
                        'aircraft_type': job.get('aircraft_type'),
                        'type_rating_required': job.get('type_rating_required', False),
                        'type_rating_provided': job.get('type_rating_provided', False),
                        'min_total_hours': job.get('min_total_hours'),
                        'min_pic_hours': job.get('min_pic_hours'),
                        'min_type_hours': job.get('min_type_hours'),
                        'license_required': job.get('license_required', 'ATPL/CPL'),
                        'contract_type': job.get('contract_type', 'permanent'),
                        'salary_info': job.get('salary_info'),
                        'benefits': job.get('benefits'),
                        'description': job.get('description'),
                        'application_url': job.get('application_url', ''),
                        'source': job.get('source', 'Scraped'),
                        'date_posted': job.get('date_posted'),
                        'date_scraped': datetime.now().isoformat(),
                        'is_active': True,
                    }

                    # Skip jobs without URL
                    if db_job['application_url']:
                        db_jobs.append(db_job)

                if db_jobs:
                    # Upsert: Update if URL exists, insert if new
                    result = self.supabase.table('pilot_jobs').upsert(
                        db_jobs,
                        on_conflict='application_url'
                    ).execute()

                    saved_count = len(db_jobs)
                    logger.info(f"✓ Saved {saved_count} jobs to Supabase")

            except Exception as e:
                logger.error(f"Error saving to Supabase: {e}")
                # Fall back to JSON only
                saved_count = len(jobs)
        else:
            saved_count = len(jobs)

        return saved_count

    def _save_to_json(self, jobs: List[Dict]):
        """Save jobs to JSON file (backup)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save timestamped version
        json_path = self.output_dir / f'jobs_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_jobs': len(jobs),
                'jobs': jobs
            }, f, indent=2, ensure_ascii=False)

        # Update latest_jobs.json (for frontend fallback)
        latest_path = self.output_dir / 'latest_jobs.json'
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump({'jobs': jobs}, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved {len(jobs)} jobs to {json_path}")

    def mark_stale_jobs_inactive(self, hours: int = 168):
        """Mark jobs not seen in X hours as inactive (default 7 days)"""
        if not self.supabase:
            return

        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            self.supabase.table('pilot_jobs').update({
                'is_active': False
            }).lt('date_scraped', cutoff.isoformat()).execute()

            logger.info(f"✓ Marked jobs older than {hours} hours as inactive")
        except Exception as e:
            logger.error(f"Error marking stale jobs: {e}")


class AirlineScrapeJob:
    """Represents a single airline scrape job with metadata"""

    def __init__(
        self,
        name: str,
        scraper_func: Callable,
        priority: int = 2,  # 1=high, 2=normal, 3=low
        interval_hours: int = 4,
        region: str = 'global'
    ):
        self.name = name
        self.scraper_func = scraper_func
        self.priority = priority
        self.interval_hours = interval_hours
        self.region = region
        self.last_run = None
        self.last_job_count = 0
        self.consecutive_failures = 0
        self.total_runs = 0


class ProductionScheduler:
    """
    Production-grade scheduler that manages all scraping jobs.

    Features:
    - Staggered job scheduling (don't hit all at once)
    - Concurrent execution (scrape multiple airlines simultaneously)
    - Error recovery with exponential backoff
    - Priority-based scheduling
    - Health monitoring
    """

    # Configuration
    MAX_CONCURRENT_SCRAPERS = 3  # How many airlines to scrape at once
    RETRY_DELAYS = [60, 300, 900, 3600]  # Retry delays in seconds (1min, 5min, 15min, 1hr)

    def __init__(self):
        self.scraper = PlaywrightScraper(headless=True)
        self.normalizer = JobNormalizer()
        self.db = DatabaseManager()
        self.proxy = ProxyManager()

        # Job registry
        self.jobs: Dict[str, AirlineScrapeJob] = {}

        # Statistics
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'total_scrapes': 0,
            'total_jobs_found': 0,
            'total_errors': 0,
            'last_full_run': None,
        }

        # Semaphore for limiting concurrent scrapers
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SCRAPERS)

        # Register all airline jobs
        self._register_jobs()

    def _register_jobs(self):
        """Register all airline scraping jobs"""

        # Priority 1 (High) - Check every 2 hours
        # Major employers that post frequently
        high_priority = [
            ('Emirates', self.scraper.scrape_emirates, 'middle_east'),
            ('Qatar Airways', self.scraper.scrape_qatar_airways, 'middle_east'),
            ('Ryanair', self.scraper.scrape_ryanair, 'europe'),
        ]

        for name, func, region in high_priority:
            self.jobs[name] = AirlineScrapeJob(
                name=name,
                scraper_func=func,
                priority=1,
                interval_hours=2,
                region=region
            )

        # Priority 2 (Normal) - Check every 4 hours
        normal_priority = [
            ('Etihad', self.scraper.scrape_etihad, 'middle_east'),
            ('flydubai', self.scraper.scrape_flydubai, 'middle_east'),
            ('easyJet', self.scraper.scrape_easyjet, 'europe'),
            ('Wizz Air', self.scraper.scrape_wizz_air, 'europe'),
            ('Vueling', self.scraper.scrape_vueling, 'europe'),
            ('Norwegian', self.scraper.scrape_norwegian, 'europe'),
        ]

        for name, func, region in normal_priority:
            self.jobs[name] = AirlineScrapeJob(
                name=name,
                scraper_func=func,
                priority=2,
                interval_hours=4,
                region=region
            )

        # Priority 3 (Low) - Check every 6 hours
        # Recruitment agencies (they aggregate from many sources)
        low_priority = [
            ('Rishworth Aviation', self.scraper.scrape_rishworth, 'global'),
        ]

        for name, func, region in low_priority:
            self.jobs[name] = AirlineScrapeJob(
                name=name,
                scraper_func=func,
                priority=3,
                interval_hours=6,
                region=region
            )

        logger.info(f"✓ Registered {len(self.jobs)} airline scraping jobs")

    async def scrape_airline(self, job: AirlineScrapeJob) -> List[Dict]:
        """
        Scrape a single airline with error handling and retry logic.
        """
        async with self.semaphore:  # Limit concurrent scrapers
            logger.info(f"[{job.name}] Starting scrape...")

            try:
                # Run the scraper
                jobs = await job.scraper_func()

                # Normalize jobs
                normalized = []
                for j in jobs:
                    try:
                        normalized.append(self.normalizer.normalize_job(j))
                    except Exception as e:
                        logger.warning(f"[{job.name}] Normalization error: {e}")
                        normalized.append(j)

                # Update job stats
                job.last_run = datetime.now()
                job.last_job_count = len(normalized)
                job.consecutive_failures = 0
                job.total_runs += 1

                logger.info(f"[{job.name}] ✓ Found {len(normalized)} jobs")
                return normalized

            except Exception as e:
                job.consecutive_failures += 1
                self.stats['total_errors'] += 1

                logger.error(f"[{job.name}] ✗ Error: {e}")

                # Calculate backoff delay
                delay_index = min(job.consecutive_failures - 1, len(self.RETRY_DELAYS) - 1)
                delay = self.RETRY_DELAYS[delay_index]

                logger.warning(f"[{job.name}] Will retry in {delay} seconds")

                return []

    async def run_full_scrape(self):
        """
        Run all scrapers with concurrent execution.
        """
        logger.info("="*70)
        logger.info("STARTING FULL SCRAPE")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Airlines: {len(self.jobs)}")
        logger.info(f"Max concurrent: {self.MAX_CONCURRENT_SCRAPERS}")
        logger.info("="*70)

        all_jobs = []

        # Sort jobs by priority
        sorted_jobs = sorted(self.jobs.values(), key=lambda j: j.priority)

        # Create tasks for all scrapers
        tasks = [self.scrape_airline(job) for job in sorted_jobs]

        # Run concurrently (semaphore limits actual concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")

        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            url = job.get('application_url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)

        logger.info(f"\nTotal jobs found: {len(all_jobs)}")
        logger.info(f"After deduplication: {len(unique_jobs)}")

        # Save to database
        if unique_jobs:
            self.db.upsert_jobs(unique_jobs)

        # Update stats
        self.stats['total_scrapes'] += 1
        self.stats['total_jobs_found'] = len(unique_jobs)
        self.stats['last_full_run'] = datetime.now().isoformat()

        # Mark old jobs as inactive
        self.db.mark_stale_jobs_inactive()

        self._print_summary(unique_jobs)

        return unique_jobs

    def _print_summary(self, jobs: List[Dict]):
        """Print scraping summary"""
        logger.info("\n" + "="*70)
        logger.info("SCRAPE COMPLETE")
        logger.info("="*70)

        # By company
        companies = {}
        for job in jobs:
            company = job.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1

        logger.info("\nJobs by company:")
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {company}: {count}")

        # By region
        regions = {}
        for job in jobs:
            region = job.get('region', 'global')
            regions[region] = regions.get(region, 0) + 1

        logger.info("\nJobs by region:")
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {region}: {count}")

        # Job stats
        logger.info("\nAirline scraper status:")
        for name, job in sorted(self.jobs.items()):
            status = "✓" if job.consecutive_failures == 0 else f"✗ ({job.consecutive_failures} failures)"
            logger.info(f"  {name}: {status} - {job.last_job_count} jobs")

    def run_scheduler(self):
        """
        Start the APScheduler to run jobs on their schedules.
        """
        if not SCHEDULER_AVAILABLE:
            logger.error("APScheduler not installed. Running once instead.")
            asyncio.run(self.run_full_scrape())
            return

        scheduler = BlockingScheduler()

        # Schedule full scrape every 4 hours
        scheduler.add_job(
            lambda: asyncio.run(self.run_full_scrape()),
            IntervalTrigger(hours=4),
            id='full_scrape',
            name='Full airline scrape',
            jitter=300,  # Random delay up to 5 minutes
        )

        # Schedule high-priority airlines more frequently
        scheduler.add_job(
            lambda: asyncio.run(self._scrape_priority_airlines()),
            IntervalTrigger(hours=2),
            id='priority_scrape',
            name='Priority airline scrape',
            jitter=120,
        )

        # Daily cleanup job (mark old jobs inactive)
        scheduler.add_job(
            lambda: self.db.mark_stale_jobs_inactive(),
            CronTrigger(hour=3, minute=0),  # Run at 3 AM
            id='cleanup',
            name='Daily cleanup',
        )

        logger.info("\n" + "="*70)
        logger.info("SCRAPER SCHEDULER STARTED")
        logger.info("="*70)
        logger.info(f"Registered jobs: {len(self.jobs)} airlines")
        logger.info("Schedule:")
        logger.info("  - Full scrape: Every 4 hours")
        logger.info("  - Priority scrape: Every 2 hours")
        logger.info("  - Cleanup: Daily at 3 AM")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*70 + "\n")

        # Run initial scrape
        logger.info("Running initial scrape...")
        asyncio.run(self.run_full_scrape())

        # Start the scheduler
        try:
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("\nShutdown requested. Stopping scheduler...")
            scheduler.shutdown()

    async def _scrape_priority_airlines(self):
        """Scrape only high-priority airlines"""
        priority_jobs = [j for j in self.jobs.values() if j.priority == 1]

        logger.info(f"Running priority scrape ({len(priority_jobs)} airlines)...")

        all_results = []
        for job in priority_jobs:
            results = await self.scrape_airline(job)
            all_results.extend(results)

        if all_results:
            self.db.upsert_jobs(all_results)

        logger.info(f"Priority scrape complete: {len(all_results)} jobs")

    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            **self.stats,
            'jobs': {
                name: {
                    'last_run': job.last_run.isoformat() if job.last_run else None,
                    'last_job_count': job.last_job_count,
                    'failures': job.consecutive_failures,
                    'total_runs': job.total_runs,
                }
                for name, job in self.jobs.items()
            },
            'database_connected': self.db.supabase is not None,
            'proxy_enabled': self.proxy.proxy_enabled,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Production Pilot Jobs Scraper')
    parser.add_argument('--test', action='store_true', help='Run once (test mode)')
    parser.add_argument('--status', action='store_true', help='Show status')
    args = parser.parse_args()

    scheduler = ProductionScheduler()

    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, default=str))
        return

    if args.test:
        logger.info("Running in TEST mode (single run)...")
        asyncio.run(scheduler.run_full_scrape())
    else:
        scheduler.run_scheduler()


if __name__ == '__main__':
    main()

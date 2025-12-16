"""
Smart Queue - Round Robin Scheduler for Universal Scraper
==========================================================
This script runs continuously, picking airlines that are "due" for scraping
based on their tier and last_checked timestamp.

How it works:
1. Query DB: "Give me airlines that haven't been checked in X hours"
2. Process batch of 5 airlines
3. Update their last_checked timestamp
4. Sleep and repeat

Tier System:
- Tier 1 (Emirates, Delta): Check every 2-3 hours
- Tier 2 (Medium airlines): Check every 12 hours
- Tier 3 (Small/Regional): Check every 24 hours

Usage:
    python smart_queue.py                    # Run continuous queue
    python smart_queue.py --once             # Run one batch and exit
    python smart_queue.py --tier 1           # Only process Tier 1 airlines
    python smart_queue.py --batch-size 10    # Process 10 airlines per batch
"""

import os
import sys
import time
import signal
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from dotenv import load_dotenv
from supabase import create_client, Client

# Import the universal engine
from universal_engine import UniversalEngine, detect_ats_type, MasterScrapers, JobNormalizer

# Load environment variables from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# --- CONFIGURATION ---
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Queue settings
DEFAULT_BATCH_SIZE = 5
SLEEP_BETWEEN_AIRLINES = 10  # seconds
SLEEP_WHEN_EMPTY = 300  # 5 minutes when no airlines due
MAX_RETRIES_PER_AIRLINE = 3

# Tier frequency settings (in hours)
TIER_FREQUENCIES = {
    1: 3,   # Tier 1: Check every 3 hours
    2: 12,  # Tier 2: Check every 12 hours
    3: 24,  # Tier 3: Check every 24 hours
}

# Logging setup - determine log directory based on where script is run from
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'smart_queue.log'), mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Graceful shutdown handling
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown signal received, finishing current batch...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# =============================================================================
# QUEUE DATABASE OPERATIONS
# =============================================================================

class QueueDB:
    """Database operations for the smart queue"""

    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials required for queue operation")
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_due_airlines(self, batch_size: int = 5, tier: int = None) -> List[Dict]:
        """
        Get airlines that are due for scraping.
        Uses each airline's tier to determine frequency.
        """
        now = datetime.utcnow()

        # Build query for each tier
        all_due = []

        tiers_to_check = [tier] if tier else [1, 2, 3]

        for t in tiers_to_check:
            frequency_hours = TIER_FREQUENCIES.get(t, 24)
            cutoff = (now - timedelta(hours=frequency_hours)).isoformat()

            try:
                # Query airlines that are due: last_checked is NULL OR last_checked < cutoff
                response = self.client.table("airlines_to_scrape")\
                    .select("*")\
                    .eq("status", "active")\
                    .eq("tier", t)\
                    .or_(f"last_checked.is.null,last_checked.lt.{cutoff}")\
                    .order("last_checked", nullsfirst=True)\
                    .limit(batch_size)\
                    .execute()

                if response.data:
                    all_due.extend(response.data)
                    logger.debug(f"Found {len(response.data)} Tier {t} airlines due")

            except Exception as e:
                logger.error(f"Error querying tier {t}: {e}")

        # Sort by last_checked (oldest first, NULLs first) and limit
        all_due.sort(key=lambda x: x.get("last_checked") or "1900-01-01")
        return all_due[:batch_size]

    def get_error_airlines(self, limit: int = 5) -> List[Dict]:
        """Get airlines in error status that might be ready for retry"""
        try:
            response = self.client.table("airlines_to_scrape")\
                .select("*")\
                .eq("status", "error")\
                .lt("consecutive_failures", 10)\
                .order("last_checked")\
                .limit(limit)\
                .execute()

            return response.data or []
        except Exception as e:
            logger.error(f"Error querying error airlines: {e}")
            return []

    def update_airline_after_scrape(self, airline_id: str, jobs_found: int,
                                     success: bool, error: str = None):
        """Update airline status after scraping"""
        now = datetime.utcnow().isoformat()

        update_data = {
            "last_checked": now,
            "jobs_found_last_scrape": jobs_found,
        }

        if success:
            update_data["consecutive_failures"] = 0
            update_data["last_successful_scrape"] = now
            update_data["last_error"] = None
            update_data["status"] = "active"
        else:
            # Increment failures
            current = self.client.table("airlines_to_scrape")\
                .select("consecutive_failures, total_jobs_found")\
                .eq("id", airline_id)\
                .single()\
                .execute()

            failures = (current.data.get("consecutive_failures", 0) if current.data else 0) + 1
            update_data["consecutive_failures"] = failures
            update_data["last_error"] = error[:500] if error else "Unknown error"

            # Set to error status after too many failures
            if failures >= 5:
                update_data["status"] = "error"

        # Update total jobs found
        if jobs_found > 0:
            current = self.client.table("airlines_to_scrape")\
                .select("total_jobs_found")\
                .eq("id", airline_id)\
                .single()\
                .execute()
            total = (current.data.get("total_jobs_found", 0) if current.data else 0) + jobs_found
            update_data["total_jobs_found"] = total

        self.client.table("airlines_to_scrape").update(update_data).eq("id", airline_id).execute()

    def upsert_jobs(self, jobs: List[Dict]) -> int:
        """Upsert jobs to database"""
        if not jobs:
            return 0

        response = self.client.table("pilot_jobs").upsert(
            jobs,
            on_conflict="application_url"
        ).execute()

        return len(response.data) if response.data else 0

    def log_scrape(self, airline_id: str, airline_name: str, ats_type: str,
                   status: str, jobs_found: int, duration: float, error: str = None):
        """Log scrape for analytics"""
        self.client.table("scrape_logs").insert({
            "airline_id": airline_id,
            "airline_name": airline_name,
            "ats_type_detected": ats_type,
            "status": status,
            "jobs_found": jobs_found,
            "duration_seconds": round(duration, 2),
            "error_message": error[:500] if error else None,
            "completed_at": datetime.utcnow().isoformat()
        }).execute()

    def get_queue_stats(self) -> Dict:
        """Get statistics about the queue"""
        stats = {"total": 0, "by_tier": {}, "by_status": {}, "due_count": 0}

        try:
            # Total count
            total = self.client.table("airlines_to_scrape").select("id", count="exact").execute()
            stats["total"] = total.count if total.count else 0

            # Count by tier
            for tier in [1, 2, 3]:
                count = self.client.table("airlines_to_scrape")\
                    .select("id", count="exact")\
                    .eq("tier", tier)\
                    .execute()
                stats["by_tier"][tier] = count.count if count.count else 0

            # Count by status
            for status in ["active", "inactive", "error", "pending_review"]:
                count = self.client.table("airlines_to_scrape")\
                    .select("id", count="exact")\
                    .eq("status", status)\
                    .execute()
                stats["by_status"][status] = count.count if count.count else 0

            # Count due for scraping
            due = self.get_due_airlines(batch_size=100)
            stats["due_count"] = len(due)

        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return stats


# =============================================================================
# SMART QUEUE ENGINE
# =============================================================================

class SmartQueue:
    """The main queue engine that runs continuously"""

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE):
        self.batch_size = batch_size
        self.db = QueueDB(SUPABASE_URL, SUPABASE_KEY)
        self.scrapers = MasterScrapers()
        self.normalizer = JobNormalizer()
        self.browser = None
        self.page = None

    def setup_browser(self):
        """Initialize Playwright browser"""
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        logger.info("Browser initialized")

    def teardown_browser(self):
        """Clean up browser resources"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        logger.info("Browser closed")

    def process_airline(self, airline: Dict) -> tuple:
        """
        Process a single airline.
        Returns: (jobs_found, success, error)
        """
        airline_name = airline["name"]
        url = airline.get("career_page_url", "")
        airline_id = airline["id"]
        airline_region = airline.get("region", "global")

        if not url:
            return 0, False, "No URL configured"

        logger.info(f"Processing: {airline_name}")
        logger.info(f"URL: {url}")

        start_time = time.time()

        # Detect ATS
        ats_type = detect_ats_type(url)
        logger.info(f"Detected ATS: {ats_type}")

        jobs = []
        error = None

        try:
            # Route to correct scraper
            if ats_type == "TALEO":
                jobs = self.scrapers.scrape_taleo(self.page, airline_name, url)
            elif ats_type == "WORKDAY":
                jobs = self.scrapers.scrape_workday(self.page, airline_name, url)
            elif ats_type == "SUCCESSFACTORS":
                jobs = self.scrapers.scrape_successfactors(self.page, airline_name, url)
            else:
                jobs = self.scrapers.scrape_custom_ai(self.page, airline_name, url)

            logger.info(f"Found {len(jobs)} pilot jobs")

        except Exception as e:
            error = str(e)
            logger.error(f"Scraper error: {e}")

        duration = time.time() - start_time

        # Normalize and save jobs
        normalized_jobs = []
        for job in jobs:
            try:
                normalized = self.normalizer.normalize(job, airline_region)
                normalized_jobs.append(normalized)
            except Exception as e:
                logger.debug(f"Normalization error: {e}")

        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in normalized_jobs:
            if job["application_url"] not in seen_urls:
                seen_urls.add(job["application_url"])
                unique_jobs.append(job)

        # Save to database
        saved_count = 0
        if unique_jobs:
            saved_count = self.db.upsert_jobs(unique_jobs)
            logger.info(f"Saved {saved_count} jobs to database")

        # Update airline status
        success = error is None
        self.db.update_airline_after_scrape(airline_id, len(unique_jobs), success, error)

        # Log scrape
        self.db.log_scrape(
            airline_id=airline_id,
            airline_name=airline_name,
            ats_type=ats_type,
            status="success" if success else "failed",
            jobs_found=len(unique_jobs),
            duration=duration,
            error=error
        )

        return len(unique_jobs), success, error

    def process_batch(self, tier: int = None) -> Dict:
        """Process a batch of due airlines"""
        # Get due airlines
        airlines = self.db.get_due_airlines(self.batch_size, tier)

        if not airlines:
            logger.info("No airlines due for scraping")
            return {"processed": 0, "jobs_found": 0, "errors": 0}

        logger.info(f"\n{'='*50}")
        logger.info(f"Processing batch of {len(airlines)} airlines")
        logger.info(f"{'='*50}")

        results = {"processed": 0, "jobs_found": 0, "errors": 0}

        for airline in airlines:
            if shutdown_requested:
                logger.info("Shutdown requested, stopping batch")
                break

            jobs_found, success, error = self.process_airline(airline)

            results["processed"] += 1
            results["jobs_found"] += jobs_found
            if not success:
                results["errors"] += 1

            # Sleep between airlines
            time.sleep(SLEEP_BETWEEN_AIRLINES)

        logger.info(f"\nBatch complete: {results['processed']} processed, "
                   f"{results['jobs_found']} jobs found, {results['errors']} errors")

        return results

    def run_once(self, tier: int = None):
        """Run one batch and exit"""
        try:
            self.setup_browser()
            self.process_batch(tier)
        finally:
            self.teardown_browser()

    def run_continuous(self, tier: int = None):
        """Run continuously in a loop"""
        logger.info("=" * 60)
        logger.info("STARTING SMART QUEUE - CONTINUOUS MODE")
        logger.info("=" * 60)

        # Print initial stats
        stats = self.db.get_queue_stats()
        logger.info(f"Queue stats: {stats['total']} total airlines, "
                   f"{stats['due_count']} due for scraping")
        logger.info(f"By tier: T1={stats['by_tier'].get(1,0)}, "
                   f"T2={stats['by_tier'].get(2,0)}, T3={stats['by_tier'].get(3,0)}")

        try:
            self.setup_browser()

            while not shutdown_requested:
                # Process a batch
                results = self.process_batch(tier)

                if results["processed"] == 0:
                    # No airlines due, sleep longer
                    logger.info(f"Sleeping {SLEEP_WHEN_EMPTY}s (no airlines due)...")
                    time.sleep(SLEEP_WHEN_EMPTY)
                else:
                    # Short sleep between batches
                    logger.info("Sleeping 60s before next batch...")
                    time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.teardown_browser()
            logger.info("Queue stopped")

    def retry_errors(self, limit: int = 5):
        """Retry airlines in error status"""
        logger.info("Retrying airlines in error status...")

        error_airlines = self.db.get_error_airlines(limit)

        if not error_airlines:
            logger.info("No error airlines to retry")
            return

        try:
            self.setup_browser()

            for airline in error_airlines:
                logger.info(f"Retrying: {airline['name']} (failures: {airline['consecutive_failures']})")
                self.process_airline(airline)
                time.sleep(SLEEP_BETWEEN_AIRLINES)

        finally:
            self.teardown_browser()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Smart Queue - Round Robin Scheduler")
    parser.add_argument("--once", action="store_true", help="Run one batch and exit")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Only process specific tier")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="Number of airlines per batch")
    parser.add_argument("--retry-errors", action="store_true", help="Retry airlines in error status")
    parser.add_argument("--stats", action="store_true", help="Print queue statistics and exit")

    args = parser.parse_args()

    queue = SmartQueue(batch_size=args.batch_size)

    if args.stats:
        stats = queue.db.get_queue_stats()
        print("\n=== Queue Statistics ===")
        print(f"Total airlines: {stats['total']}")
        print(f"Due for scraping: {stats['due_count']}")
        print(f"\nBy Tier:")
        for tier, count in stats['by_tier'].items():
            print(f"  Tier {tier}: {count}")
        print(f"\nBy Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
        return

    if args.retry_errors:
        queue.retry_errors()
        return

    if args.once:
        queue.run_once(tier=args.tier)
    else:
        queue.run_continuous(tier=args.tier)


if __name__ == "__main__":
    main()

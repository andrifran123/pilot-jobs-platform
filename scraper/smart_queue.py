"""
Smart Queue - Round Robin Scheduler for Universal Scraper
==========================================================
This script runs continuously, picking airlines that are "due" for scraping
based on their tier and last_checked timestamp.

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
from universal_engine import scrape_airline

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

# Tier frequency settings (in hours)
TIER_FREQUENCIES = {
    1: 3,   # Tier 1: Check every 3 hours
    2: 12,  # Tier 2: Check every 12 hours
    3: 24,  # Tier 3: Check every 24 hours
}

# Logging setup
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
        """Get airlines that are due for scraping."""
        now = datetime.utcnow()
        all_due = []

        tiers_to_check = [tier] if tier else [1, 2, 3]

        for t in tiers_to_check:
            frequency_hours = TIER_FREQUENCIES.get(t, 24)
            cutoff = (now - timedelta(hours=frequency_hours)).isoformat()

            try:
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

            except Exception as e:
                logger.error(f"Error querying tier {t}: {e}")

        all_due.sort(key=lambda x: x.get("last_checked") or "1900-01-01")
        return all_due[:batch_size]

    def get_queue_stats(self) -> Dict:
        """Get statistics about the queue"""
        stats = {"total": 0, "by_tier": {}, "by_status": {}, "due_count": 0}

        try:
            total = self.client.table("airlines_to_scrape").select("id", count="exact").execute()
            stats["total"] = total.count if total.count else 0

            for tier in [1, 2, 3]:
                count = self.client.table("airlines_to_scrape")\
                    .select("id", count="exact")\
                    .eq("tier", tier)\
                    .execute()
                stats["by_tier"][tier] = count.count if count.count else 0

            for status in ["active", "inactive", "error"]:
                count = self.client.table("airlines_to_scrape")\
                    .select("id", count="exact")\
                    .eq("status", status)\
                    .execute()
                stats["by_status"][status] = count.count if count.count else 0

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

    def process_batch(self, tier: int = None) -> Dict:
        """Process a batch of due airlines"""
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

            try:
                # Use the nuclear scrape_airline function
                scrape_airline(airline)
                results["processed"] += 1
            except Exception as e:
                logger.error(f"Error processing {airline['name']}: {e}")
                results["errors"] += 1

            time.sleep(SLEEP_BETWEEN_AIRLINES)

        logger.info(f"\nBatch complete: {results['processed']} processed, {results['errors']} errors")
        return results

    def run_once(self, tier: int = None):
        """Run one batch and exit"""
        self.process_batch(tier)

    def run_continuous(self, tier: int = None):
        """Run continuously in a loop"""
        logger.info("=" * 60)
        logger.info("STARTING SMART QUEUE - CONTINUOUS MODE")
        logger.info("=" * 60)

        stats = self.db.get_queue_stats()
        logger.info(f"Queue stats: {stats['total']} total airlines, {stats['due_count']} due for scraping")

        while not shutdown_requested:
            results = self.process_batch(tier)

            if results["processed"] == 0:
                logger.info(f"Sleeping {SLEEP_WHEN_EMPTY}s (no airlines due)...")
                time.sleep(SLEEP_WHEN_EMPTY)
            else:
                logger.info("Sleeping 60s before next batch...")
                time.sleep(60)

        logger.info("Queue stopped")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Smart Queue - Round Robin Scheduler")
    parser.add_argument("--once", action="store_true", help="Run one batch and exit")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Only process specific tier")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Number of airlines per batch")
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

    if args.once:
        queue.run_once(tier=args.tier)
    else:
        queue.run_continuous(tier=args.tier)


if __name__ == "__main__":
    main()

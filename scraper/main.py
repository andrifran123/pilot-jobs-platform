#!/usr/bin/env python3
"""
Pilot Jobs Platform - Universal Scraper System
===============================================
Main entry point for all scraper operations.

Commands:
    python main.py scrape              # Run universal scraper for all due airlines
    python main.py scrape --airline X  # Scrape single airline
    python main.py queue               # Start continuous queue processor
    python main.py hunt                # Discover new airlines
    python main.py stats               # Show system statistics
    python main.py setup               # Initial setup (install playwright, etc.)

Examples:
    python main.py scrape --test                    # Dry run
    python main.py queue --tier 1                   # Only process Tier 1 airlines
    python main.py hunt --search "Delta" "United"   # Find specific airlines
    python main.py stats                            # View queue statistics
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment from project root (.env file is in parent directory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_scrape(args):
    """Run the universal scraper"""
    from universal_engine import UniversalEngine

    engine = UniversalEngine(test_mode=args.test)
    engine.run(single_airline=args.airline, use_ai=args.ai)


def cmd_scrape_deep(args):
    """Run the AI-powered deep scraper"""
    from ai_scraper import AIDeepScraper

    scraper = AIDeepScraper()
    scraper.run(airline_name=args.airline, limit=args.limit)


def cmd_queue(args):
    """Run the smart queue processor"""
    from smart_queue import SmartQueue

    queue = SmartQueue(batch_size=args.batch_size)

    if args.once:
        queue.run_once(tier=args.tier)
    else:
        queue.run_continuous(tier=args.tier)


def cmd_hunt(args):
    """Run the airline hunter"""
    from airline_hunter import AirlineHunter

    hunter = AirlineHunter(test_mode=args.test)

    if args.search:
        results = hunter.hunt_specific(args.search)
        print(f"\nFound {len(results)} airlines:")
        for r in results:
            print(f"  {r['name']}: {r['career_page_url']} ({r['ats_type']})")
    else:
        hunter.run_full_hunt(limit=args.limit)


def cmd_stats(args):
    """Show system statistics"""
    from smart_queue import QueueDB
    from supabase import create_client

    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase credentials not configured")
        return

    db = QueueDB(SUPABASE_URL, SUPABASE_KEY)
    stats = db.get_queue_stats()

    print("\n" + "=" * 50)
    print("  PILOT JOBS PLATFORM - SCRAPER STATISTICS")
    print("=" * 50)
    print(f"\n  Total Airlines in Database: {stats['total']}")
    print(f"  Airlines Due for Scraping: {stats['due_count']}")

    print("\n  By Tier:")
    print(f"    Tier 1 (Major):    {stats['by_tier'].get(1, 0)}")
    print(f"    Tier 2 (Medium):   {stats['by_tier'].get(2, 0)}")
    print(f"    Tier 3 (Regional): {stats['by_tier'].get(3, 0)}")

    print("\n  By Status:")
    for status, count in stats['by_status'].items():
        print(f"    {status}: {count}")

    # Get recent scrape logs
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logs = client.table("scrape_logs")\
            .select("*")\
            .order("started_at", desc=True)\
            .limit(10)\
            .execute()

        if logs.data:
            print("\n  Recent Scrapes:")
            for log in logs.data:
                status_icon = "✓" if log["status"] == "success" else "✗"
                print(f"    {status_icon} {log['airline_name']}: {log['jobs_found']} jobs "
                      f"({log['duration_seconds']}s)")

        # Get job count
        jobs = client.table("pilot_jobs").select("id", count="exact").execute()
        print(f"\n  Total Jobs in Database: {jobs.count if jobs.count else 0}")

    except Exception as e:
        logger.debug(f"Could not fetch additional stats: {e}")

    print("\n" + "=" * 50 + "\n")


def cmd_setup(args):
    """Initial setup - install dependencies"""
    print("Setting up the Universal Scraper System...")

    # Install playwright browsers
    print("\n1. Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

    # Create directories
    print("\n2. Creating directories...")
    os.makedirs("scraper/logs", exist_ok=True)
    os.makedirs("scraper/output", exist_ok=True)

    # Check environment
    print("\n3. Checking environment...")
    required_vars = ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        print(f"   Warning: Missing environment variables: {missing}")
        print("   Add these to your .env file")
    else:
        print("   ✓ All required environment variables set")

    print("\n4. Testing Supabase connection...")
    try:
        from supabase import create_client
        client = create_client(
            os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
        # Test query
        client.table("airlines_to_scrape").select("id").limit(1).execute()
        print("   ✓ Supabase connection successful")
    except Exception as e:
        print(f"   ✗ Supabase connection failed: {e}")
        print("   Make sure to run the SQL schema in your Supabase dashboard")

    print("\n✓ Setup complete!")
    print("\nNext steps:")
    print("  1. Run the SQL schema in Supabase (supabase-schema.sql)")
    print("  2. Test with: python main.py scrape --test")
    print("  3. Start the queue: python main.py queue")


def cmd_validate(args):
    """Validate job URLs and deactivate broken ones"""
    print("Validating job URLs...")

    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    from supabase import create_client
    import requests

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get active jobs
    jobs = client.table("pilot_jobs")\
        .select("id, application_url, company")\
        .eq("is_active", True)\
        .limit(args.limit or 100)\
        .execute()

    if not jobs.data:
        print("No jobs to validate")
        return

    print(f"Validating {len(jobs.data)} jobs...")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    valid = 0
    invalid = 0

    for job in jobs.data:
        try:
            response = session.head(job["application_url"], timeout=10, allow_redirects=True)
            if response.status_code < 400:
                valid += 1
            else:
                invalid += 1
                if not args.dry_run:
                    client.table("pilot_jobs").update({"is_active": False}).eq("id", job["id"]).execute()
                print(f"  ✗ {job['company']}: {response.status_code}")
        except Exception as e:
            invalid += 1
            if not args.dry_run:
                client.table("pilot_jobs").update({"is_active": False}).eq("id", job["id"]).execute()
            print(f"  ✗ {job['company']}: {str(e)[:50]}")

    print(f"\nResults: {valid} valid, {invalid} invalid")
    if args.dry_run:
        print("(Dry run - no changes made)")


def main():
    parser = argparse.ArgumentParser(
        description="Pilot Jobs Platform - Universal Scraper System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scrape                    Run scraper for all due airlines
  python main.py scrape --airline Emirates Scrape single airline
  python main.py scrape --test             Dry run (no DB writes)
  python main.py queue                     Start continuous queue processor
  python main.py queue --tier 1            Only process Tier 1 airlines
  python main.py hunt                      Discover new airlines
  python main.py hunt --search Delta       Find specific airline
  python main.py stats                     Show system statistics
  python main.py setup                     Initial setup
  python main.py validate                  Validate job URLs
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Run universal scraper")
    scrape_parser.add_argument("--airline", type=str, help="Scrape single airline")
    scrape_parser.add_argument("--test", action="store_true", help="Test mode (no DB writes)")
    scrape_parser.add_argument("--ai", action="store_true", help="Use AI for deep job parsing (requires ANTHROPIC_API_KEY)")

    # Deep scrape with AI command
    deep_parser = subparsers.add_parser("deep", help="AI-powered deep scrape (follows job links)")
    deep_parser.add_argument("--airline", type=str, help="Scrape single airline")
    deep_parser.add_argument("--limit", type=int, default=10, help="Max jobs to analyze per airline")

    # Queue command
    queue_parser = subparsers.add_parser("queue", help="Run smart queue processor")
    queue_parser.add_argument("--once", action="store_true", help="Run one batch and exit")
    queue_parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Only process specific tier")
    queue_parser.add_argument("--batch-size", type=int, default=5, help="Airlines per batch")

    # Hunt command
    hunt_parser = subparsers.add_parser("hunt", help="Discover new airlines")
    hunt_parser.add_argument("--search", type=str, nargs="+", help="Search specific airlines")
    hunt_parser.add_argument("--limit", type=int, help="Limit airlines to process")
    hunt_parser.add_argument("--test", action="store_true", help="Test mode (no DB writes)")

    # Stats command
    subparsers.add_parser("stats", help="Show system statistics")

    # Setup command
    subparsers.add_parser("setup", help="Initial setup")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate job URLs")
    validate_parser.add_argument("--limit", type=int, default=100, help="Max jobs to validate")
    validate_parser.add_argument("--dry-run", action="store_true", help="Don't update database")

    args = parser.parse_args()

    if args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "deep":
        cmd_scrape_deep(args)
    elif args.command == "queue":
        cmd_queue(args)
    elif args.command == "hunt":
        cmd_hunt(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "validate":
        cmd_validate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

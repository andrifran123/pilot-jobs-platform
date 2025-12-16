#!/usr/bin/env python3
"""
Cleanup Invalid Jobs Script
============================
Uses AI to re-evaluate existing jobs in the database and removes
non-job entries (FAQs, login pages, "Life at Emirates" pages, etc.)

Usage:
    python cleanup_invalid_jobs.py              # Dry run (preview what would be deleted)
    python cleanup_invalid_jobs.py --execute    # Actually delete the invalid jobs
    python cleanup_invalid_jobs.py --limit 50   # Process only 50 jobs
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client

# Import AI parser
try:
    from ai_parser import parse_job_with_ai, client as ai_client
    AI_AVAILABLE = ai_client is not None
except ImportError:
    AI_AVAILABLE = False
    parse_job_with_ai = None

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_jobs(supabase: Client, limit: int = None) -> List[Dict]:
    """Fetch all jobs from the database"""
    query = supabase.table("pilot_jobs").select("*").eq("is_active", True)

    if limit:
        query = query.limit(limit)

    response = query.execute()
    return response.data or []


def analyze_job_with_ai(job: Dict) -> Dict[str, Any]:
    """
    Re-analyze a job using AI to determine if it's a real job posting.
    Returns dict with is_valid_job boolean and reason.
    """
    if not AI_AVAILABLE or not parse_job_with_ai:
        return {"is_valid_job": True, "reason": "AI unavailable - skipping"}

    # Build text for AI to analyze
    raw_text = f"""
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description: {job.get('description', '') or 'No description'}
"""

    try:
        ai_result = parse_job_with_ai(
            raw_text=raw_text,
            url=job.get('application_url', ''),
            company_name=job.get('company', '')
        )

        return {
            "is_valid_job": ai_result.get("is_valid_job", True),
            "ai_title": ai_result.get("job_title", ""),
        }

    except Exception as e:
        logger.error(f"AI analysis failed for job {job.get('id')}: {e}")
        return {"is_valid_job": True, "reason": f"AI error: {e}"}


def delete_jobs(supabase: Client, job_ids: List[str]) -> int:
    """Delete jobs by their IDs. Returns count of deleted jobs."""
    if not job_ids:
        return 0

    # Delete in batches of 100
    deleted = 0
    batch_size = 100

    for i in range(0, len(job_ids), batch_size):
        batch = job_ids[i:i + batch_size]
        try:
            response = supabase.table("pilot_jobs").delete().in_("id", batch).execute()
            deleted += len(batch)
        except Exception as e:
            logger.error(f"Error deleting batch: {e}")

    return deleted


def main():
    parser = argparse.ArgumentParser(description="Cleanup invalid jobs from database")
    parser.add_argument("--execute", action="store_true", help="Actually delete invalid jobs (default is dry run)")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to process")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY in environment")
        sys.exit(1)

    if not AI_AVAILABLE:
        logger.error("AI parser not available. Set ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    logger.info("=" * 60)
    logger.info("CLEANUP INVALID JOBS SCRIPT")
    logger.info(f"Mode: {'EXECUTE (will delete)' if args.execute else 'DRY RUN (preview only)'}")
    logger.info("=" * 60)

    # Fetch jobs
    logger.info("Fetching jobs from database...")
    jobs = get_all_jobs(supabase, limit=args.limit)
    logger.info(f"Found {len(jobs)} jobs to analyze")

    # Analyze each job
    invalid_jobs = []
    valid_jobs = []

    for i, job in enumerate(jobs, 1):
        job_id = job.get("id")
        title = job.get("title", "")[:50]
        company = job.get("company", "")

        if args.verbose:
            logger.info(f"[{i}/{len(jobs)}] Analyzing: {title}...")

        result = analyze_job_with_ai(job)

        if not result.get("is_valid_job", True):
            invalid_jobs.append({
                "id": job_id,
                "title": job.get("title"),
                "company": company,
                "url": job.get("application_url"),
                "reason": "Not a valid job posting"
            })
            logger.info(f"   ❌ NOT A JOB: {title} ({company})")
        else:
            valid_jobs.append(job_id)
            if args.verbose:
                logger.info(f"   ✅ Valid job: {title}")

        # Progress update every 10 jobs
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(jobs)} analyzed, {len(invalid_jobs)} invalid found")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total jobs analyzed: {len(jobs)}")
    logger.info(f"Valid jobs: {len(valid_jobs)}")
    logger.info(f"Invalid jobs (to delete): {len(invalid_jobs)}")

    if invalid_jobs:
        logger.info("\nInvalid jobs found:")
        for ij in invalid_jobs[:20]:  # Show first 20
            logger.info(f"  - {ij['title'][:60]} ({ij['company']})")
        if len(invalid_jobs) > 20:
            logger.info(f"  ... and {len(invalid_jobs) - 20} more")

        # Save report
        report_file = f"scraper/output/cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_analyzed": len(jobs),
                "valid_count": len(valid_jobs),
                "invalid_count": len(invalid_jobs),
                "invalid_jobs": invalid_jobs
            }, f, indent=2)
        logger.info(f"\nReport saved to: {report_file}")

        # Execute deletion if flag set
        if args.execute:
            logger.info("\nExecuting deletion...")
            job_ids_to_delete = [ij["id"] for ij in invalid_jobs]
            deleted_count = delete_jobs(supabase, job_ids_to_delete)
            logger.info(f"✅ Deleted {deleted_count} invalid jobs from database")
        else:
            logger.info("\n⚠️  DRY RUN - No jobs were deleted")
            logger.info("Run with --execute to actually delete these jobs")
    else:
        logger.info("\n✅ No invalid jobs found! Database is clean.")


if __name__ == "__main__":
    main()

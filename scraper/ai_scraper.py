#!/usr/bin/env python3
"""
AI-Powered Deep Scraper
=======================
This scraper:
1. Visits airline career pages
2. Finds job listing links
3. Follows each link to the full job description
4. Sends the full text to Claude AI for intelligent parsing
5. Saves structured data to Supabase

This is more thorough but slower/costlier than the basic scraper.
Best for getting detailed job requirements (hours, aircraft, visa, etc.)
"""

import os
import sys
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

from ai_parser import parse_job_with_ai, client as ai_client

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase setup
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Pilot job keywords
PILOT_KEYWORDS = [
    "pilot", "captain", "first officer", "f/o", "fo ", "co-pilot",
    "second officer", "cruise pilot", "cadet", "flight instructor",
    "type rating", "a320", "a330", "a350", "a380",
    "b737", "b747", "b777", "b787", "boeing", "airbus",
    "cockpit", "flight deck", "atpl", "cpl", "command"
]


class AIDeepScraper:
    """AI-powered deep scraper that follows job links and parses with Claude"""

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured")

        self.db = create_client(SUPABASE_URL, SUPABASE_KEY)

        if not ai_client:
            logger.warning("ANTHROPIC_API_KEY not set - AI parsing will use fallback")

    def get_airlines(self, airline_name: str = None) -> List[Dict]:
        """Get airlines from database"""
        query = self.db.table("airlines_to_scrape").select("*").eq("status", "active")

        if airline_name:
            query = query.ilike("name", airline_name)

        response = query.execute()
        return response.data or []

    def find_job_links(self, page: Page, airline_name: str, base_url: str) -> List[Dict]:
        """Find all pilot job links on a career page"""
        job_links = []
        seen_urls = set()

        try:
            # Get all links on the page
            links = page.query_selector_all("a[href]")
            logger.info(f"   Scanning {len(links)} links for pilot jobs...")

            for link in links:
                try:
                    text = link.inner_text().strip().lower()
                    href = link.get_attribute("href") or ""

                    if not href or href.startswith("#") or href.startswith("javascript"):
                        continue

                    # Build full URL
                    if href.startswith("/"):
                        href = base_url.rstrip("/") + href
                    elif not href.startswith("http"):
                        href = base_url.rstrip("/") + "/" + href.lstrip("/")

                    # Skip already seen
                    if href in seen_urls:
                        continue

                    # Check if it's a pilot job
                    is_pilot_job = any(kw in text for kw in PILOT_KEYWORDS)
                    is_pilot_url = any(kw in href.lower() for kw in ["pilot", "captain", "flight", "cockpit"])

                    if is_pilot_job or is_pilot_url:
                        seen_urls.add(href)
                        job_links.append({
                            "url": href,
                            "title_guess": text[:100],
                            "airline": airline_name
                        })

                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"Error finding job links: {e}")

        return job_links

    def scrape_job_detail(self, page: Page, job_url: str, airline_name: str) -> Optional[Dict]:
        """Visit a job page and extract details using AI"""
        try:
            logger.info(f"      Reading job page...")
            page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(1)  # Let dynamic content load

            # Get the full page text
            raw_text = page.locator("body").inner_text()

            if len(raw_text) < 100:
                logger.warning(f"      Page too short ({len(raw_text)} chars), skipping")
                return None

            # Parse with AI
            ai_data = parse_job_with_ai(raw_text, job_url, airline_name)

            return {
                "url": job_url,
                "airline": airline_name,
                "raw_length": len(raw_text),
                "ai_parsed": ai_data
            }

        except Exception as e:
            logger.error(f"      Error scraping job detail: {e}")
            return None

    def save_job(self, job_data: Dict, airline_region: str = "global") -> bool:
        """Save parsed job to database"""
        try:
            ai = job_data.get("ai_parsed", {})

            # Map AI output to database schema
            record = {
                "title": ai.get("job_title", "Pilot Position"),
                "company": job_data.get("airline", "Unknown"),
                "location": ai.get("location", "Not specified"),
                "region": self._detect_region(ai.get("location", ""), airline_region),
                "position_type": ai.get("position_type", "other"),
                "aircraft_type": ", ".join(ai.get("aircraft", [])) if ai.get("aircraft") else None,
                "type_rating_required": ai.get("type_rating_required", False),
                "type_rating_provided": ai.get("type_rating_provided", False),
                "min_total_hours": ai.get("min_hours"),
                "min_pic_hours": ai.get("min_pic_hours"),
                "license_required": "ATPL/CPL",
                "visa_sponsorship": ai.get("visa_sponsored", False),
                "is_entry_level": ai.get("is_entry_level", False),
                "contract_type": ai.get("contract_type", "permanent"),
                "description": ai.get("description_summary", ""),
                "application_url": job_data.get("url", ""),
                "source": f"AI Deep Scrape - {job_data.get('airline', '')}",
                "is_active": True
            }

            # Upsert (update if URL exists)
            self.db.table("pilot_jobs").upsert(
                record,
                on_conflict="application_url"
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error saving job: {e}")
            return False

    def _detect_region(self, location: str, default: str) -> str:
        """Detect region from location string"""
        if not location:
            return default

        location_lower = location.lower()

        region_keywords = {
            "middle_east": ["dubai", "uae", "qatar", "doha", "saudi", "bahrain", "oman", "kuwait", "abu dhabi"],
            "europe": ["uk", "london", "ireland", "dublin", "germany", "france", "spain", "italy", "netherlands"],
            "asia": ["singapore", "hong kong", "japan", "tokyo", "korea", "seoul", "china", "thailand", "malaysia"],
            "north_america": ["usa", "united states", "america", "canada", "new york", "los angeles"],
            "oceania": ["australia", "sydney", "melbourne", "new zealand"],
            "africa": ["south africa", "kenya", "ethiopia", "egypt", "morocco"],
            "south_america": ["brazil", "chile", "argentina", "colombia"]
        }

        for region, keywords in region_keywords.items():
            if any(kw in location_lower for kw in keywords):
                return region

        return default

    def run(self, airline_name: str = None, limit: int = 10):
        """Run the AI deep scraper"""
        logger.info("=" * 60)
        logger.info("AI DEEP SCRAPER - Starting")
        logger.info("=" * 60)

        if not ai_client:
            logger.error("ANTHROPIC_API_KEY not set! Add it to .env file")
            logger.info("Get a key at: https://console.anthropic.com/")
            return

        # Get airlines
        airlines = self.get_airlines(airline_name)

        if not airlines:
            logger.warning("No airlines found!")
            return

        logger.info(f"Found {len(airlines)} airlines to deep scrape")

        total_jobs_found = 0
        total_jobs_saved = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            for airline in airlines:
                name = airline["name"]
                url = airline.get("career_page_url", "")
                region = airline.get("region", "global")

                if not url:
                    logger.warning(f"No URL for {name}, skipping")
                    continue

                logger.info(f"\n{'='*50}")
                logger.info(f"Processing: {name}")
                logger.info(f"URL: {url}")

                try:
                    # Visit career page
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(2)

                    # Get base URL for relative links
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"

                    # Find job links
                    job_links = self.find_job_links(page, name, base_url)
                    logger.info(f"   Found {len(job_links)} potential pilot job links")

                    # Process each job (up to limit)
                    jobs_processed = 0
                    for job in job_links[:limit]:
                        logger.info(f"   [{jobs_processed+1}/{min(len(job_links), limit)}] {job['title_guess'][:50]}...")

                        # Scrape job detail page with AI
                        job_data = self.scrape_job_detail(page, job["url"], name)

                        if job_data:
                            total_jobs_found += 1
                            ai = job_data.get("ai_parsed", {})

                            # Log what AI extracted
                            logger.info(f"      AI: {ai.get('job_title', 'N/A')} | "
                                       f"{ai.get('min_hours', 'N/A')}hrs | "
                                       f"{ai.get('aircraft', [])}")

                            # Save to database
                            if self.save_job(job_data, region):
                                total_jobs_saved += 1
                                logger.info(f"      Saved to database")

                        jobs_processed += 1
                        time.sleep(1)  # Rate limit

                    # Update airline last_checked
                    self.db.table("airlines_to_scrape").update({
                        "last_checked": datetime.utcnow().isoformat()
                    }).eq("id", airline["id"]).execute()

                except Exception as e:
                    logger.error(f"Error processing {name}: {e}")

            browser.close()

        logger.info(f"\n{'='*60}")
        logger.info(f"AI DEEP SCRAPER - Complete")
        logger.info(f"Jobs Found: {total_jobs_found}")
        logger.info(f"Jobs Saved: {total_jobs_saved}")
        logger.info(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Deep Scraper")
    parser.add_argument("--airline", type=str, help="Scrape single airline")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs per airline")

    args = parser.parse_args()

    scraper = AIDeepScraper()
    scraper.run(airline_name=args.airline, limit=args.limit)

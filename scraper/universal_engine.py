"""
Universal ATS Router & Scraper Engine
=====================================
The brain of the pilot jobs platform. This script:
1. Fetches airlines from the database
2. Auto-detects the ATS (Applicant Tracking System) each airline uses
3. Routes to the correct "Master Scraper" for that ATS
4. Normalizes and saves jobs to Supabase

Usage:
    python universal_engine.py                    # Run full scrape
    python universal_engine.py --airline Emirates # Test single airline
    python universal_engine.py --test             # Dry run (no DB writes)
"""

import os
import re
import time
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, Browser
from dotenv import load_dotenv
from supabase import create_client, Client

# Import AI parser - ALWAYS use AI for job parsing
try:
    from ai_parser import parse_job_with_ai, client as ai_client
    AI_AVAILABLE = ai_client is not None
except ImportError:
    AI_AVAILABLE = False
    parse_job_with_ai = None

# Load environment variables from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# --- CONFIGURATION ---
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper/logs/universal_engine.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Ensure log directory exists
os.makedirs('scraper/logs', exist_ok=True)
os.makedirs('scraper/output', exist_ok=True)

# --- PILOT JOB KEYWORDS ---
PILOT_KEYWORDS = [
    "pilot", "captain", "first officer", "f/o", "fo ", "co-pilot",
    "flight crew", "flight operations", "flight deck", "cockpit",
    "type rating", "atpl", "cpl", "mpl", "airline pilot",
    "a320", "a330", "a350", "a380", "b737", "b777", "b787", "b747",
    "airbus", "boeing", "embraer", "atr", "crj", "e-jet",
    "cadet", "trainee pilot", "ab initio", "direct entry",
    "line pilot", "training captain", "check pilot", "trf", "tri", "tre"
]

# --- DATA STRUCTURES ---
@dataclass
class ScrapedJob:
    """Standardized job data structure"""
    title: str
    company: str
    location: str = "Not specified"
    region: str = "global"
    position_type: str = "other"
    aircraft_type: Optional[str] = None
    type_rating_required: bool = False
    type_rating_provided: bool = False
    min_total_hours: Optional[int] = None
    min_pic_hours: Optional[int] = None
    license_required: str = "ATPL/CPL"
    visa_sponsorship: bool = False
    is_entry_level: bool = False
    contract_type: str = "permanent"
    description: Optional[str] = None
    application_url: str = ""
    source: str = "Universal Scraper"
    date_posted: Optional[str] = None
    ats_type: str = "UNKNOWN"


# =============================================================================
# 1. THE ATS ROUTER (Detects what system the airline is using)
# =============================================================================

def detect_ats_type(url: str) -> str:
    """
    Analyzes the URL to determine which ATS (Applicant Tracking System)
    the airline is using. This routes to the correct scraper.
    """
    url_lower = url.lower()

    # Taleo (Oracle) - Used by Emirates, Etihad, BA, Air France, etc.
    if any(x in url_lower for x in ["taleo.net", "taleo.com", "oraclecloud.com/hcmUI"]):
        return "TALEO"

    # Workday - Used by Singapore Airlines, Qantas, JetBlue, SWISS, etc.
    if any(x in url_lower for x in ["myworkdayjobs.com", "workday.com", ".wd1.", ".wd3.", ".wd5."]):
        return "WORKDAY"

    # SuccessFactors (SAP) - Used by various European carriers
    if any(x in url_lower for x in ["successfactors.com", "successfactors.eu", "jobs2web.com"]):
        return "SUCCESSFACTORS"

    # Brassring (IBM Kenexa) - Used by some legacy systems
    if "brassring" in url_lower:
        return "BRASSRING"

    # iCIMS - Growing ATS provider
    if "icims.com" in url_lower:
        return "ICIMS"

    # Greenhouse - Popular with tech-forward companies
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "GREENHOUSE"

    # Lever - Another modern ATS
    if "lever.co" in url_lower or "jobs.lever" in url_lower:
        return "LEVER"

    # SmartRecruiters
    if "smartrecruiters.com" in url_lower:
        return "SMARTRECRUITERS"

    # Avature - Used by Delta, etc.
    if "avature.net" in url_lower:
        return "AVATURE"

    # Default to AI-based visual scraping for custom sites
    return "CUSTOM_AI"


# =============================================================================
# 2. MASTER SCRAPERS (Write once, works for dozens of airlines)
# =============================================================================

class MasterScrapers:
    """Collection of universal scrapers for each ATS type"""

    @staticmethod
    def scrape_taleo(page: Page, airline_name: str, url: str) -> List[ScrapedJob]:
        """
        Universal Taleo scraper.
        Works for: Emirates, Etihad, British Airways, Air France, KLM, etc.
        """
        logger.info(f"   Running Universal Taleo Scraper for {airline_name}...")
        jobs_found = []

        try:
            page.goto(url, timeout=60000, wait_until="networkidle")

            # Wait for Taleo job list to load
            try:
                page.wait_for_selector("div.multiline-data-container, table.jobs-list, div.job-row", timeout=15000)
            except:
                logger.warning(f"   Taleo list container not found for {airline_name}")
                # Try clicking search button if needed
                search_btn = page.query_selector("input[type='submit'], button[type='submit']")
                if search_btn:
                    search_btn.click()
                    page.wait_for_load_state("networkidle")

            # Try multiple Taleo selectors (different versions have different HTML)
            selectors = [
                "div.multiline-data-container",
                "tr.job-row",
                "div.requisition",
                "table.jobs-list tbody tr",
                "a[href*='jobdetails']"
            ]

            rows = []
            for selector in selectors:
                rows = page.query_selector_all(selector)
                if rows:
                    break

            base_url = f"https://{urlparse(url).netloc}"

            for row in rows:
                try:
                    # Try to get title and link
                    title_el = row.query_selector("span.titlelink a, a.job-title, a[href*='job']")
                    if not title_el:
                        title_el = row if row.get_attribute("href") else None

                    if title_el:
                        title = title_el.inner_text().strip()
                        link = title_el.get_attribute("href") or ""

                        # Filter for pilot jobs
                        if not any(kw in title.lower() for kw in PILOT_KEYWORDS):
                            continue

                        # Build full URL
                        if link.startswith("/"):
                            link = base_url + link
                        elif not link.startswith("http"):
                            link = base_url + "/" + link

                        # Get location if available
                        location = "Not specified"
                        loc_el = row.query_selector("span.location, div.location, td:nth-child(2)")
                        if loc_el:
                            location = loc_el.inner_text().strip()

                        job = ScrapedJob(
                            title=title,
                            company=airline_name,
                            location=location,
                            application_url=link,
                            ats_type="TALEO",
                            source=f"Direct - {airline_name}"
                        )
                        jobs_found.append(job)

                except Exception as e:
                    logger.debug(f"Error parsing Taleo row: {e}")
                    continue

        except Exception as e:
            logger.error(f"Taleo scraper error for {airline_name}: {e}")

        return jobs_found

    @staticmethod
    def scrape_workday(page: Page, airline_name: str, url: str) -> List[ScrapedJob]:
        """
        Universal Workday scraper.
        Works for: Singapore Airlines, Qantas, JetBlue, SWISS, Cathay Pacific, etc.
        """
        logger.info(f"   Running Universal Workday Scraper for {airline_name}...")
        jobs_found = []

        try:
            page.goto(url, timeout=60000, wait_until="networkidle")

            # Workday pages load slowly with lots of JS
            time.sleep(3)

            # Wait for job list to appear
            try:
                page.wait_for_selector("li[class*='css'], section[data-automation-id='jobResults']", timeout=20000)
            except:
                logger.warning(f"   Workday list not found for {airline_name}")

            # Scroll to load more jobs (Workday uses infinite scroll)
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            base_url = f"https://{urlparse(url).netloc}"

            # Workday uses various selectors depending on version
            job_items = page.query_selector_all("li[class*='css'] a[href*='/job/'], a[data-automation-id='jobTitle']")

            for item in job_items:
                try:
                    title = item.inner_text().strip()
                    link = item.get_attribute("href") or ""

                    # Filter for pilot jobs
                    if not any(kw in title.lower() for kw in PILOT_KEYWORDS):
                        continue

                    # Build full URL
                    if link.startswith("/"):
                        link = base_url + link

                    job = ScrapedJob(
                        title=title,
                        company=airline_name,
                        application_url=link,
                        ats_type="WORKDAY",
                        source=f"Direct - {airline_name}"
                    )
                    jobs_found.append(job)

                except Exception as e:
                    logger.debug(f"Error parsing Workday item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Workday scraper error for {airline_name}: {e}")

        return jobs_found

    @staticmethod
    def scrape_successfactors(page: Page, airline_name: str, url: str) -> List[ScrapedJob]:
        """
        Universal SuccessFactors (SAP) scraper.
        """
        logger.info(f"   Running Universal SuccessFactors Scraper for {airline_name}...")
        jobs_found = []

        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
            time.sleep(2)

            # SuccessFactors selectors
            job_links = page.query_selector_all("a[href*='jobDetail'], a[href*='requisition'], tr.job-row a")
            base_url = f"https://{urlparse(url).netloc}"

            for link_el in job_links:
                try:
                    title = link_el.inner_text().strip()
                    link = link_el.get_attribute("href") or ""

                    if not any(kw in title.lower() for kw in PILOT_KEYWORDS):
                        continue

                    if link.startswith("/"):
                        link = base_url + link

                    job = ScrapedJob(
                        title=title,
                        company=airline_name,
                        application_url=link,
                        ats_type="SUCCESSFACTORS",
                        source=f"Direct - {airline_name}"
                    )
                    jobs_found.append(job)

                except Exception as e:
                    logger.debug(f"Error parsing SuccessFactors item: {e}")
                    continue

        except Exception as e:
            logger.error(f"SuccessFactors scraper error for {airline_name}: {e}")

        return jobs_found

    @staticmethod
    def scrape_custom_ai(page: Page, airline_name: str, url: str) -> List[ScrapedJob]:
        """
        The AI/Visual Fallback scraper for custom websites.
        Uses smart heuristics to find pilot job links on ANY website.
        Works for: Qatar Airways, Ryanair, easyJet, Lufthansa, etc.
        """
        logger.info(f"   Running AI Visual Scraper for {airline_name}...")
        jobs_found = []

        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
            time.sleep(2)

            # Scroll to trigger lazy loading
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)

            base_url = f"https://{urlparse(url).netloc}"

            # Strategy 1: Find ALL links and filter by pilot keywords
            all_links = page.query_selector_all("a[href]")

            seen_urls = set()

            for link in all_links:
                try:
                    text = link.inner_text().strip()
                    href = link.get_attribute("href") or ""

                    # Skip empty or useless links
                    if not text or len(text) < 5 or not href:
                        continue

                    # Skip social/external links
                    if any(x in href.lower() for x in ["linkedin", "facebook", "twitter", "instagram", "youtube"]):
                        continue

                    # Check if it's a pilot job
                    text_lower = text.lower()
                    href_lower = href.lower()

                    is_pilot_job = any(kw in text_lower for kw in PILOT_KEYWORDS)
                    is_pilot_url = any(kw in href_lower for kw in ["pilot", "captain", "flight", "cockpit"])

                    if is_pilot_job or is_pilot_url:
                        # Build full URL
                        if href.startswith("/"):
                            href = base_url + href
                        elif not href.startswith("http"):
                            href = base_url + "/" + href.lstrip("/")

                        # Deduplicate
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)

                        # Clean title
                        title = text.replace("\n", " ").strip()
                        title = re.sub(r'\s+', ' ', title)

                        # Skip if title is too long (probably not a job title)
                        if len(title) > 200:
                            continue

                        job = ScrapedJob(
                            title=title,
                            company=airline_name,
                            application_url=href,
                            ats_type="CUSTOM_AI",
                            source=f"Direct - {airline_name}"
                        )
                        jobs_found.append(job)

                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

            # Strategy 2: Look for job cards/containers with structured data
            job_card_selectors = [
                "div[class*='job']", "article[class*='job']", "li[class*='job']",
                "div[class*='vacancy']", "div[class*='position']", "div[class*='career']",
                "div[class*='opening']", "tr[class*='job']", "div[data-job]"
            ]

            for selector in job_card_selectors:
                cards = page.query_selector_all(selector)
                for card in cards:
                    try:
                        # Try to find title and link within card
                        title_el = card.query_selector("h2, h3, h4, a[class*='title'], span[class*='title']")
                        link_el = card.query_selector("a[href]")

                        if title_el and link_el:
                            title = title_el.inner_text().strip()
                            href = link_el.get_attribute("href") or ""

                            if any(kw in title.lower() for kw in PILOT_KEYWORDS):
                                if href.startswith("/"):
                                    href = base_url + href

                                if href not in seen_urls:
                                    seen_urls.add(href)
                                    job = ScrapedJob(
                                        title=title,
                                        company=airline_name,
                                        application_url=href,
                                        ats_type="CUSTOM_AI",
                                        source=f"Direct - {airline_name}"
                                    )
                                    jobs_found.append(job)

                    except Exception as e:
                        continue

        except Exception as e:
            logger.error(f"AI scraper error for {airline_name}: {e}")

        return jobs_found


# =============================================================================
# 3. JOB NORMALIZER (Standardizes data across all sources)
# =============================================================================

class JobNormalizer:
    """Normalizes scraped job data to match our database schema"""

    # Region mapping based on country/location
    REGION_MAP = {
        # Middle East
        "uae": "middle_east", "dubai": "middle_east", "abu dhabi": "middle_east",
        "qatar": "middle_east", "doha": "middle_east", "saudi": "middle_east",
        "bahrain": "middle_east", "oman": "middle_east", "kuwait": "middle_east",
        # Europe
        "uk": "europe", "london": "europe", "ireland": "europe", "dublin": "europe",
        "germany": "europe", "frankfurt": "europe", "munich": "europe",
        "france": "europe", "paris": "europe", "spain": "europe", "madrid": "europe",
        "italy": "europe", "netherlands": "europe", "amsterdam": "europe",
        "switzerland": "europe", "zurich": "europe", "austria": "europe", "vienna": "europe",
        "belgium": "europe", "brussels": "europe", "portugal": "europe", "lisbon": "europe",
        "poland": "europe", "warsaw": "europe", "hungary": "europe", "budapest": "europe",
        "czech": "europe", "prague": "europe", "norway": "europe", "oslo": "europe",
        "sweden": "europe", "stockholm": "europe", "finland": "europe", "helsinki": "europe",
        "denmark": "europe", "copenhagen": "europe", "greece": "europe", "athens": "europe",
        "turkey": "europe", "istanbul": "europe",
        # Asia
        "singapore": "asia", "hong kong": "asia", "japan": "asia", "tokyo": "asia",
        "korea": "asia", "seoul": "asia", "china": "asia", "beijing": "asia", "shanghai": "asia",
        "taiwan": "asia", "taipei": "asia", "thailand": "asia", "bangkok": "asia",
        "malaysia": "asia", "kuala lumpur": "asia", "indonesia": "asia", "jakarta": "asia",
        "philippines": "asia", "manila": "asia", "vietnam": "asia", "hanoi": "asia",
        "india": "asia", "mumbai": "asia", "delhi": "asia",
        # Oceania
        "australia": "oceania", "sydney": "oceania", "melbourne": "oceania",
        "new zealand": "oceania", "auckland": "oceania",
        # North America
        "usa": "north_america", "united states": "north_america", "america": "north_america",
        "atlanta": "north_america", "new york": "north_america", "los angeles": "north_america",
        "chicago": "north_america", "dallas": "north_america", "denver": "north_america",
        "canada": "north_america", "toronto": "north_america", "vancouver": "north_america",
        # South America
        "brazil": "south_america", "sao paulo": "south_america",
        "argentina": "south_america", "buenos aires": "south_america",
        "chile": "south_america", "santiago": "south_america",
        "colombia": "south_america", "bogota": "south_america",
        "peru": "south_america", "lima": "south_america",
        "panama": "south_america",
        # Africa
        "south africa": "africa", "johannesburg": "africa",
        "kenya": "africa", "nairobi": "africa",
        "ethiopia": "africa", "addis ababa": "africa",
        "egypt": "africa", "cairo": "africa",
        "morocco": "africa", "casablanca": "africa",
        "nigeria": "africa", "lagos": "africa",
    }

    # Aircraft normalization
    AIRCRAFT_MAP = {
        "a320": "Airbus A320", "a319": "Airbus A319", "a321": "Airbus A321",
        "a320neo": "Airbus A320neo", "a321neo": "Airbus A321neo",
        "a330": "Airbus A330", "a340": "Airbus A340", "a350": "Airbus A350",
        "a380": "Airbus A380",
        "b737": "Boeing 737", "737": "Boeing 737", "737ng": "Boeing 737NG",
        "737max": "Boeing 737 MAX", "b737max": "Boeing 737 MAX",
        "b747": "Boeing 747", "747": "Boeing 747",
        "b777": "Boeing 777", "777": "Boeing 777",
        "b787": "Boeing 787", "787": "Boeing 787", "dreamliner": "Boeing 787",
        "e190": "Embraer E190", "e195": "Embraer E195", "e-jet": "Embraer E-Jet",
        "atr": "ATR", "atr72": "ATR 72", "atr42": "ATR 42",
        "crj": "Bombardier CRJ", "crj900": "Bombardier CRJ-900",
        "dash 8": "De Havilland Dash 8", "q400": "Dash 8 Q400",
    }

    @classmethod
    def normalize(cls, job: ScrapedJob, airline_region: str = None) -> Optional[Dict[str, Any]]:
        """
        Normalize a scraped job. Returns None if the job is invalid (junk).
        """

        # Build raw text for AI parsing
        raw_text = f"{job.title}\n\n{job.description or ''}"

        # === AI PARSING (THE FILTER) ===
        if AI_AVAILABLE and parse_job_with_ai:
            try:
                ai_data = parse_job_with_ai(raw_text, job.application_url, job.company)

                # --- THE KILL SWITCH ---
                # If AI says this isn't a job, return None immediately.
                if not ai_data.get("is_valid_job", True):
                    logger.warning(f"   🗑️ GARBAGE DETECTED: AI says '{job.title}' is not a valid job.")
                    return None

                # If title looks suspicious (e.g., "FAQ", "Login"), double check
                if any(x in job.title.lower() for x in ["faq", "login", "register", "game", "mobile", "policy"]):
                    logger.warning(f"   🗑️ KEYWORD REJECT: '{job.title}'")
                    return None

                # Proceed with data extraction
                position_type = ai_data.get("position_type", "other")
                aircraft = ", ".join(ai_data.get("aircraft", [])) if ai_data.get("aircraft") else None
                min_hours = ai_data.get("min_hours", 0) or None  # Convert 0 to None
                min_pic_hours = None
                type_rating_required = len(ai_data.get("aircraft", [])) > 0
                type_rating_provided = False
                visa_sponsorship = ai_data.get("visa_sponsored", False)
                is_entry_level = ai_data.get("is_low_hour", False)
                contract_type = "permanent"

                # Update the job title with cleaner AI version if available
                clean_title = ai_data.get("job_title", job.title) or job.title

                # Use AI location if provided, else fall back to scraped location
                location = ai_data.get("location") or job.location or "Not specified"

                # Region detection (AI doesn't provide this, use our logic)
                region = cls._detect_region(location, airline_region)

            except Exception as e:
                logger.warning(f"AI parsing error: {e}")
                # Fall through to regex parsing
                clean_title = job.title
                position_type = cls._detect_position_type(job.title)
                aircraft = cls._detect_aircraft(job.title, job.description or "")
                region = cls._detect_region(job.location, airline_region)
                type_rating_required, type_rating_provided = cls._detect_type_rating(job.title, job.description or "")
                min_hours = cls._detect_hours(job.title, job.description or "")
                min_pic_hours = None
                is_entry_level = cls._detect_entry_level(job.title, position_type, type_rating_provided)
                visa_sponsorship = region == "middle_east" or "visa" in (job.description or "").lower()
                contract_type = "permanent"
                location = job.location or "Not specified"
        else:
            # === REGEX FALLBACK (only if AI unavailable) ===
            clean_title = job.title
            position_type = cls._detect_position_type(job.title)
            aircraft = cls._detect_aircraft(job.title, job.description or "")
            region = cls._detect_region(job.location, airline_region)
            type_rating_required, type_rating_provided = cls._detect_type_rating(job.title, job.description or "")
            min_hours = cls._detect_hours(job.title, job.description or "")
            min_pic_hours = None
            is_entry_level = cls._detect_entry_level(job.title, position_type, type_rating_provided)
            visa_sponsorship = region == "middle_east" or "visa" in (job.description or "").lower()
            contract_type = "permanent"
            location = job.location or "Not specified"

        # Final sanity check before returning
        if any(x in clean_title.lower() for x in ["game", "faq", "login", "register", "policy"]):
            logger.warning(f"   🗑️ FINAL REJECT: '{clean_title}'")
            return None

        return {
            "title": clean_title[:500],
            "company": job.company[:255],
            "location": location[:255] if location else "Not specified",
            "region": region,
            "position_type": position_type,
            "aircraft_type": aircraft,
            "type_rating_required": type_rating_required,
            "type_rating_provided": type_rating_provided,
            "min_total_hours": min_hours,
            "min_pic_hours": min_pic_hours,
            "license_required": "ATPL/CPL",
            "visa_sponsorship": visa_sponsorship,
            "is_entry_level": is_entry_level,
            "contract_type": contract_type,
            "description": job.description,
            "application_url": job.application_url,
            "source": job.source,
            "date_posted": job.date_posted,
            "is_active": True
        }

    @classmethod
    def _detect_position_type(cls, title: str) -> str:
        """Detect position type from title"""
        title_lower = title.lower()

        if any(x in title_lower for x in ["captain", "commander", "pic ", "p.i.c"]):
            return "captain"
        if any(x in title_lower for x in ["first officer", "f/o", "fo ", "co-pilot", "second officer", "s/o"]):
            return "first_officer"
        if any(x in title_lower for x in ["cadet", "trainee", "ab initio", "mpl", "mentored"]):
            return "cadet"
        if any(x in title_lower for x in ["instructor", "trf", "tri", "tre", "examiner", "check pilot"]):
            return "instructor"

        return "other"

    @classmethod
    def _detect_aircraft(cls, title: str, description: str) -> Optional[str]:
        """Detect aircraft type from title/description"""
        text = (title + " " + description).lower()

        for pattern, aircraft in cls.AIRCRAFT_MAP.items():
            if pattern in text:
                return aircraft

        return None

    @classmethod
    def _detect_region(cls, location: str, airline_region: str = None) -> str:
        """Detect region from location"""
        if airline_region:
            return airline_region

        if not location:
            return "global"

        location_lower = location.lower()

        for keyword, region in cls.REGION_MAP.items():
            if keyword in location_lower:
                return region

        return "global"

    @classmethod
    def _detect_type_rating(cls, title: str, description: str) -> tuple:
        """Detect if type rating is required or provided"""
        text = (title + " " + description).lower()

        required = "type rating required" in text or "type rated" in text or "current type" in text
        provided = "type rating provided" in text or "type rating included" in text or "conversion" in text

        return required, provided

    @classmethod
    def _detect_hours(cls, title: str, description: str) -> Optional[int]:
        """
        Smart hours extraction - handles edge cases like:
        - "2000+ hours" (plus sign)
        - "1,500 - 3,000 hours" (ranges - takes minimum)
        - "minimum 1500 total time"
        - Hours spread across multiple lines
        """
        text = title + " " + (description or "")

        # Normalize text - remove newlines, collapse spaces
        text = re.sub(r'\s+', ' ', text)

        # Patterns ordered by specificity (most specific first)
        patterns = [
            # Range patterns - extract minimum
            r'(\d{1,2}[,.]?\d{3})\s*[-–to]+\s*\d{1,2}[,.]?\d{3}\s*(?:hours?|hrs?|h\b)',

            # "2000+ hours" pattern (handles plus sign)
            r'(\d{1,2}[,.]?\d{3})\+?\s*(?:hours?|hrs?|h\b)',

            # "minimum of X hours" or "min X hours"
            r'(?:minimum|min\.?)\s*(?:of\s*)?(\d{1,2}[,.]?\d{3})',

            # "X hours total" or "X total hours" or "X TT"
            r'(\d{1,2}[,.]?\d{3})\s*(?:hours?\s*)?(?:total|tt|TT|total\s*time)',

            # "total time: X" or "TT: X"
            r'(?:total\s*time|TT)\s*[:\-]?\s*(\d{1,2}[,.]?\d{3})',

            # Generic hours pattern (fallback)
            r'(\d{1,2}[,.]?\d{3})\s*(?:hours?|hrs?|h\b)',

            # Just a 4-digit number near "hours" context words
            r'(?:require|need|must have)\s*.*?(\d{1,2}[,.]?\d{3})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hours_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    hours = int(hours_str)
                    # Sanity check: pilot hours are typically between 100 and 25000
                    if 100 <= hours <= 25000:
                        return hours
                except:
                    pass

        # Special case: Look for "X00" pattern if nothing found (like "2000", "1500")
        # Only in context of pilot requirements
        if any(word in text.lower() for word in ['hour', 'experience', 'time', 'requirement']):
            match = re.search(r'\b(\d{1,2}[,.]?\d{3})\b', text)
            if match:
                hours_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    hours = int(hours_str)
                    if 500 <= hours <= 15000:  # More conservative range for fallback
                        return hours
                except:
                    pass

        return None

    @classmethod
    def _detect_entry_level(cls, title: str, position_type: str, type_rating_provided: bool) -> bool:
        """Conservative entry-level detection"""
        title_lower = title.lower()

        # Explicit cadets/trainees are entry level
        if position_type == "cadet":
            return True

        # Entry level keywords
        if any(x in title_lower for x in ["entry level", "graduate", "ab initio", "new hire", "starting"]):
            return True

        # Type rating provided + not captain = likely entry level friendly
        if type_rating_provided and position_type != "captain":
            return True

        return False


# =============================================================================
# 4. DATABASE OPERATIONS
# =============================================================================

class DatabaseOps:
    """Database operations for the scraper"""

    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and Key are required")
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_airlines_to_scrape(self, limit: int = None) -> List[Dict]:
        """Get all active airlines from the database"""
        query = self.client.table("airlines_to_scrape").select("*").eq("status", "active")

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data or []

    def get_airline_by_name(self, name: str) -> Optional[Dict]:
        """Get a single airline by name (case-insensitive)"""
        response = self.client.table("airlines_to_scrape")\
            .select("*")\
            .ilike("name", name)\
            .limit(1)\
            .execute()

        if response.data:
            return response.data[0]
        return None

    def get_stale_airlines(self, hours_threshold: int = 4, limit: int = 5) -> List[Dict]:
        """Get airlines that haven't been checked recently (for queue system)"""
        cutoff = (datetime.utcnow() - timedelta(hours=hours_threshold)).isoformat()

        response = self.client.table("airlines_to_scrape")\
            .select("*")\
            .eq("status", "active")\
            .lt("last_checked", cutoff)\
            .order("last_checked")\
            .limit(limit)\
            .execute()

        return response.data or []

    def update_airline_status(self, airline_id: str, jobs_found: int, error: str = None):
        """Update airline after scraping"""
        update_data = {
            "last_checked": datetime.utcnow().isoformat(),
            "jobs_found_last_scrape": jobs_found,
        }

        if error:
            update_data["consecutive_failures"] = self.client.table("airlines_to_scrape")\
                .select("consecutive_failures")\
                .eq("id", airline_id)\
                .single()\
                .execute().data.get("consecutive_failures", 0) + 1
            update_data["last_error"] = error[:500]

            # Set to error status if too many failures
            if update_data["consecutive_failures"] >= 5:
                update_data["status"] = "error"
        else:
            update_data["consecutive_failures"] = 0
            update_data["last_successful_scrape"] = datetime.utcnow().isoformat()
            update_data["last_error"] = None

        self.client.table("airlines_to_scrape").update(update_data).eq("id", airline_id).execute()

    def upsert_jobs(self, jobs: List[Dict]) -> int:
        """Upsert jobs to database, returns count of jobs saved"""
        if not jobs:
            return 0

        # Upsert based on application_url (unique key)
        response = self.client.table("pilot_jobs").upsert(
            jobs,
            on_conflict="application_url"
        ).execute()

        return len(response.data) if response.data else 0

    def log_scrape(self, airline_id: str, airline_name: str, ats_type: str,
                   status: str, jobs_found: int, duration: float, error: str = None):
        """Log scrape attempt for analytics"""
        log_data = {
            "airline_id": airline_id,
            "airline_name": airline_name,
            "ats_type_detected": ats_type,
            "status": status,
            "jobs_found": jobs_found,
            "duration_seconds": round(duration, 2),
            "error_message": error[:500] if error else None,
            "completed_at": datetime.utcnow().isoformat()
        }

        self.client.table("scrape_logs").insert(log_data).execute()


# =============================================================================
# 5. MAIN UNIVERSAL ENGINE
# =============================================================================

class UniversalEngine:
    """The main scraper engine that coordinates everything"""

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.db = None if test_mode else DatabaseOps(SUPABASE_URL, SUPABASE_KEY)
        self.scrapers = MasterScrapers()
        self.normalizer = JobNormalizer()

    def run(self, single_airline: str = None, use_ai: bool = False):
        """Run the scraper for all airlines or a single airline"""
        logger.info("=" * 60)
        logger.info("STARTING UNIVERSAL SCRAPER ENGINE")
        logger.info(f"AI Parsing: {'ENABLED' if AI_AVAILABLE else 'DISABLED (using regex fallback)'}")
        logger.info("=" * 60)

        # Get airlines to scrape
        if single_airline:
            if self.test_mode:
                # Use mock data in test mode
                mock_airlines = {
                    "Emirates": {"url": "https://www.emiratesgroupcareers.com/pilots/", "region": "middle_east"},
                    "Qatar Airways": {"url": "https://careers.qatarairways.com/global/en/c/pilots-jobs", "region": "middle_east"},
                    "Qantas": {"url": "https://www.qantas.com/au/en/about-us/qantas-careers/pilots.html", "region": "oceania"},
                    "Ryanair": {"url": "https://careers.ryanair.com/search/?q=pilot", "region": "europe"},
                }
                if single_airline in mock_airlines:
                    airlines = [{"name": single_airline, "career_page_url": mock_airlines[single_airline]["url"], "id": None, "region": mock_airlines[single_airline]["region"]}]
                else:
                    airlines = [{"name": single_airline, "career_page_url": "", "id": None, "region": "global"}]
            else:
                # Fetch from database
                airline_data = self.db.get_airline_by_name(single_airline)
                if airline_data:
                    airlines = [airline_data]
                else:
                    logger.error(f"Airline '{single_airline}' not found in database")
                    return
        elif self.test_mode:
            # Mock data for testing
            airlines = [
                {"name": "Emirates", "career_page_url": "https://emirates.taleo.net/careersection/2/jobsearch.ftl", "id": None, "region": "middle_east"},
                {"name": "Qatar Airways", "career_page_url": "https://careers.qatarairways.com/global/en/c/pilots-jobs", "id": None, "region": "middle_east"},
                {"name": "Qantas", "career_page_url": "https://qantas.wd3.myworkdayjobs.com/Qantas_Careers", "id": None, "region": "oceania"},
            ]
        else:
            airlines = self.db.get_airlines_to_scrape()

        if not airlines:
            logger.warning("No airlines found to scrape!")
            return

        logger.info(f"Found {len(airlines)} airlines to scrape")

        all_jobs = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            for airline in airlines:
                airline_name = airline["name"]
                url = airline.get("career_page_url") or airline.get("url", "")
                airline_id = airline.get("id")
                airline_region = airline.get("region", "global")

                if not url:
                    logger.warning(f"No URL for {airline_name}, skipping...")
                    continue

                logger.info(f"\n{'='*40}")
                logger.info(f"Processing: {airline_name}")
                logger.info(f"URL: {url}")

                start_time = time.time()

                # Detect ATS type
                ats_type = detect_ats_type(url)
                logger.info(f"Detected ATS: {ats_type}")

                # Route to correct scraper
                jobs = []
                error = None

                try:
                    if ats_type == "TALEO":
                        jobs = self.scrapers.scrape_taleo(page, airline_name, url)
                    elif ats_type == "WORKDAY":
                        jobs = self.scrapers.scrape_workday(page, airline_name, url)
                    elif ats_type == "SUCCESSFACTORS":
                        jobs = self.scrapers.scrape_successfactors(page, airline_name, url)
                    else:
                        jobs = self.scrapers.scrape_custom_ai(page, airline_name, url)

                    logger.info(f"Found {len(jobs)} pilot jobs for {airline_name}")

                except Exception as e:
                    error = str(e)
                    logger.error(f"CRITICAL ERROR scraping {airline_name}: {e}")

                duration = time.time() - start_time

                # Normalize jobs (filter out non-jobs detected by AI)
                normalized_jobs = []
                filtered_count = 0
                for job in jobs:
                    try:
                        normalized = self.normalizer.normalize(job, airline_region)
                        if normalized is not None:
                            normalized_jobs.append(normalized)
                        else:
                            filtered_count += 1
                    except Exception as e:
                        logger.error(f"Error normalizing job: {e}")

                if filtered_count > 0:
                    logger.info(f"   Filtered out {filtered_count} non-job pages (FAQs, login pages, etc.)")

                # Deduplicate by URL
                seen_urls = set()
                unique_jobs = []
                for job in normalized_jobs:
                    if job["application_url"] not in seen_urls:
                        seen_urls.add(job["application_url"])
                        unique_jobs.append(job)

                all_jobs.extend(unique_jobs)

                # Update database (if not test mode)
                if not self.test_mode and self.db and airline_id:
                    try:
                        # Save jobs
                        saved_count = self.db.upsert_jobs(unique_jobs)
                        logger.info(f"Saved {saved_count} jobs to database")

                        # Update airline status
                        self.db.update_airline_status(airline_id, len(unique_jobs), error)

                        # Log scrape
                        self.db.log_scrape(
                            airline_id=airline_id,
                            airline_name=airline_name,
                            ats_type=ats_type,
                            status="success" if not error else "failed",
                            jobs_found=len(unique_jobs),
                            duration=duration,
                            error=error
                        )
                    except Exception as e:
                        logger.error(f"Database error: {e}")

                # Be polite - wait between airlines
                time.sleep(2)

            browser.close()

        # Save to JSON file (always, as backup)
        output_file = "scraper/output/universal_jobs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, default=str)

        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPE COMPLETE")
        logger.info(f"Total jobs found: {len(all_jobs)}")
        logger.info(f"Output saved to: {output_file}")
        logger.info(f"{'='*60}")

        return all_jobs


# =============================================================================
# 6. CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Universal Airline Job Scraper")
    parser.add_argument("--airline", type=str, help="Scrape a single airline by name")
    parser.add_argument("--test", action="store_true", help="Test mode (no database writes)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    engine = UniversalEngine(test_mode=args.test)
    engine.run(single_airline=args.airline)


if __name__ == "__main__":
    main()

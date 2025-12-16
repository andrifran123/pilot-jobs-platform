"""
Airline Hunter - Automatic Airline Discovery System
====================================================
This script automatically discovers new airlines and their career pages.
Run this monthly to expand your airline database.

Sources:
1. Wikipedia lists of airlines
2. Google search for career pages
3. IATA/ICAO airline databases

Usage:
    python airline_hunter.py                    # Run full discovery
    python airline_hunter.py --source wikipedia # Only scrape Wikipedia
    python airline_hunter.py --search "Delta"   # Search for specific airline
    python airline_hunter.py --test             # Dry run (no DB writes)
"""

import os
import re
import time
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# --- CONFIGURATION ---
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# Optional: Use SerpAPI or Serper.dev for Google searches
# Free alternatives: DuckDuckGo, Bing Search API
SERP_API_KEY = os.getenv("SERP_API_KEY")  # serper.dev key
SERPAPI_KEY = os.getenv("SERPAPI_KEY")    # serpapi.com key

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper/logs/airline_hunter.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs('scraper/logs', exist_ok=True)
os.makedirs('scraper/output', exist_ok=True)


# =============================================================================
# 1. WIKIPEDIA SCRAPER - Get airline names from Wikipedia
# =============================================================================

class WikipediaScraper:
    """Scrapes airline names from Wikipedia lists"""

    # Wikipedia pages with airline lists
    WIKI_SOURCES = [
        # By region
        "https://en.wikipedia.org/wiki/List_of_airlines_of_Europe",
        "https://en.wikipedia.org/wiki/List_of_airlines_of_Asia",
        "https://en.wikipedia.org/wiki/List_of_airlines_of_North_America",
        "https://en.wikipedia.org/wiki/List_of_airlines_of_South_America",
        "https://en.wikipedia.org/wiki/List_of_airlines_of_Africa",
        "https://en.wikipedia.org/wiki/List_of_airlines_of_Oceania",
        # Special lists
        "https://en.wikipedia.org/wiki/List_of_largest_airlines_in_the_world",
        "https://en.wikipedia.org/wiki/List_of_low-cost_airlines",
        "https://en.wikipedia.org/wiki/List_of_cargo_airlines",
    ]

    # Region mapping from Wikipedia page URLs
    REGION_FROM_URL = {
        "europe": "europe",
        "asia": "asia",
        "north_america": "north_america",
        "south_america": "south_america",
        "africa": "africa",
        "oceania": "oceania",
        "middle_east": "middle_east",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_airlines_from_page(self, url: str) -> List[Dict]:
        """Extract airline names from a Wikipedia page"""
        airlines = []

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Detect region from URL
            region = "global"
            for key, value in self.REGION_FROM_URL.items():
                if key in url.lower():
                    region = value
                    break

            # Strategy 1: Find tables with airline data
            tables = soup.find_all('table', class_='wikitable')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        # First cell usually has airline name
                        first_cell = cells[0]
                        link = first_cell.find('a')
                        if link:
                            name = link.get_text(strip=True)
                            # Skip invalid names
                            if name and len(name) > 2 and not name.startswith('['):
                                airlines.append({
                                    "name": name,
                                    "region": region,
                                    "source": "wikipedia"
                                })

            # Strategy 2: Find lists with airline links (only in main content)
            # Get main content area only (excludes sidebar, navigation, footer)
            content = soup.find('div', {'id': 'mw-content-text'}) or soup.find('div', {'class': 'mw-parser-output'})
            if content:
                lists = content.find_all(['ul', 'ol'])
                for lst in lists:
                    # Skip navigation/menu lists
                    parent_classes = ' '.join(lst.parent.get('class', []) if lst.parent else [])
                    if any(x in parent_classes for x in ['navbox', 'sidebar', 'navigation', 'toc']):
                        continue

                    items = lst.find_all('li', recursive=False)  # Only direct children
                    for item in items:
                        link = item.find('a')
                        if link:
                            href = link.get('href', '')
                            # Skip Wikipedia internal/navigation links
                            if href.startswith('#') or ':' in href.split('/')[-1]:
                                continue
                            # Must be a wiki article link
                            if not href.startswith('/wiki/'):
                                continue

                            name = link.get_text(strip=True)
                            # Basic filtering
                            if name and len(name) > 2 and len(name) < 100:
                                # Skip obviously non-airline items
                                skip_words = ['defunct', 'former', 'see also', 'references',
                                              'category', 'main page', 'contents', 'current events',
                                              'random article', 'about wikipedia', 'contact', 'help',
                                              'learn to edit', 'community portal', 'recent changes',
                                              'upload file', 'special pages', 'permanent link',
                                              'page information', 'cite this', 'wikidata', 'download',
                                              'printable', 'what links here', 'related changes']
                                if not any(w in name.lower() for w in skip_words):
                                    airlines.append({
                                        "name": name,
                                        "region": region,
                                        "source": "wikipedia"
                                    })

            logger.info(f"Found {len(airlines)} airlines from {url}")

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return airlines

    def get_all_airlines(self) -> List[Dict]:
        """Scrape all Wikipedia sources"""
        all_airlines = []
        seen_names = set()

        for url in self.WIKI_SOURCES:
            airlines = self.get_airlines_from_page(url)
            for airline in airlines:
                # Deduplicate by name
                if airline["name"].lower() not in seen_names:
                    seen_names.add(airline["name"].lower())
                    all_airlines.append(airline)
            time.sleep(2)  # Be nice to Wikipedia - avoid rate limits

        logger.info(f"Total unique airlines from Wikipedia: {len(all_airlines)}")
        return all_airlines


# =============================================================================
# 2. CAREER PAGE FINDER - Google search for career URLs
# =============================================================================

class CareerPageFinder:
    """Finds career page URLs for airlines using search engines"""

    # Domains to skip (not career pages)
    SKIP_DOMAINS = [
        "linkedin.com", "indeed.com", "glassdoor.com", "wikipedia.org",
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "news.", "bbc.", "cnn.", "reuters.", "bloomberg.",
        "amazon.com", "google.com", "bing.com"
    ]

    # Keywords that indicate a career page
    CAREER_KEYWORDS = ["career", "job", "vacanc", "recruit", "employment", "hiring", "join"]

    def __init__(self, api_key: str = None):
        self.serp_api_key = api_key or SERP_API_KEY
        self.serpapi_key = SERPAPI_KEY
        self.session = requests.Session()

    def find_career_url(self, airline_name: str) -> Optional[str]:
        """
        Search for airline's career page.
        Tries multiple methods: Serper API, SerpAPI, DuckDuckGo fallback
        """
        query = f"{airline_name} airline pilot careers official site"

        # Try Serper.dev API first (if available)
        if self.serp_api_key:
            url = self._search_serper(query)
            if url:
                return url

        # Try SerpAPI (if available)
        if self.serpapi_key:
            url = self._search_serpapi(query)
            if url:
                return url

        # Fallback to DuckDuckGo (free, no API key needed)
        url = self._search_duckduckgo(query)
        if url:
            return url

        return None

    def _search_serper(self, query: str) -> Optional[str]:
        """Search using Serper.dev API"""
        try:
            response = self.session.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": self.serp_api_key,
                    "Content-Type": "application/json"
                },
                json={"q": query, "num": 10},
                timeout=10
            )
            results = response.json().get("organic", [])

            for result in results:
                link = result.get("link", "")
                if self._is_valid_career_url(link):
                    return link

        except Exception as e:
            logger.debug(f"Serper search error: {e}")

        return None

    def _search_serpapi(self, query: str) -> Optional[str]:
        """Search using SerpAPI"""
        try:
            response = self.session.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.serpapi_key,
                    "engine": "google",
                    "num": 10
                },
                timeout=10
            )
            results = response.json().get("organic_results", [])

            for result in results:
                link = result.get("link", "")
                if self._is_valid_career_url(link):
                    return link

        except Exception as e:
            logger.debug(f"SerpAPI search error: {e}")

        return None

    def _search_duckduckgo(self, query: str) -> Optional[str]:
        """Search using DuckDuckGo (free, no API key)"""
        try:
            # DuckDuckGo HTML search
            response = self.session.get(
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=10
            )
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find result links - try multiple selectors
            # DuckDuckGo HTML results structure varies
            results = []

            # Try .result__url (old structure)
            results.extend(soup.find_all('a', class_='result__url'))

            # Try .result__a (newer structure)
            results.extend(soup.find_all('a', class_='result__a'))

            # Try any link within .result div
            for div in soup.find_all('div', class_='result'):
                links = div.find_all('a', href=True)
                results.extend(links)

            # Try links within .results div
            results_div = soup.find('div', class_='results')
            if results_div:
                for link in results_div.find_all('a', href=True):
                    if link.get('href', '').startswith('http'):
                        results.append(link)

            seen_urls = set()
            for result in results:
                link = result.get('href', '')

                # Skip empty or duplicate
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                # Handle relative URLs
                if link.startswith('//'):
                    link = 'https:' + link

                # Skip DuckDuckGo internal links
                if 'duckduckgo.com' in link:
                    continue

                if self._is_valid_career_url(link):
                    return link

        except Exception as e:
            logger.debug(f"DuckDuckGo search error: {e}")

        return None

    def _is_valid_career_url(self, url: str) -> bool:
        """Check if URL looks like a legitimate career page"""
        if not url:
            return False

        url_lower = url.lower()

        # Skip blacklisted domains
        for domain in self.SKIP_DOMAINS:
            if domain in url_lower:
                return False

        # Prefer URLs with career keywords
        has_career_keyword = any(kw in url_lower for kw in self.CAREER_KEYWORDS)

        # Must be HTTPS
        if not url.startswith("https://"):
            return False

        return has_career_keyword or True  # Accept even without keyword if it passed other checks


# =============================================================================
# 3. ATS DETECTOR - Detect what system the career page uses
# =============================================================================

class ATSDetector:
    """Detects the ATS (Applicant Tracking System) from a URL"""

    ATS_PATTERNS = {
        "TALEO": ["taleo.net", "taleo.com", "oraclecloud.com/hcmUI"],
        "WORKDAY": ["myworkdayjobs.com", "workday.com", ".wd1.", ".wd3.", ".wd5."],
        "SUCCESSFACTORS": ["successfactors.com", "successfactors.eu", "jobs2web.com"],
        "BRASSRING": ["brassring.com"],
        "ICIMS": ["icims.com"],
        "GREENHOUSE": ["greenhouse.io", "boards.greenhouse"],
        "LEVER": ["lever.co", "jobs.lever"],
        "SMARTRECRUITERS": ["smartrecruiters.com"],
        "AVATURE": ["avature.net"],
    }

    @classmethod
    def detect(cls, url: str) -> str:
        """Detect ATS type from URL"""
        url_lower = url.lower()

        for ats_type, patterns in cls.ATS_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return ats_type

        return "CUSTOM_AI"


# =============================================================================
# 4. DATABASE OPERATIONS
# =============================================================================

class HunterDB:
    """Database operations for the hunter"""

    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not provided, running in offline mode")
            self.client = None
        else:
            self.client: Client = create_client(supabase_url, supabase_key)

    def get_existing_airlines(self) -> Set[str]:
        """Get set of existing airline names"""
        if not self.client:
            return set()

        response = self.client.table("airlines_to_scrape").select("name").execute()
        return {a["name"].lower() for a in response.data} if response.data else set()

    def add_airline(self, airline_data: Dict) -> bool:
        """Add new airline to database"""
        if not self.client:
            return False

        try:
            self.client.table("airlines_to_scrape").insert(airline_data).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding airline: {e}")
            return False

    def update_airline_url(self, name: str, url: str, ats_type: str) -> bool:
        """Update airline with discovered URL"""
        if not self.client:
            return False

        try:
            self.client.table("airlines_to_scrape").update({
                "career_page_url": url,
                "ats_type": ats_type,
                "status": "active"
            }).eq("name", name).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating airline: {e}")
            return False


# =============================================================================
# 5. MAIN HUNTER ENGINE
# =============================================================================

class AirlineHunter:
    """Main hunter engine that coordinates discovery"""

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.wiki_scraper = WikipediaScraper()
        self.career_finder = CareerPageFinder()
        self.db = HunterDB(SUPABASE_URL, SUPABASE_KEY) if not test_mode else None
        self.discovered_airlines = []

    def hunt_from_wikipedia(self) -> List[Dict]:
        """Discover airlines from Wikipedia"""
        logger.info("Starting Wikipedia airline discovery...")

        airlines = self.wiki_scraper.get_all_airlines()
        existing = self.db.get_existing_airlines() if self.db else set()

        new_airlines = []
        for airline in airlines:
            if airline["name"].lower() not in existing:
                new_airlines.append(airline)

        logger.info(f"Found {len(new_airlines)} new airlines not in database")
        return new_airlines

    def find_career_pages(self, airlines: List[Dict], limit: int = None) -> List[Dict]:
        """Find career page URLs for a list of airlines"""
        logger.info(f"Searching for career pages for {len(airlines)} airlines...")

        results = []
        count = 0

        for airline in airlines:
            if limit and count >= limit:
                break

            name = airline["name"]
            logger.info(f"Searching: {name}")

            url = self.career_finder.find_career_url(name)

            if url:
                ats_type = ATSDetector.detect(url)
                airline_data = {
                    "name": name,
                    "career_page_url": url,
                    "ats_type": ats_type,
                    "region": airline.get("region", "global"),
                    "status": "active",
                    "tier": 3,  # Default to Tier 3 for new discoveries
                    "scrape_frequency_hours": 24,
                    "discovered_by": "hunter"
                }
                results.append(airline_data)
                logger.info(f"   FOUND: {url} (ATS: {ats_type})")

                # Save to database
                if self.db and not self.test_mode:
                    self.db.add_airline(airline_data)
            else:
                logger.info(f"   No career page found for {name}")

            count += 1
            time.sleep(1)  # Rate limiting

        return results

    def hunt_specific(self, airline_names: List[str]) -> List[Dict]:
        """Hunt for specific airlines by name"""
        airlines = [{"name": name, "region": "global"} for name in airline_names]
        return self.find_career_pages(airlines)

    def run_full_hunt(self, limit: int = None):
        """Run full discovery process"""
        logger.info("=" * 60)
        logger.info("STARTING FULL AIRLINE HUNT")
        logger.info("=" * 60)

        # Step 1: Get airlines from Wikipedia
        new_airlines = self.hunt_from_wikipedia()

        # Step 2: Find career pages
        if limit:
            new_airlines = new_airlines[:limit]

        discovered = self.find_career_pages(new_airlines)

        # Save results to file
        output_file = "scraper/output/discovered_airlines.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(discovered, f, indent=2)

        logger.info("=" * 60)
        logger.info(f"HUNT COMPLETE")
        logger.info(f"Airlines discovered: {len(discovered)}")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 60)

        return discovered


# =============================================================================
# 6. GOOGLE DORK HUNTER - Find hidden job PDFs and pages
# =============================================================================

class GoogleDorkHunter:
    """
    Uses Google dorks to find hidden pilot job postings.
    These are jobs that aren't on standard career pages.
    """

    DORK_QUERIES = [
        'site:*.pdf "pilot" "captain" "first officer" hiring',
        '"pilot vacancy" OR "captain vacancy" filetype:pdf',
        'site:linkedin.com/jobs "airline pilot" posted:week',
        '"direct entry captain" OR "direct entry first officer" apply',
        'site:*.aero "pilot" "careers" OR "recruitment"',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.serp_api_key = SERP_API_KEY

    def search_dork(self, query: str) -> List[Dict]:
        """Execute a Google dork search"""
        results = []

        if not self.serp_api_key:
            logger.warning("No SERP API key, skipping dork search")
            return results

        try:
            response = self.session.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": self.serp_api_key,
                    "Content-Type": "application/json"
                },
                json={"q": query, "num": 20},
                timeout=15
            )
            data = response.json()

            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google_dork"
                })

        except Exception as e:
            logger.error(f"Dork search error: {e}")

        return results

    def run_all_dorks(self) -> List[Dict]:
        """Run all Google dork queries"""
        all_results = []

        for query in self.DORK_QUERIES:
            logger.info(f"Running dork: {query[:50]}...")
            results = self.search_dork(query)
            all_results.extend(results)
            time.sleep(2)

        # Deduplicate by URL
        seen = set()
        unique = []
        for r in all_results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)

        return unique


# =============================================================================
# 7. CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Airline Hunter - Discover new airlines")
    parser.add_argument("--source", choices=["wikipedia", "dork", "all"], default="all",
                        help="Discovery source")
    parser.add_argument("--search", type=str, nargs="+",
                        help="Search for specific airline(s)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of airlines to process")
    parser.add_argument("--test", action="store_true",
                        help="Test mode (no database writes)")

    args = parser.parse_args()

    hunter = AirlineHunter(test_mode=args.test)

    if args.search:
        # Search for specific airlines
        results = hunter.hunt_specific(args.search)
        print(f"\nFound {len(results)} airlines:")
        for r in results:
            print(f"  {r['name']}: {r['career_page_url']} ({r['ats_type']})")

    elif args.source == "wikipedia":
        # Only Wikipedia
        airlines = hunter.hunt_from_wikipedia()
        hunter.find_career_pages(airlines, limit=args.limit)

    elif args.source == "dork":
        # Only Google dorks
        dork_hunter = GoogleDorkHunter()
        results = dork_hunter.run_all_dorks()
        print(f"\nFound {len(results)} results from dorks")
        for r in results[:10]:
            print(f"  {r['title'][:50]}: {r['url']}")

    else:
        # Full hunt
        hunter.run_full_hunt(limit=args.limit)


if __name__ == "__main__":
    main()

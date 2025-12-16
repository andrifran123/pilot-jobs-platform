"""
Discovery Bot - Light scraper for competitor sites

Purpose: Discover WHICH airlines are hiring, not to get job data.
- Scrapes aggregator sites lightly to find airline names
- Adds new airlines to our database for direct scraping
- Avoids getting blocked by being gentle

This is "Tier 2" in the scraping strategy:
- Don't rely on aggregator data (stale, incomplete)
- Just use them to discover hiring trends
- Then go direct to airline ATS for accurate data
"""

import asyncio
import re
from typing import List, Dict, Set
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class DiscoveryBot:
    """Light scraper to discover which airlines are hiring"""

    # Known competitor aggregator sites
    AGGREGATOR_SITES = [
        {
            'name': 'PilotsGlobal',
            'url': 'https://pilotsglobal.com/jobs',
            'selectors': {
                'job_list': '.job-listing, .job-card',
                'company': '.company, .employer',
                'title': '.job-title, h3, h4',
            }
        },
        {
            'name': 'AllFlyingJobs',
            'url': 'https://www.allflyingjobs.com/jobs/search/pilots',
            'selectors': {
                'job_list': '.job-item, .vacancy',
                'company': '.company-name, .employer',
                'title': '.job-title, .vacancy-title',
            }
        },
        {
            'name': 'Flightglobal Jobs',
            'url': 'https://jobs.flightglobal.com/jobs/pilot/',
            'selectors': {
                'job_list': '.job-result, .search-result',
                'company': '.company, .job-company',
                'title': '.job-title, h3',
            }
        },
        {
            'name': 'AvJobs',
            'url': 'https://www.avjobs.com/jobs/search.asp',
            'selectors': {
                'job_list': '.job-listing, tr.job',
                'company': '.company, td:nth-child(2)',
                'title': '.title, td:nth-child(1)',
            }
        },
        {
            'name': 'AERO Crew News',
            'url': 'https://www.aerocrewnews.com/pilot-jobs/',
            'selectors': {
                'job_list': '.job-posting, article',
                'company': '.company, .employer',
                'title': '.job-title, h2',
            }
        },
    ]

    # Keywords that suggest pilot hiring
    HIRING_KEYWORDS = [
        'pilot', 'captain', 'first officer', 'f/o', 'cadet',
        'type rating', 'direct entry', 'flight crew',
        'a320', 'a330', 'a350', 'b737', 'b777', 'b787',
    ]

    # Known airline name patterns (to extract from text)
    AIRLINE_PATTERNS = [
        r'([\w\s]+(?:air|airways|airlines|aviation|jet|fly))',
        r'(ryanair|easyjet|wizz\s*air|vueling|transavia)',
        r'(emirates|etihad|qatar|flydubai|air\s*arabia)',
        r'(lufthansa|swiss|austrian|brussels|eurowings)',
        r'(british\s*airways|virgin\s*atlantic|jet2)',
        r'(klm|air\s*france|transavia)',
        r'(sas|norwegian|finnair|icelandair)',
        r'(turkish|pegasus|sunexpress)',
        r'(aegean|olympic|tap\s*portugal|iberia)',
        r'(lot\s*polish|enter\s*air|smartwings)',
        r'(singapore|cathay|eva\s*air|china\s*airlines)',
    ]

    def __init__(self, known_airlines: Set[str] = None):
        """
        Initialize discovery bot

        Args:
            known_airlines: Set of airline names we already track
        """
        self.known_airlines = known_airlines or set()
        self.discovered_airlines = set()
        self.discovery_log = []

    async def run_discovery(self) -> Dict:
        """
        Run discovery across all aggregator sites

        Returns:
            Dict with discovered airlines and metadata
        """
        print("\n[Discovery] Starting airline discovery scan...")
        print(f"[Discovery] Known airlines: {len(self.known_airlines)}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        timeout = httpx.Timeout(20.0, connect=10.0)

        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False
        ) as client:
            for site in self.AGGREGATOR_SITES:
                await self._scan_aggregator(site, client)
                # Be gentle - wait between sites
                await asyncio.sleep(3)

        # Find truly new airlines
        new_airlines = self.discovered_airlines - self.known_airlines

        results = {
            'timestamp': datetime.now().isoformat(),
            'sites_scanned': len(self.AGGREGATOR_SITES),
            'total_discovered': len(self.discovered_airlines),
            'new_airlines': list(new_airlines),
            'discovery_log': self.discovery_log,
        }

        print(f"\n[Discovery] Scan complete!")
        print(f"[Discovery] Total airlines discovered: {len(self.discovered_airlines)}")
        print(f"[Discovery] New airlines found: {len(new_airlines)}")

        if new_airlines:
            print("\n[Discovery] NEW AIRLINES FOUND:")
            for airline in sorted(new_airlines):
                print(f"  - {airline}")

        return results

    async def _scan_aggregator(self, site: Dict, client: httpx.AsyncClient):
        """Scan a single aggregator site for airline names"""
        site_name = site['name']
        url = site['url']

        print(f"\n[Discovery] Scanning {site_name}...")

        try:
            response = await client.get(url)

            if response.status_code != 200:
                print(f"[Discovery] Failed to load {site_name}: {response.status_code}")
                self.discovery_log.append({
                    'site': site_name,
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}'
                })
                return

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            # Extract airline names from page
            airlines_found = self._extract_airline_names(soup, site['selectors'])

            self.discovered_airlines.update(airlines_found)

            self.discovery_log.append({
                'site': site_name,
                'status': 'success',
                'airlines_found': len(airlines_found),
                'airlines': list(airlines_found)[:20]  # Log first 20
            })

            print(f"[Discovery] Found {len(airlines_found)} airlines on {site_name}")

        except httpx.TimeoutException:
            print(f"[Discovery] Timeout on {site_name}")
            self.discovery_log.append({
                'site': site_name,
                'status': 'timeout'
            })
        except Exception as e:
            print(f"[Discovery] Error on {site_name}: {str(e)}")
            self.discovery_log.append({
                'site': site_name,
                'status': 'error',
                'error': str(e)
            })

    def _extract_airline_names(self, soup: BeautifulSoup, selectors: Dict) -> Set[str]:
        """Extract airline names from page content"""
        airlines = set()

        # Try specific selectors first
        company_selector = selectors.get('company', '')
        if company_selector:
            for selector in company_selector.split(', '):
                elements = soup.select(selector)
                for elem in elements:
                    name = self._clean_airline_name(elem.get_text(strip=True))
                    if name:
                        airlines.add(name)

        # Also scan full page text for airline patterns
        page_text = soup.get_text()
        for pattern in self.AIRLINE_PATTERNS:
            matches = re.findall(pattern, page_text, re.I)
            for match in matches:
                name = self._clean_airline_name(match)
                if name:
                    airlines.add(name)

        # Look for specific well-known airline mentions
        known_names = [
            'Ryanair', 'EasyJet', 'Wizz Air', 'Vueling', 'Norwegian',
            'Emirates', 'Etihad', 'Qatar Airways', 'FlyDubai',
            'Lufthansa', 'Swiss', 'Austrian Airlines', 'Eurowings',
            'British Airways', 'Virgin Atlantic', 'Jet2',
            'KLM', 'Air France', 'Transavia',
            'Turkish Airlines', 'Pegasus', 'SunExpress',
            'LOT Polish', 'Enter Air', 'Smartwings',
            'Aegean Airlines', 'TAP Portugal', 'Iberia',
            'SAS', 'Finnair', 'Icelandair',
            'Singapore Airlines', 'Cathay Pacific', 'EVA Air',
            'Air Asia', 'Scoot', 'Jetstar',
            'Condor', 'TUI', 'Corendon',
            'Volotea', 'Aer Lingus', 'Flybe',
        ]

        for name in known_names:
            if name.lower() in page_text.lower():
                airlines.add(name)

        return airlines

    def _clean_airline_name(self, name: str) -> str:
        """Clean and normalize airline name"""
        if not name:
            return ''

        # Remove extra whitespace
        name = ' '.join(name.split())

        # Skip if too short or too long
        if len(name) < 3 or len(name) > 50:
            return ''

        # Skip if it's just numbers or generic text
        if name.isdigit():
            return ''

        generic_terms = [
            'view', 'apply', 'details', 'more', 'click', 'job', 'jobs',
            'pilot', 'captain', 'first officer', 'see', 'read', 'all',
            'search', 'filter', 'sort', 'page', 'next', 'previous',
        ]

        if name.lower() in generic_terms:
            return ''

        # Capitalize properly
        name = name.title()

        return name

    async def scan_social_media(self) -> Dict:
        """
        Scan social media for pilot hiring announcements
        (Placeholder - would need proper API access)
        """
        # This would scan:
        # - LinkedIn job postings
        # - Facebook aviation groups
        # - Twitter/X aviation hashtags
        # - Aviation forums

        print("[Discovery] Social media scanning not yet implemented")
        return {'status': 'not_implemented'}

    def get_unknown_airlines(self) -> List[str]:
        """Get list of discovered airlines not in our database"""
        return list(self.discovered_airlines - self.known_airlines)

    def suggest_ats_type(self, airline_name: str) -> str:
        """
        Suggest likely ATS type for an airline based on patterns
        """
        # Major airlines by ATS type
        taleo_airlines = [
            'emirates', 'etihad', 'british airways', 'air france', 'klm',
            'qatar', 'singapore', 'cathay'
        ]

        workday_airlines = [
            'delta', 'united', 'american', 'jetblue', 'southwest',
            'qantas', 'air canada'
        ]

        successfactors_airlines = [
            'lufthansa', 'swiss', 'austrian', 'sas', 'finnair', 'norwegian'
        ]

        name_lower = airline_name.lower()

        if any(a in name_lower for a in taleo_airlines):
            return 'taleo'
        elif any(a in name_lower for a in workday_airlines):
            return 'workday'
        elif any(a in name_lower for a in successfactors_airlines):
            return 'successfactors'
        else:
            return 'unknown'


async def test_discovery_bot():
    """Test the discovery bot"""
    # Known airlines from our database
    known = {
        'Ryanair', 'EasyJet', 'Wizz Air', 'Emirates', 'Etihad',
        'Lufthansa', 'British Airways', 'KLM', 'Air France'
    }

    bot = DiscoveryBot(known_airlines=known)
    results = await bot.run_discovery()

    print("\n" + "="*60)
    print("DISCOVERY RESULTS")
    print("="*60)
    print(f"Sites scanned: {results['sites_scanned']}")
    print(f"Total airlines found: {results['total_discovered']}")
    print(f"New airlines: {len(results['new_airlines'])}")

    if results['new_airlines']:
        print("\nNew airlines to investigate:")
        for airline in results['new_airlines'][:20]:
            ats = bot.suggest_ats_type(airline)
            print(f"  - {airline} (likely ATS: {ats})")

    return results


if __name__ == '__main__':
    asyncio.run(test_discovery_bot())

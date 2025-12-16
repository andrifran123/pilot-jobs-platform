"""
Recruitment Agency Scrapers

Major pilot recruitment agencies often have exclusive positions
and provide type-rating programs. These are especially important
for pilots seeking non-type-rated positions.

Key agencies:
- Rishworth Aviation (Asia-Pacific, Middle East)
- PARC Aviation (Europe, Middle East)
- OSM Aviation (Scandinavia, global)
- CAE Parc (Training + placement)
- Aerviva (European airlines)
- Goose Recruitment (Global)
"""

import asyncio
import re
import json
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class RishworthScraper:
    """Scraper for Rishworth Aviation - major Asia-Pacific recruiter"""

    BASE_URL = 'https://www.rishworthaviation.com'
    JOBS_URL = 'https://www.rishworthaviation.com/pilot-jobs'

    PILOT_KEYWORDS = [
        'pilot', 'captain', 'first officer', 'f/o', 'cadet',
        'a320', 'a330', 'a350', 'b737', 'b777', 'b787',
    ]

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch all pilot jobs from Rishworth"""
        print(f"\n[Rishworth] Scraping pilot jobs...")
        jobs = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.JOBS_URL)

                if response.status_code != 200:
                    print(f"[Rishworth] Failed: {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find job listings
                job_cards = soup.select('.job-listing, .vacancy, article, .job-card')

                if not job_cards:
                    # Try finding job links directly
                    job_links = soup.find_all('a', href=re.compile(r'/job|/pilot|/captain|/first-officer', re.I))

                    for link in job_links:
                        title = link.get_text(strip=True)
                        if self._is_pilot_job(title):
                            url = link.get('href', '')
                            if not url.startswith('http'):
                                url = f"{self.BASE_URL}{url}"

                            job = {
                                'title': title,
                                'company': 'Rishworth Aviation',
                                'location': '',
                                'region': 'global',
                                'application_url': url,
                                'source': 'Rishworth Aviation',
                                'date_scraped': datetime.now().isoformat(),
                                'is_active': True,
                                'recruitment_agency': True,
                            }
                            jobs.append(job)

                else:
                    for card in job_cards:
                        job = self._parse_job_card(card)
                        if job:
                            jobs.append(job)

                print(f"[Rishworth] Found {len(jobs)} pilot jobs")

            except Exception as e:
                print(f"[Rishworth] Error: {e}")

        return jobs

    def _parse_job_card(self, card) -> Optional[Dict]:
        """Parse a job card element"""
        title_elem = card.select_one('h2, h3, .title, .job-title, a')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        if not self._is_pilot_job(title):
            return None

        # Get URL
        link = card.select_one('a[href]')
        url = link.get('href', '') if link else ''
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"

        # Get location
        loc_elem = card.select_one('.location, .job-location')
        location = loc_elem.get_text(strip=True) if loc_elem else ''

        # Get airline (if mentioned)
        airline = ''
        text = card.get_text()
        airline_patterns = [
            r'for\s+([\w\s]+(?:Air|Airways|Airlines))',
            r'client[:\s]+([\w\s]+)',
        ]
        for pattern in airline_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                airline = match.group(1).strip()
                break

        return {
            'title': title,
            'company': airline or 'Rishworth Aviation',
            'location': location,
            'region': self._detect_region(location),
            'application_url': url,
            'source': 'Rishworth Aviation',
            'date_scraped': datetime.now().isoformat(),
            'is_active': True,
            'recruitment_agency': True,
        }

    def _is_pilot_job(self, title: str) -> bool:
        if not title:
            return False
        return any(kw in title.lower() for kw in self.PILOT_KEYWORDS)

    def _detect_region(self, location: str) -> str:
        loc_lower = location.lower()
        if any(c in loc_lower for c in ['uae', 'dubai', 'qatar', 'saudi', 'bahrain', 'oman', 'kuwait']):
            return 'middle_east'
        elif any(c in loc_lower for c in ['china', 'korea', 'japan', 'singapore', 'hong kong', 'thailand', 'vietnam', 'indonesia']):
            return 'asia'
        elif any(c in loc_lower for c in ['australia', 'new zealand']):
            return 'oceania'
        elif any(c in loc_lower for c in ['uk', 'germany', 'france', 'spain', 'italy', 'ireland', 'poland']):
            return 'europe'
        return 'global'


class PARCScraper:
    """Scraper for PARC Aviation - European/Middle East recruiter"""

    BASE_URL = 'https://www.parcaviation.aero'
    JOBS_URL = 'https://www.parcaviation.aero/pilot-jobs'

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch pilot jobs from PARC Aviation"""
        print(f"\n[PARC] Scraping pilot jobs...")
        jobs = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.JOBS_URL)

                if response.status_code != 200:
                    print(f"[PARC] Failed: {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, 'html.parser')

                # PARC typically lists jobs in tables or cards
                job_rows = soup.select('table tr, .job-row, .vacancy-item, article')

                for row in job_rows:
                    job = self._parse_job_row(row)
                    if job:
                        jobs.append(job)

                # Also check for job links
                if not jobs:
                    links = soup.find_all('a', href=re.compile(r'job|pilot|captain|officer', re.I))
                    for link in links:
                        title = link.get_text(strip=True)
                        if self._is_pilot_job(title):
                            url = link.get('href', '')
                            if not url.startswith('http'):
                                url = f"{self.BASE_URL}{url}"

                            jobs.append({
                                'title': title,
                                'company': 'PARC Aviation',
                                'location': '',
                                'region': 'europe',
                                'application_url': url,
                                'source': 'PARC Aviation',
                                'date_scraped': datetime.now().isoformat(),
                                'is_active': True,
                                'recruitment_agency': True,
                            })

                print(f"[PARC] Found {len(jobs)} pilot jobs")

            except Exception as e:
                print(f"[PARC] Error: {e}")

        return jobs

    def _parse_job_row(self, row) -> Optional[Dict]:
        text = row.get_text(strip=True)
        if not self._is_pilot_job(text):
            return None

        # Extract title
        title_elem = row.select_one('td:first-child, .title, h3, a')
        title = title_elem.get_text(strip=True) if title_elem else text[:100]

        # Extract link
        link = row.select_one('a[href]')
        url = link.get('href', '') if link else ''
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"

        return {
            'title': title,
            'company': 'PARC Aviation',
            'location': '',
            'region': 'europe',
            'application_url': url or self.JOBS_URL,
            'source': 'PARC Aviation',
            'date_scraped': datetime.now().isoformat(),
            'is_active': True,
            'recruitment_agency': True,
        }

    def _is_pilot_job(self, text: str) -> bool:
        keywords = ['pilot', 'captain', 'first officer', 'f/o', 'cadet', 'a320', 'b737']
        return any(kw in text.lower() for kw in keywords)


class OSMScraper:
    """Scraper for OSM Aviation - Scandinavian recruiter"""

    BASE_URL = 'https://www.osm-aviation.com'
    JOBS_URL = 'https://www.osm-aviation.com/jobs'

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch pilot jobs from OSM Aviation"""
        print(f"\n[OSM] Scraping pilot jobs...")
        jobs = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.JOBS_URL)

                if response.status_code != 200:
                    print(f"[OSM] Failed: {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all job links
                job_links = soup.find_all('a', href=True)

                for link in job_links:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')

                    if self._is_pilot_job(title) or self._is_pilot_job(href):
                        if not href.startswith('http'):
                            href = f"{self.BASE_URL}{href}"

                        if href not in [j.get('application_url') for j in jobs]:
                            jobs.append({
                                'title': title or 'Pilot Position',
                                'company': 'OSM Aviation',
                                'location': 'Scandinavia',
                                'region': 'europe',
                                'application_url': href,
                                'source': 'OSM Aviation',
                                'date_scraped': datetime.now().isoformat(),
                                'is_active': True,
                                'recruitment_agency': True,
                            })

                print(f"[OSM] Found {len(jobs)} pilot jobs")

            except Exception as e:
                print(f"[OSM] Error: {e}")

        return jobs

    def _is_pilot_job(self, text: str) -> bool:
        keywords = ['pilot', 'captain', 'first officer', 'f/o', 'cadet', 'flight crew']
        return any(kw in text.lower() for kw in keywords)


class GooseRecruitmentScraper:
    """Scraper for Goose Recruitment - global aviation recruiter"""

    BASE_URL = 'https://www.goose-recruitment.com'
    JOBS_URL = 'https://www.goose-recruitment.com/jobs/pilots'

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch pilot jobs from Goose Recruitment"""
        print(f"\n[Goose] Scraping pilot jobs...")
        jobs = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.JOBS_URL)

                if response.status_code != 200:
                    print(f"[Goose] Failed: {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find job cards
                job_cards = soup.select('.job-card, .vacancy, article, .listing')

                for card in job_cards:
                    title_elem = card.select_one('h2, h3, .title, a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    link = card.select_one('a[href]')
                    url = link.get('href', '') if link else ''
                    if url and not url.startswith('http'):
                        url = f"{self.BASE_URL}{url}"

                    loc_elem = card.select_one('.location')
                    location = loc_elem.get_text(strip=True) if loc_elem else ''

                    jobs.append({
                        'title': title,
                        'company': 'Goose Recruitment',
                        'location': location,
                        'region': 'global',
                        'application_url': url or self.JOBS_URL,
                        'source': 'Goose Recruitment',
                        'date_scraped': datetime.now().isoformat(),
                        'is_active': True,
                        'recruitment_agency': True,
                    })

                # If no cards found, look for any pilot job links
                if not jobs:
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        if self._is_pilot_job(title):
                            if not href.startswith('http'):
                                href = f"{self.BASE_URL}{href}"
                            jobs.append({
                                'title': title,
                                'company': 'Goose Recruitment',
                                'location': '',
                                'region': 'global',
                                'application_url': href,
                                'source': 'Goose Recruitment',
                                'date_scraped': datetime.now().isoformat(),
                                'is_active': True,
                                'recruitment_agency': True,
                            })

                print(f"[Goose] Found {len(jobs)} pilot jobs")

            except Exception as e:
                print(f"[Goose] Error: {e}")

        return jobs

    def _is_pilot_job(self, text: str) -> bool:
        keywords = ['pilot', 'captain', 'first officer', 'f/o', 'cadet', 'flight crew', 'atpl', 'cpl']
        return any(kw in text.lower() for kw in keywords)


class AgencyOrchestrator:
    """Orchestrates all recruitment agency scrapers"""

    def __init__(self):
        self.scrapers = [
            RishworthScraper(),
            PARCScraper(),
            OSMScraper(),
            GooseRecruitmentScraper(),
        ]

    async def fetch_all_jobs(self) -> List[Dict]:
        """Fetch jobs from all recruitment agencies"""
        print("\n" + "="*50)
        print("RECRUITMENT AGENCY SCRAPING")
        print("="*50)

        all_jobs = []

        for scraper in self.scrapers:
            try:
                jobs = await scraper.fetch_jobs()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"Error with {scraper.__class__.__name__}: {e}")

            await asyncio.sleep(2)  # Be nice between agencies

        print(f"\nTotal agency jobs: {len(all_jobs)}")
        return all_jobs


async def test_agency_scrapers():
    """Test all agency scrapers"""
    orchestrator = AgencyOrchestrator()
    jobs = await orchestrator.fetch_all_jobs()

    print("\n" + "="*60)
    print(f"AGENCY RESULTS: {len(jobs)} jobs")
    print("="*60)

    for job in jobs[:15]:
        print(f"\n{job['title']}")
        print(f"  Source: {job['source']}")
        print(f"  Location: {job['location']}")
        print(f"  Apply: {job['application_url']}")

    return jobs


if __name__ == '__main__':
    asyncio.run(test_agency_scrapers())

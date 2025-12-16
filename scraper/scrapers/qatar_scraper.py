"""
Qatar Airways Taleo Scraper

Qatar Airways uses Taleo (aa115.taleo.net) for their career system.
This scraper handles their specific page structure and extracts detailed
job information including flight hour requirements.
"""

import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class QatarAirwaysScraper:
    """Specialized scraper for Qatar Airways Taleo career site"""

    # Qatar Airways specific URLs
    SEARCH_URL = "https://careers.qatarairways.com/global/SearchJobs/?817=%5B9764%5D&817_format=449&listFilterMode=1"
    TALEO_BASE = "https://aa115.taleo.net/careersection/QA_External_CS/"

    # Pilot-related keywords for filtering
    PILOT_KEYWORDS = [
        'pilot', 'captain', 'first officer', 'f/o', 'fo ', 'second officer',
        'flight crew', 'cockpit', 'atpl', 'type rated', 'a320', 'a330',
        'a350', 'a380', 'b777', 'b787', 'bd700', 'flight operations'
    ]

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    async def fetch_all_jobs(self) -> List[Dict]:
        """Fetch all pilot jobs from Qatar Airways"""
        jobs = []

        print("\n[Qatar Airways] Starting scrape...")

        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False
        ) as client:
            try:
                # Fetch the search results page
                print(f"[Qatar Airways] Fetching: {self.SEARCH_URL}")
                response = await client.get(self.SEARCH_URL)

                if response.status_code != 200:
                    print(f"[Qatar Airways] Failed to load search page: {response.status_code}")
                    return jobs

                # Parse the search results
                job_links = self._extract_job_links(response.text)
                print(f"[Qatar Airways] Found {len(job_links)} job links")

                # Fetch details for each job
                for job_info in job_links:
                    if self._is_pilot_job(job_info['title']):
                        try:
                            detailed_job = await self._fetch_job_details(
                                client,
                                job_info['url'],
                                job_info['title'],
                                job_info.get('location', 'Doha, Qatar')
                            )
                            if detailed_job:
                                jobs.append(detailed_job)
                                print(f"  [+] {detailed_job['title']} - {detailed_job.get('min_total_hours', 'N/A')} hours")

                            # Rate limiting
                            await asyncio.sleep(1)
                        except Exception as e:
                            print(f"  [!] Error fetching job details: {e}")
                            continue

                print(f"[Qatar Airways] Scraped {len(jobs)} pilot jobs")

            except Exception as e:
                print(f"[Qatar Airways] Error: {e}")

        return jobs

    def _extract_job_links(self, html: str) -> List[Dict]:
        """Extract job listing links from search results page"""
        job_links = []
        soup = BeautifulSoup(html, 'html.parser')

        # Qatar's Avature system uses specific class patterns
        # Look for job cards or job list items

        # Pattern 1: Direct links with job titles
        job_elements = soup.find_all('a', href=re.compile(r'(job|requisition|jobdetail)', re.I))

        for elem in job_elements:
            title = elem.get_text(strip=True)
            href = elem.get('href', '')

            if title and len(title) > 5 and href:  # Filter out empty/short links
                # Make URL absolute if needed
                if not href.startswith('http'):
                    if 'taleo.net' in href or href.startswith('/careersection'):
                        href = f"https://aa115.taleo.net{href}"
                    else:
                        href = f"https://careers.qatarairways.com{href}"

                job_links.append({
                    'title': title,
                    'url': href,
                    'location': 'Doha, Qatar'
                })

        # Pattern 2: Look for job cards with nested links
        job_cards = soup.find_all(['div', 'li'], class_=re.compile(r'(job|position|vacancy|result)', re.I))

        for card in job_cards:
            link = card.find('a', href=True)
            if link:
                title = link.get_text(strip=True)
                href = link.get('href', '')

                # Try to find location within the card
                location = 'Doha, Qatar'
                loc_elem = card.find(class_=re.compile(r'location', re.I))
                if loc_elem:
                    location = loc_elem.get_text(strip=True)

                if title and href and {'title': title, 'url': href} not in job_links:
                    if not href.startswith('http'):
                        href = f"https://careers.qatarairways.com{href}"

                    job_links.append({
                        'title': title,
                        'url': href,
                        'location': location
                    })

        # Deduplicate
        seen = set()
        unique_links = []
        for job in job_links:
            key = (job['title'], job['url'])
            if key not in seen:
                seen.add(key)
                unique_links.append(job)

        return unique_links

    async def _fetch_job_details(self, client: httpx.AsyncClient, url: str, title: str, location: str) -> Optional[Dict]:
        """Fetch detailed job information from job detail page"""

        # Build the Taleo job detail URL if we have a job ID
        job_id_match = re.search(r'job[=/](\d+[A-Z0-9]*)', url, re.I)
        if job_id_match:
            job_id = job_id_match.group(1)
            detail_url = f"{self.TALEO_BASE}jobdetail.ftl?job={job_id}"
        else:
            detail_url = url

        try:
            response = await client.get(detail_url)
            if response.status_code != 200:
                # Try original URL
                response = await client.get(url)
                if response.status_code != 200:
                    return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract description
            description = ''
            desc_selectors = [
                '#jobDescription', '.jobDescription', '[id*="Description"]',
                '.job-description', '.requisition-description', '.content-block'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break

            # If no description found, try getting all text
            if not description:
                main_content = soup.find('main') or soup.find('body')
                if main_content:
                    description = main_content.get_text(' ', strip=True)[:5000]

            # Build job dict
            job = {
                'title': title,
                'company': 'Qatar Airways',
                'location': location,
                'region': 'middle_east',
                'application_url': url,
                'source': 'Direct - Qatar Airways Taleo',
                'description': description[:5000] if description else '',
                'date_scraped': datetime.now().isoformat(),
                'is_active': True,
                'visa_sponsorship': True,  # Qatar typically sponsors
                'contract_type': 'permanent',
            }

            # Extract requirements from description
            job = self._extract_requirements(job)

            return job

        except Exception as e:
            print(f"  [!] Error fetching {url}: {e}")
            return None

    def _extract_requirements(self, job: Dict) -> Dict:
        """Extract flight hours and other requirements from job description"""
        description = job.get('description', '').lower()

        # Extract total hours - multiple patterns
        hours_patterns = [
            r'minimum\s*(?:of\s*)?(\d{1,2}[,.]?\d{3})\s*(?:total\s*)?(?:flight\s*)?hours',
            r'(\d{1,2}[,.]?\d{3})\s*(?:total\s*)?(?:flight\s*)?hours?\s*(?:minimum|min)',
            r'(\d{1,2}[,.]?\d{3})\+?\s*hours?\s*(?:total|tt|flight)',
            r'total\s*(?:flight\s*)?(?:time|hours?)[:\s]*(\d{1,2}[,.]?\d{3})',
            r'(\d{3,5})\s*hours?\s*(?:on\s*)?(?:multi|jet|type)',
        ]

        for pattern in hours_patterns:
            match = re.search(pattern, description)
            if match:
                hours_str = match.group(1).replace(',', '').replace('.', '')
                try:
                    hours = int(hours_str)
                    if 100 <= hours <= 30000:  # Sanity check
                        job['min_total_hours'] = hours
                        break
                except ValueError:
                    pass

        # Extract PIC hours
        pic_patterns = [
            r'(\d{1,2}[,.]?\d{3})\s*(?:hours?\s*)?(?:pic|command|p\.?i\.?c)',
            r'(?:pic|command)[:\s]*(\d{1,2}[,.]?\d{3})',
        ]

        for pattern in pic_patterns:
            match = re.search(pattern, description)
            if match:
                hours_str = match.group(1).replace(',', '').replace('.', '')
                try:
                    hours = int(hours_str)
                    if 50 <= hours <= 20000:
                        job['min_pic_hours'] = hours
                        break
                except ValueError:
                    pass

        # Determine position type from title and description
        # Valid values: captain, first_officer, second_officer, cadet, instructor, other
        title_lower = job.get('title', '').lower()
        if 'captain' in title_lower or 'command' in title_lower:
            job['position_type'] = 'captain'
        elif 'first officer' in title_lower or 'f/o' in title_lower:
            job['position_type'] = 'first_officer'
        elif 'second officer' in title_lower or 's/o' in title_lower:
            job['position_type'] = 'second_officer'
        elif 'cadet' in title_lower or 'trainee' in title_lower:
            job['position_type'] = 'cadet'
        elif 'instructor' in title_lower or 'tre' in title_lower or 'tri' in title_lower:
            job['position_type'] = 'instructor'
        else:
            # Default to first_officer for generic pilot positions, or 'other' for non-flying
            if 'roadshow' in title_lower or 'event' in title_lower:
                job['position_type'] = 'other'
            else:
                job['position_type'] = 'first_officer'

        # Extract aircraft types
        aircraft_patterns = [
            r'(a320|a321|a319|a318)',
            r'(a330|a340)',
            r'(a350)',
            r'(a380)',
            r'(b737|737ng|737\s*max)',
            r'(b777|777)',
            r'(b787|787)',
            r'(bd700|global\s*\d+|gulfstream)',
        ]

        aircraft_types = []
        for pattern in aircraft_patterns:
            matches = re.findall(pattern, description)
            aircraft_types.extend(matches)

        # Also check title
        for pattern in aircraft_patterns:
            matches = re.findall(pattern, title_lower)
            aircraft_types.extend(matches)

        if aircraft_types:
            # Clean up and deduplicate
            cleaned = []
            for t in aircraft_types:
                t = t.upper().replace(' ', '')
                if t not in cleaned:
                    cleaned.append(t)
            job['aircraft_type'] = ', '.join(cleaned)

        # Type rating required/provided
        if any(phrase in description for phrase in ['type rating required', 'type rated', 'current type rating', 'must hold type']):
            job['type_rating_required'] = True
        else:
            job['type_rating_required'] = False

        if any(phrase in description for phrase in ['type rating provided', 'will provide type', 'type conversion']):
            job['type_rating_provided'] = True
        else:
            job['type_rating_provided'] = False

        # Entry level determination - CONSERVATIVE approach
        # Only mark as entry level if explicitly low hours or cadet
        is_cadet = job.get('position_type') == 'cadet'
        has_low_hours = job.get('min_total_hours') and job['min_total_hours'] < 500
        is_type_provided_non_captain = job.get('type_rating_provided') and job.get('position_type') != 'captain'

        job['is_entry_level'] = is_cadet or has_low_hours or is_type_provided_non_captain

        return job

    def _is_pilot_job(self, title: str) -> bool:
        """Check if job title indicates a pilot position"""
        if not title:
            return False
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in self.PILOT_KEYWORDS)


async def test_qatar_scraper():
    """Test the Qatar Airways scraper"""
    scraper = QatarAirwaysScraper()
    jobs = await scraper.fetch_all_jobs()

    print(f"\n{'='*60}")
    print(f"Qatar Airways Scraper Results")
    print(f"{'='*60}")
    print(f"Total pilot jobs found: {len(jobs)}")

    for job in jobs:
        print(f"\n{job['title']}")
        print(f"  Location: {job['location']}")
        print(f"  Position: {job.get('position_type', 'N/A')}")
        print(f"  Aircraft: {job.get('aircraft_type', 'N/A')}")
        print(f"  Min Hours: {job.get('min_total_hours', 'Not Specified')}")
        print(f"  Entry Level: {job.get('is_entry_level', False)}")
        print(f"  Apply: {job['application_url']}")

    return jobs


if __name__ == '__main__':
    asyncio.run(test_qatar_scraper())

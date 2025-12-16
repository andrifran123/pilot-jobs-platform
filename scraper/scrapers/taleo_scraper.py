"""
Universal Taleo ATS Scraper

Taleo is used by major airlines including:
- Emirates, Etihad, Qatar Airways
- British Airways, Air France, KLM, Lufthansa
- Singapore Airlines, Cathay Pacific

Taleo has several versions:
1. Taleo Enterprise (Oracle Taleo) - Modern cloud version
2. Taleo Business Edition - Smaller companies
3. Legacy Taleo - Older implementations

Common URL patterns:
- https://careers.example.com/careersection/external/jobsearch.ftl
- https://example.taleo.net/careersection/jobdetail.ftl
- https://tas-example.taleo.net/careersection/
"""

import asyncio
import re
import json
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class TaleoScraper:
    """Universal scraper for Taleo-based career sites"""

    # Common Taleo selectors and patterns
    TALEO_PATTERNS = {
        'job_list_table': ['table.datarow', '#requisitionListInterface', '.requisition-list'],
        'job_row': ['tr.datarow', '.requisitionList tr', '.job-posting'],
        'job_title': ['.titlelink', '.jobTitle', '.requisitionTitle', 'a[id*="requisitionTitle"]'],
        'job_location': ['.location', '.jobLocation', '[id*="location"]'],
        'job_date': ['.date', '.postingDate', '[id*="PostedDate"]'],
        'job_id': ['[id*="requisitionId"]', '.reqId'],
        'pagination': ['.pagingControls', '.requisitionPaging', '#requisitionListNavFooter'],
        'next_page': ['a[id*="next"]', '.nextLink', 'a:contains("Next")'],
    }

    # Keywords to identify pilot jobs
    PILOT_KEYWORDS = [
        'pilot', 'captain', 'first officer', 'f/o', 'fo ', 'co-pilot',
        'second officer', 'cruise pilot', 'relief pilot', 'training captain',
        'line captain', 'senior first officer', 'direct entry', 'cadet',
        'type rating', 'flight crew', 'cockpit crew', 'flight deck',
        'a320', 'a330', 'a350', 'a380', 'b737', 'b747', 'b777', 'b787',
        'boeing', 'airbus', 'embraer', 'bombardier', 'atr', 'crj', 'erj',
        'flight operations', 'atpl', 'cpl', 'mpl'
    ]

    def __init__(self, use_proxy: bool = False, proxy_url: Optional[str] = None):
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.session_cookies = {}

    async def fetch_jobs(self, airline_config: Dict) -> List[Dict]:
        """
        Fetch all pilot jobs from a Taleo career site

        Args:
            airline_config: Dict with 'name', 'careers_url', 'region', etc.

        Returns:
            List of job dictionaries
        """
        jobs = []
        base_url = airline_config.get('careers_url', '')
        airline_name = airline_config.get('name', 'Unknown')

        print(f"\n[Taleo] Scraping {airline_name}...")
        print(f"[Taleo] URL: {base_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }

        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False  # Some airline sites have cert issues
        ) as client:
            try:
                # First, get the main careers page to establish session
                response = await client.get(base_url)

                if response.status_code != 200:
                    print(f"[Taleo] Failed to load page: {response.status_code}")
                    return jobs

                html = response.text

                # Detect Taleo version and extract jobs accordingly
                if self._is_taleo_enterprise(html):
                    jobs = await self._parse_taleo_enterprise(html, base_url, airline_config, client)
                elif self._is_taleo_legacy(html):
                    jobs = await self._parse_taleo_legacy(html, base_url, airline_config, client)
                else:
                    # Try generic parsing
                    jobs = await self._parse_generic_taleo(html, base_url, airline_config, client)

                # Try Taleo API if HTML parsing found nothing
                if not jobs:
                    jobs = await self._try_taleo_api(base_url, airline_config, client)

                print(f"[Taleo] Found {len(jobs)} pilot jobs at {airline_name}")

            except httpx.TimeoutException:
                print(f"[Taleo] Timeout scraping {airline_name}")
            except Exception as e:
                print(f"[Taleo] Error scraping {airline_name}: {str(e)}")

        return jobs

    def _is_taleo_enterprise(self, html: str) -> bool:
        """Check if page is Taleo Enterprise (modern Oracle cloud)"""
        indicators = [
            'requisitionListInterface',
            'taleo.net',
            'Oracle Taleo',
            'careersection',
            'requisitionList',
        ]
        return any(indicator in html for indicator in indicators)

    def _is_taleo_legacy(self, html: str) -> bool:
        """Check if page is legacy Taleo"""
        indicators = [
            'jobdetail.ftl',
            'jobsearch.ftl',
            'TBE_the498',
            'taleo_',
        ]
        return any(indicator in html for indicator in indicators)

    async def _parse_taleo_enterprise(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Parse Taleo Enterprise/Oracle Cloud career sites"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Look for job listings in various Taleo table formats
        job_elements = []

        # Try different selectors
        for selector in ['tr[id*="requisition"]', 'tr.datarow', '.job-listing', '.requisition-row']:
            job_elements = soup.select(selector)
            if job_elements:
                break

        # Also try finding job links directly
        if not job_elements:
            job_links = soup.find_all('a', href=re.compile(r'(jobdetail|requisition|job/)', re.I))
            for link in job_links:
                title = link.get_text(strip=True)
                if self._is_pilot_job(title):
                    job_url = link.get('href', '')
                    if not job_url.startswith('http'):
                        job_url = self._make_absolute_url(base_url, job_url)

                    job = await self._extract_job_details(job_url, title, airline_config, client)
                    if job:
                        jobs.append(job)
            return jobs

        for element in job_elements:
            try:
                # Extract title
                title_elem = element.select_one('a[id*="Title"], .titlelink, .jobTitle, a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                if not self._is_pilot_job(title):
                    continue

                # Extract URL
                job_url = title_elem.get('href', '')
                if not job_url.startswith('http'):
                    job_url = self._make_absolute_url(base_url, job_url)

                # Extract location
                location = ''
                loc_elem = element.select_one('[id*="location"], .location, td:nth-child(2)')
                if loc_elem:
                    location = loc_elem.get_text(strip=True)

                # Extract date
                date_posted = ''
                date_elem = element.select_one('[id*="Date"], .date, td:nth-child(3)')
                if date_elem:
                    date_posted = date_elem.get_text(strip=True)

                # Build job dict
                job = {
                    'title': title,
                    'company': airline_config.get('name', ''),
                    'location': location or airline_config.get('headquarters', ''),
                    'region': airline_config.get('region', ''),
                    'application_url': job_url,
                    'source': 'Taleo',
                    'date_posted': date_posted,
                    'date_scraped': datetime.now().isoformat(),
                    'is_active': True,
                }

                # Try to get more details from job page
                detailed_job = await self._fetch_job_details(job_url, job, client)
                jobs.append(detailed_job if detailed_job else job)

            except Exception as e:
                print(f"[Taleo] Error parsing job element: {e}")
                continue

        # Handle pagination
        next_page = soup.select_one('a[id*="next"], .nextLink')
        if next_page and next_page.get('href'):
            next_url = self._make_absolute_url(base_url, next_page.get('href'))
            # Recursively get next page (with limit)
            if len(jobs) < 100:  # Safety limit
                try:
                    response = await client.get(next_url)
                    if response.status_code == 200:
                        more_jobs = await self._parse_taleo_enterprise(
                            response.text, next_url, airline_config, client
                        )
                        jobs.extend(more_jobs)
                except Exception:
                    pass

        return jobs

    async def _parse_taleo_legacy(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Parse legacy Taleo sites"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Legacy Taleo often uses tables with specific class names
        job_rows = soup.select('table.datarow tr, .jobSearchResultsTable tr')

        for row in job_rows:
            try:
                title_link = row.select_one('a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                if not self._is_pilot_job(title):
                    continue

                job_url = title_link.get('href', '')
                if not job_url.startswith('http'):
                    job_url = self._make_absolute_url(base_url, job_url)

                # Extract other fields from table cells
                cells = row.find_all('td')
                location = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                date_posted = cells[2].get_text(strip=True) if len(cells) > 2 else ''

                job = {
                    'title': title,
                    'company': airline_config.get('name', ''),
                    'location': location or airline_config.get('headquarters', ''),
                    'region': airline_config.get('region', ''),
                    'application_url': job_url,
                    'source': 'Taleo',
                    'date_posted': date_posted,
                    'date_scraped': datetime.now().isoformat(),
                    'is_active': True,
                }

                jobs.append(job)

            except Exception:
                continue

        return jobs

    async def _parse_generic_taleo(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Generic parsing for unknown Taleo variants"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find all links that might be job postings
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # Check if it looks like a job link
            job_indicators = ['job', 'requisition', 'position', 'career', 'opening']
            if not any(ind in href.lower() for ind in job_indicators):
                continue

            if not self._is_pilot_job(title):
                continue

            job_url = href if href.startswith('http') else self._make_absolute_url(base_url, href)

            job = {
                'title': title,
                'company': airline_config.get('name', ''),
                'location': airline_config.get('headquarters', ''),
                'region': airline_config.get('region', ''),
                'application_url': job_url,
                'source': 'Taleo',
                'date_posted': '',
                'date_scraped': datetime.now().isoformat(),
                'is_active': True,
            }

            jobs.append(job)

        return jobs

    async def _try_taleo_api(self, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Try to access Taleo REST API directly"""
        jobs = []

        # Common Taleo API endpoints
        api_patterns = [
            '/careersection/rest/jobboard/searchjobs',
            '/careersection/rest/jobboard/jobs',
            '/api/recruiting/v1/jobs',
            '/services/rest/talent/v2/jobs',
        ]

        # Extract base domain
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        for api_pattern in api_patterns:
            api_url = f"{base_domain}{api_pattern}"

            try:
                # Try POST with search params
                search_payload = {
                    'keywords': 'pilot',
                    'pageSize': 100,
                    'pageNumber': 1,
                }

                response = await client.post(
                    api_url,
                    json=search_payload,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Parse API response
                        job_list = data.get('jobs', data.get('requisitions', data.get('results', [])))

                        for job_data in job_list:
                            title = job_data.get('title', job_data.get('jobTitle', ''))
                            if self._is_pilot_job(title):
                                job = {
                                    'title': title,
                                    'company': airline_config.get('name', ''),
                                    'location': job_data.get('location', job_data.get('primaryLocation', '')),
                                    'region': airline_config.get('region', ''),
                                    'application_url': job_data.get('applyUrl', job_data.get('url', base_url)),
                                    'source': 'Taleo API',
                                    'description': job_data.get('description', job_data.get('jobDescription', '')),
                                    'date_posted': job_data.get('postedDate', ''),
                                    'date_scraped': datetime.now().isoformat(),
                                    'is_active': True,
                                }
                                jobs.append(job)

                        if jobs:
                            print(f"[Taleo] Found {len(jobs)} jobs via API")
                            return jobs

                    except json.JSONDecodeError:
                        continue

            except Exception:
                continue

        return jobs

    async def _fetch_job_details(self, job_url: str, job: Dict, client: httpx.AsyncClient) -> Optional[Dict]:
        """Fetch additional details from job detail page"""
        try:
            response = await client.get(job_url)
            if response.status_code != 200:
                return job

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract description
            desc_selectors = [
                '.jobdescription', '#jobDescription', '.description',
                '[id*="jobDescription"]', '.requisition-description'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    job['description'] = desc_elem.get_text(strip=True)[:5000]  # Limit length
                    break

            # Extract requirements from description
            if job.get('description'):
                job = self._extract_requirements(job)

            # Try to find specific requirement fields
            req_selectors = [
                '[id*="qualification"]', '[id*="requirement"]',
                '.qualifications', '.requirements'
            ]
            for selector in req_selectors:
                req_elem = soup.select_one(selector)
                if req_elem:
                    req_text = req_elem.get_text(strip=True)
                    if 'description' in job:
                        job['description'] += '\n\nRequirements: ' + req_text
                    break

            return job

        except Exception:
            return job

    async def _extract_job_details(self, job_url: str, title: str, airline_config: Dict, client: httpx.AsyncClient) -> Optional[Dict]:
        """Extract full job details from a job URL"""
        job = {
            'title': title,
            'company': airline_config.get('name', ''),
            'location': airline_config.get('headquarters', ''),
            'region': airline_config.get('region', ''),
            'application_url': job_url,
            'source': 'Taleo',
            'date_scraped': datetime.now().isoformat(),
            'is_active': True,
        }

        return await self._fetch_job_details(job_url, job, client)

    def _is_pilot_job(self, title: str) -> bool:
        """Check if job title indicates a pilot position"""
        if not title:
            return False
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in self.PILOT_KEYWORDS)

    def _make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """Convert relative URL to absolute"""
        from urllib.parse import urljoin
        return urljoin(base_url, relative_url)

    def _extract_requirements(self, job: Dict) -> Dict:
        """Extract flight hour requirements and other details from description"""
        description = job.get('description', '').lower()

        # Extract total hours
        hours_patterns = [
            r'(\d{1,2}[,.]?\d{3})\s*(?:total\s*)?(?:flight\s*)?hours',
            r'minimum\s*(?:of\s*)?(\d{1,2}[,.]?\d{3})\s*hours',
            r'(\d{1,2}[,.]?\d{3})\+?\s*hours?\s*(?:total|tt|flight)',
        ]

        for pattern in hours_patterns:
            match = re.search(pattern, description)
            if match:
                hours_str = match.group(1).replace(',', '').replace('.', '')
                try:
                    job['min_total_hours'] = int(hours_str)
                    break
                except ValueError:
                    pass

        # Extract PIC hours
        pic_patterns = [
            r'(\d{1,2}[,.]?\d{3})\s*(?:pic|command)\s*hours',
            r'pic[:\s]*(\d{1,2}[,.]?\d{3})',
        ]

        for pattern in pic_patterns:
            match = re.search(pattern, description)
            if match:
                hours_str = match.group(1).replace(',', '').replace('.', '')
                try:
                    job['min_pic_hours'] = int(hours_str)
                    break
                except ValueError:
                    pass

        # Check for type rating requirement
        type_rating_phrases = [
            'type rating required', 'type rated', 'current type rating',
            'must hold type rating', 'valid type rating'
        ]
        job['type_rating_required'] = any(phrase in description for phrase in type_rating_phrases)

        # Check if type rating is provided
        type_provided_phrases = [
            'type rating provided', 'type rating offered', 'will provide type rating',
            'type conversion', 'type training provided'
        ]
        job['type_rating_provided'] = any(phrase in description for phrase in type_provided_phrases)

        # Extract license requirements
        license_patterns = [
            r'(easa|faa|icao|uk caa)[\s-]*(atpl|cpl|mpl)',
            r'(atpl|cpl|mpl)[\s/]*(frozen|f)?',
        ]

        licenses = []
        for pattern in license_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if isinstance(match, tuple):
                    licenses.append(' '.join(match).upper().strip())
                else:
                    licenses.append(match.upper())

        if licenses:
            job['license_required'] = ', '.join(set(licenses))

        # Detect position type
        if 'captain' in description or 'command' in description:
            job['position_type'] = 'captain'
        elif 'first officer' in description or 'f/o' in description or 'copilot' in description:
            job['position_type'] = 'first_officer'
        elif 'cadet' in description or 'trainee' in description or 'ab initio' in description:
            job['position_type'] = 'cadet'
        elif 'instructor' in description or 'tri' in description or 'tre' in description:
            job['position_type'] = 'instructor'
        else:
            job['position_type'] = 'other'

        # Extract aircraft type
        aircraft_patterns = [
            r'(a320|a321|a319|a318|a330|a340|a350|a380)',
            r'(b737|b738|b739|737ng|737max|b747|b757|b767|b777|b787)',
            r'(crj\d{3}|erj\d{3}|e\d{3}|embraer\s*\d{3})',
            r'(atr\s*\d{2}|dash\s*8|q\d{3}|bombardier)',
        ]

        aircraft_types = []
        for pattern in aircraft_patterns:
            matches = re.findall(pattern, description)
            aircraft_types.extend(matches)

        if aircraft_types:
            job['aircraft_type'] = ', '.join(set(t.upper() for t in aircraft_types))

        return job


async def test_taleo_scraper():
    """Test the Taleo scraper with sample airlines"""
    scraper = TaleoScraper()

    # Test airlines using Taleo
    test_airlines = [
        {
            'name': 'Emirates',
            'careers_url': 'https://www.emiratesgroupcareers.com/search-and-apply/',
            'region': 'middle_east',
            'headquarters': 'Dubai, UAE',
        },
        {
            'name': 'British Airways',
            'careers_url': 'https://careers.ba.com/jobs',
            'region': 'europe',
            'headquarters': 'London, UK',
        },
    ]

    all_jobs = []
    for airline in test_airlines:
        jobs = await scraper.fetch_jobs(airline)
        all_jobs.extend(jobs)
        await asyncio.sleep(2)  # Be respectful between requests

    print(f"\n{'='*60}")
    print(f"Total pilot jobs found: {len(all_jobs)}")
    print(f"{'='*60}")

    for job in all_jobs[:10]:  # Show first 10
        print(f"\n{job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Apply: {job['application_url']}")
        if job.get('min_total_hours'):
            print(f"  Min Hours: {job['min_total_hours']}")
        if job.get('type_rating_required'):
            print(f"  Type Rating Required: Yes")

    return all_jobs


if __name__ == '__main__':
    asyncio.run(test_taleo_scraper())

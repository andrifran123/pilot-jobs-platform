"""
Universal Workday ATS Scraper

Workday is used by many major airlines:
- Qatar Airways, Singapore Airlines, Cathay Pacific
- Lufthansa Group, SWISS, Qantas, etc.

Workday has a consistent API structure across all implementations.
"""

import asyncio
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

class WorkdayScraperError(Exception):
    pass

class WorkdayScraper:
    """
    Scrapes job listings from Workday-based career sites.

    Workday sites have a predictable structure:
    1. They use a JSON API for job listings
    2. Job details are available at /job/{job-id}
    3. Apply links go to the actual application page
    """

    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_jobs(self, airline_config: Dict) -> List[Dict]:
        """
        Fetch all pilot jobs from a Workday career site.

        Args:
            airline_config: Dict with 'name', 'workday_url', 'region', 'country'

        Returns:
            List of job dictionaries
        """
        jobs = []
        airline_name = airline_config['name']
        base_url = airline_config.get('workday_url', '')

        if not base_url:
            print(f"[{airline_name}] No Workday URL configured")
            return jobs

        print(f"[{airline_name}] Scraping Workday jobs...")

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True,
            proxy=self.proxy
        ) as client:
            try:
                # First, get the main page to find the API endpoint
                response = await client.get(base_url)
                response.raise_for_status()

                # Look for Workday's embedded job data
                html = response.text
                jobs = await self._parse_workday_response(
                    html,
                    base_url,
                    airline_config,
                    client
                )

            except httpx.HTTPStatusError as e:
                print(f"[{airline_name}] HTTP error: {e.response.status_code}")
            except Exception as e:
                print(f"[{airline_name}] Error: {str(e)}")

        print(f"[{airline_name}] Found {len(jobs)} pilot jobs")
        return jobs

    async def _parse_workday_response(
        self,
        html: str,
        base_url: str,
        airline_config: Dict,
        client: httpx.AsyncClient
    ) -> List[Dict]:
        """Parse Workday HTML/JSON response for job listings"""
        jobs = []
        airline_name = airline_config['name']

        # Method 1: Look for embedded JSON data
        json_pattern = r'window\.__INITIAL_DATA__\s*=\s*({.*?});'
        match = re.search(json_pattern, html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))
                jobs = self._extract_jobs_from_json(data, airline_config, base_url)
                return jobs
            except json.JSONDecodeError:
                pass

        # Method 2: Parse HTML directly
        soup = BeautifulSoup(html, 'lxml')

        # Common Workday job listing patterns
        job_cards = soup.select('[data-automation-id="jobTitle"]')
        if not job_cards:
            job_cards = soup.select('.css-19uc56f')  # Another common class
        if not job_cards:
            job_cards = soup.select('a[href*="/job/"]')

        for card in job_cards:
            try:
                job = self._parse_job_card(card, airline_config, base_url)
                if job and self._is_pilot_job(job.get('title', '')):
                    jobs.append(job)
            except Exception as e:
                continue

        # Method 3: Try the Workday API directly
        if not jobs:
            api_jobs = await self._try_workday_api(base_url, airline_config, client)
            jobs.extend(api_jobs)

        return jobs

    async def _try_workday_api(
        self,
        base_url: str,
        airline_config: Dict,
        client: httpx.AsyncClient
    ) -> List[Dict]:
        """Try to hit Workday's internal API"""
        jobs = []

        # Workday API patterns
        api_patterns = [
            f"{base_url}/wday/cxs/search",
            f"{base_url}/fs/searchPagination/jobs",
            base_url.replace('/search-results', '/wday/cxs/search'),
        ]

        for api_url in api_patterns:
            try:
                # Common payload for Workday search
                payload = {
                    "appliedFacets": {},
                    "limit": 50,
                    "offset": 0,
                    "searchText": "pilot"
                }

                response = await client.post(
                    api_url,
                    json=payload,
                    headers={**self.headers, 'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    data = response.json()
                    jobs = self._extract_jobs_from_api_response(data, airline_config, base_url)
                    if jobs:
                        break
            except Exception:
                continue

        return jobs

    def _extract_jobs_from_json(self, data: Dict, airline_config: Dict, base_url: str) -> List[Dict]:
        """Extract jobs from embedded JSON data"""
        jobs = []

        # Navigate common Workday JSON structures
        job_postings = []

        if 'jobPostings' in data:
            job_postings = data['jobPostings']
        elif 'jobs' in data:
            job_postings = data['jobs']
        elif 'searchResults' in data:
            job_postings = data['searchResults']

        for posting in job_postings:
            try:
                title = posting.get('title', posting.get('jobTitle', ''))

                if not self._is_pilot_job(title):
                    continue

                job = {
                    'title': title,
                    'company': airline_config['name'],
                    'location': posting.get('location', posting.get('primaryLocation', '')),
                    'region': airline_config.get('region', ''),
                    'country': airline_config.get('country', ''),
                    'job_id': posting.get('id', posting.get('jobId', '')),
                    'description': posting.get('description', posting.get('jobDescription', '')),
                    'posted_date': posting.get('postedDate', posting.get('datePosted', '')),
                    'application_url': self._build_application_url(posting, base_url),
                    'source': 'Workday',
                    'scraped_at': datetime.utcnow().isoformat(),
                }

                # Extract requirements if available
                job.update(self._extract_requirements(posting))

                jobs.append(job)
            except Exception:
                continue

        return jobs

    def _extract_jobs_from_api_response(self, data: Dict, airline_config: Dict, base_url: str) -> List[Dict]:
        """Extract jobs from Workday API response"""
        jobs = []

        job_postings = data.get('jobPostings', data.get('jobs', []))

        for posting in job_postings:
            try:
                title = posting.get('title', '')

                if not self._is_pilot_job(title):
                    continue

                # Build the actual application URL
                external_path = posting.get('externalPath', '')
                if external_path:
                    # Workday URLs are relative
                    base = base_url.split('/search')[0] if '/search' in base_url else base_url
                    application_url = f"{base}{external_path}"
                else:
                    application_url = base_url

                job = {
                    'title': title,
                    'company': airline_config['name'],
                    'location': self._extract_location(posting),
                    'region': airline_config.get('region', ''),
                    'country': airline_config.get('country', ''),
                    'job_id': posting.get('bulletFields', [{}])[0] if posting.get('bulletFields') else '',
                    'description': posting.get('descriptionSummary', ''),
                    'posted_date': posting.get('postedOn', ''),
                    'application_url': application_url,
                    'source': 'Workday API',
                    'scraped_at': datetime.utcnow().isoformat(),
                }

                jobs.append(job)
            except Exception:
                continue

        return jobs

    def _parse_job_card(self, card, airline_config: Dict, base_url: str) -> Optional[Dict]:
        """Parse a single job card element"""
        try:
            # Get job title
            title_elem = card.select_one('[data-automation-id="jobTitle"]') or card
            title = title_elem.get_text(strip=True)

            # Get job URL
            link = card.get('href') or card.find_parent('a').get('href', '')
            if link and not link.startswith('http'):
                base = base_url.split('/search')[0] if '/search' in base_url else base_url.rsplit('/', 1)[0]
                link = f"{base}{link}"

            # Get location
            location_elem = card.find_next('[data-automation-id="jobLocation"]')
            location = location_elem.get_text(strip=True) if location_elem else ''

            return {
                'title': title,
                'company': airline_config['name'],
                'location': location,
                'region': airline_config.get('region', ''),
                'country': airline_config.get('country', ''),
                'application_url': link,
                'source': 'Workday HTML',
                'scraped_at': datetime.utcnow().isoformat(),
            }
        except Exception:
            return None

    def _build_application_url(self, posting: Dict, base_url: str) -> str:
        """Build the actual application URL from job posting data"""
        # Check for direct application URL
        if 'applyUrl' in posting:
            return posting['applyUrl']
        if 'applicationUrl' in posting:
            return posting['applicationUrl']

        # Build from job ID
        job_id = posting.get('id', posting.get('jobId', ''))
        if job_id:
            base = base_url.split('/search')[0] if '/search' in base_url else base_url
            return f"{base}/job/{job_id}"

        return base_url

    def _extract_location(self, posting: Dict) -> str:
        """Extract location from various possible fields"""
        if 'locationsText' in posting:
            return posting['locationsText']
        if 'primaryLocation' in posting:
            return posting['primaryLocation']
        if 'location' in posting:
            if isinstance(posting['location'], dict):
                return posting['location'].get('name', '')
            return posting['location']
        return ''

    def _extract_requirements(self, posting: Dict) -> Dict:
        """Extract hour requirements and other qualifications"""
        requirements = {}
        description = posting.get('description', '') + ' ' + posting.get('qualifications', '')
        description = description.lower()

        # Extract hour requirements using regex
        hour_patterns = [
            (r'(\d{1,5})\s*(?:hours?|hrs?)\s*(?:total|tt)', 'min_total_hours'),
            (r'minimum\s*(?:of\s*)?(\d{1,5})\s*(?:hours?|hrs?)', 'min_total_hours'),
            (r'(\d{1,5})\s*(?:hours?|hrs?)\s*(?:pic|command)', 'min_pic_hours'),
            (r'(\d{1,5})\s*(?:hours?|hrs?)\s*(?:on\s*type|type)', 'min_type_hours'),
        ]

        for pattern, field in hour_patterns:
            match = re.search(pattern, description)
            if match:
                try:
                    requirements[field] = int(match.group(1))
                except ValueError:
                    pass

        # Check for type rating requirement
        type_rating_patterns = [
            r'type\s*rat(?:ed|ing)\s*required',
            r'must\s*have.*type\s*rat',
            r'current\s*type\s*rat',
        ]

        requirements['type_rating_required'] = any(
            re.search(p, description) for p in type_rating_patterns
        )

        # Check if type rating is provided
        provided_patterns = [
            r'type\s*rat(?:ed|ing).*provided',
            r'training\s*provided',
            r'will\s*provide\s*type',
        ]

        requirements['type_rating_provided'] = any(
            re.search(p, description) for p in provided_patterns
        )

        return requirements

    def _is_pilot_job(self, title: str) -> bool:
        """Check if job title is pilot-related"""
        title_lower = title.lower()

        pilot_keywords = [
            'pilot', 'captain', 'first officer', 'f/o', 'fo ',
            'second officer', 'cruise pilot', 'flight crew',
            'cadet', 'co-pilot', 'copilot', 'flight operations',
            'type rated', 'direct entry'
        ]

        # Exclude non-flying roles
        exclude_keywords = [
            'drone', 'simulator', 'instructor only', 'ground',
            'dispatcher', 'coordinator', 'manager', 'admin'
        ]

        has_pilot_keyword = any(kw in title_lower for kw in pilot_keywords)
        has_exclude_keyword = any(kw in title_lower for kw in exclude_keywords)

        return has_pilot_keyword and not has_exclude_keyword


# ============================================================
# Main execution
# ============================================================

async def scrape_all_workday_airlines():
    """Scrape all airlines using Workday ATS"""
    from airline_sources import WORKDAY_AIRLINES

    scraper = WorkdayScraper()
    all_jobs = []

    for airline_key, config in WORKDAY_AIRLINES.items():
        try:
            jobs = await scraper.fetch_jobs(config)
            all_jobs.extend(jobs)
            await asyncio.sleep(2)  # Be polite between requests
        except Exception as e:
            print(f"Error scraping {airline_key}: {e}")

    return all_jobs


if __name__ == "__main__":
    jobs = asyncio.run(scrape_all_workday_airlines())
    print(f"\nTotal jobs found: {len(jobs)}")

    for job in jobs[:5]:
        print(f"\n{job['title']} at {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Apply: {job['application_url']}")

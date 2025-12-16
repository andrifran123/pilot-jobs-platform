"""
Universal SAP SuccessFactors ATS Scraper

SuccessFactors is used by airlines including:
- Lufthansa Group (Lufthansa, Swiss, Austrian, Brussels, Eurowings)
- SAS Scandinavian Airlines
- Finnair
- Norwegian
- Many Asian carriers

Common URL patterns:
- https://jobs.sap.com/search/
- https://careers.example.com/jobs
- https://performancemanager.successfactors.eu/career
- https://example.successfactors.com/career
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


class SuccessfactorsScraper:
    """Universal scraper for SAP SuccessFactors career sites"""

    # Keywords to identify pilot jobs
    PILOT_KEYWORDS = [
        'pilot', 'captain', 'first officer', 'f/o', 'fo ', 'co-pilot',
        'second officer', 'cruise pilot', 'relief pilot', 'training captain',
        'line captain', 'senior first officer', 'direct entry', 'cadet',
        'type rating', 'flight crew', 'cockpit crew', 'flight deck',
        'a320', 'a330', 'a350', 'a380', 'b737', 'b747', 'b777', 'b787',
        'boeing', 'airbus', 'embraer', 'bombardier', 'atr', 'crj', 'erj',
        'flight operations', 'atpl', 'cpl', 'mpl', 'flugkapitän', 'copilot',
        'flygkapten', 'styrman', 'pilote', 'commandant de bord'
    ]

    def __init__(self, use_proxy: bool = False, proxy_url: Optional[str] = None):
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url

    async def fetch_jobs(self, airline_config: Dict) -> List[Dict]:
        """
        Fetch all pilot jobs from a SuccessFactors career site

        Args:
            airline_config: Dict with 'name', 'careers_url', 'region', etc.

        Returns:
            List of job dictionaries
        """
        jobs = []
        base_url = airline_config.get('careers_url', '')
        airline_name = airline_config.get('name', 'Unknown')

        print(f"\n[SF] Scraping {airline_name}...")
        print(f"[SF] URL: {base_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False
        ) as client:
            try:
                response = await client.get(base_url)

                if response.status_code != 200:
                    print(f"[SF] Failed to load page: {response.status_code}")
                    return jobs

                html = response.text

                # Try different parsing strategies
                if self._is_sf_recruiting(html):
                    jobs = await self._parse_sf_recruiting(html, base_url, airline_config, client)
                elif self._is_sf_career_site(html):
                    jobs = await self._parse_sf_career_site(html, base_url, airline_config, client)
                else:
                    jobs = await self._parse_generic_sf(html, base_url, airline_config, client)

                # Try SuccessFactors API
                if not jobs:
                    jobs = await self._try_sf_api(base_url, airline_config, client)

                print(f"[SF] Found {len(jobs)} pilot jobs at {airline_name}")

            except httpx.TimeoutException:
                print(f"[SF] Timeout scraping {airline_name}")
            except Exception as e:
                print(f"[SF] Error scraping {airline_name}: {str(e)}")

        return jobs

    def _is_sf_recruiting(self, html: str) -> bool:
        """Check if it's SuccessFactors Recruiting (newer version)"""
        indicators = [
            'successfactors',
            'careersite',
            'sap-apply',
            'recruitingsite',
        ]
        return any(indicator in html.lower() for indicator in indicators)

    def _is_sf_career_site(self, html: str) -> bool:
        """Check if it's a SuccessFactors Career Site Builder page"""
        indicators = [
            'career-site',
            'jobRequisition',
            'careerSiteToken',
        ]
        return any(indicator in html for indicator in indicators)

    async def _parse_sf_recruiting(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Parse SuccessFactors Recruiting pages"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Look for job cards/listings
        job_selectors = [
            '.job-card', '.jobCard', '.job-listing',
            'li[data-job-id]', '.requisition', '.job-tile',
            'article.job', '.position-card'
        ]

        job_elements = []
        for selector in job_selectors:
            job_elements = soup.select(selector)
            if job_elements:
                break

        # If no job cards, look for job links
        if not job_elements:
            job_links = soup.find_all('a', href=re.compile(r'(job|requisition|position|career)', re.I))

            for link in job_links:
                title = link.get_text(strip=True)
                if not self._is_pilot_job(title):
                    continue

                job_url = link.get('href', '')
                if not job_url.startswith('http'):
                    job_url = self._make_absolute_url(base_url, job_url)

                job = {
                    'title': title,
                    'company': airline_config.get('name', ''),
                    'location': airline_config.get('headquarters', ''),
                    'region': airline_config.get('region', ''),
                    'application_url': job_url,
                    'source': 'SuccessFactors',
                    'date_scraped': datetime.now().isoformat(),
                    'is_active': True,
                }

                # Try to fetch details
                detailed_job = await self._fetch_job_details(job_url, job, client)
                jobs.append(detailed_job if detailed_job else job)

            return jobs

        for element in job_elements:
            try:
                # Extract title
                title_elem = element.select_one('h2, h3, .job-title, .title, a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not self._is_pilot_job(title):
                    continue

                # Get job URL
                link_elem = element.select_one('a[href]') or title_elem
                job_url = link_elem.get('href', '') if link_elem.name == 'a' else ''
                if job_url and not job_url.startswith('http'):
                    job_url = self._make_absolute_url(base_url, job_url)

                # Extract location
                location = ''
                loc_elem = element.select_one('.location, .job-location, [class*="location"]')
                if loc_elem:
                    location = loc_elem.get_text(strip=True)

                # Extract date
                date_posted = ''
                date_elem = element.select_one('.date, .posted, [class*="date"]')
                if date_elem:
                    date_posted = date_elem.get_text(strip=True)

                job = {
                    'title': title,
                    'company': airline_config.get('name', ''),
                    'location': location or airline_config.get('headquarters', ''),
                    'region': airline_config.get('region', ''),
                    'application_url': job_url or base_url,
                    'source': 'SuccessFactors',
                    'date_posted': date_posted,
                    'date_scraped': datetime.now().isoformat(),
                    'is_active': True,
                }

                jobs.append(job)

            except Exception as e:
                continue

        return jobs

    async def _parse_sf_career_site(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Parse SuccessFactors Career Site Builder pages"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Career Site Builder often embeds job data as JSON
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'jobRequisition' in script.string:
                try:
                    # Try to extract JSON
                    json_match = re.search(r'var\s+\w+\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
                    if json_match:
                        job_data = json.loads(json_match.group(1))
                        for item in job_data:
                            title = item.get('title', item.get('jobTitle', ''))
                            if self._is_pilot_job(title):
                                job = self._parse_sf_json_job(item, airline_config, base_url)
                                jobs.append(job)
                except Exception:
                    continue

        # Also try standard HTML parsing
        if not jobs:
            jobs = await self._parse_sf_recruiting(html, base_url, airline_config, client)

        return jobs

    async def _parse_generic_sf(self, html: str, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Generic parsing for SuccessFactors sites"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')

        # Look for any job-related links
        all_links = soup.find_all('a', href=True)

        seen_urls = set()
        for link in all_links:
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # Skip if already seen
            if href in seen_urls:
                continue

            # Check if it looks like a job link
            job_url_patterns = ['job', 'position', 'requisition', 'vacancy', 'opening', 'career']
            if not any(pattern in href.lower() for pattern in job_url_patterns):
                continue

            if not self._is_pilot_job(title):
                continue

            seen_urls.add(href)
            job_url = href if href.startswith('http') else self._make_absolute_url(base_url, href)

            job = {
                'title': title,
                'company': airline_config.get('name', ''),
                'location': airline_config.get('headquarters', ''),
                'region': airline_config.get('region', ''),
                'application_url': job_url,
                'source': 'SuccessFactors',
                'date_scraped': datetime.now().isoformat(),
                'is_active': True,
            }

            jobs.append(job)

        return jobs

    async def _try_sf_api(self, base_url: str, airline_config: Dict, client: httpx.AsyncClient) -> List[Dict]:
        """Try SuccessFactors REST API endpoints"""
        jobs = []

        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"

        # Common SF API patterns
        api_endpoints = [
            '/career/api/v1/jobs',
            '/api/jobs/search',
            '/recruiting/api/jobs',
            '/career/jobs/search',
            '/sf/api/v2/jobs',
        ]

        for endpoint in api_endpoints:
            api_url = f"{base_domain}{endpoint}"

            try:
                # Try GET with search params
                params = {
                    'q': 'pilot',
                    'keyword': 'pilot',
                    'limit': 100,
                }

                response = await client.get(api_url, params=params)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        job_list = data.get('jobs', data.get('results', data.get('data', [])))

                        for job_data in job_list:
                            title = job_data.get('title', job_data.get('jobTitle', ''))
                            if self._is_pilot_job(title):
                                job = self._parse_sf_json_job(job_data, airline_config, base_url)
                                jobs.append(job)

                        if jobs:
                            print(f"[SF] Found {len(jobs)} jobs via API")
                            return jobs

                    except json.JSONDecodeError:
                        continue

                # Also try POST
                response = await client.post(
                    api_url,
                    json={'keyword': 'pilot', 'pageSize': 100},
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        job_list = data.get('jobs', data.get('results', []))

                        for job_data in job_list:
                            title = job_data.get('title', '')
                            if self._is_pilot_job(title):
                                job = self._parse_sf_json_job(job_data, airline_config, base_url)
                                jobs.append(job)

                        if jobs:
                            return jobs

                    except json.JSONDecodeError:
                        continue

            except Exception:
                continue

        return jobs

    def _parse_sf_json_job(self, job_data: Dict, airline_config: Dict, base_url: str) -> Dict:
        """Parse a job from SuccessFactors JSON format"""
        title = job_data.get('title', job_data.get('jobTitle', job_data.get('name', '')))
        location = job_data.get('location', job_data.get('primaryLocation', job_data.get('city', '')))

        # Handle location object
        if isinstance(location, dict):
            location = location.get('name', location.get('city', ''))

        job_url = job_data.get('applyUrl', job_data.get('url', job_data.get('externalPath', '')))
        if job_url and not job_url.startswith('http'):
            job_url = self._make_absolute_url(base_url, job_url)

        job = {
            'title': title,
            'company': airline_config.get('name', ''),
            'location': location or airline_config.get('headquarters', ''),
            'region': airline_config.get('region', ''),
            'application_url': job_url or base_url,
            'source': 'SuccessFactors',
            'description': job_data.get('description', job_data.get('jobDescription', '')),
            'date_posted': job_data.get('postedDate', job_data.get('postingDate', '')),
            'date_scraped': datetime.now().isoformat(),
            'is_active': True,
        }

        # Extract requirements if description exists
        if job.get('description'):
            job = self._extract_requirements(job)

        return job

    async def _fetch_job_details(self, job_url: str, job: Dict, client: httpx.AsyncClient) -> Optional[Dict]:
        """Fetch additional details from job detail page"""
        if not job_url:
            return job

        try:
            response = await client.get(job_url)
            if response.status_code != 200:
                return job

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract description
            desc_selectors = [
                '.job-description', '.description', '#jobDescription',
                '[class*="description"]', '.content', 'article'
            ]

            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    job['description'] = desc_elem.get_text(strip=True)[:5000]
                    break

            # Extract location if not already set
            if not job.get('location') or job['location'] == job.get('company', ''):
                loc_selectors = ['.location', '[class*="location"]', '.job-location']
                for selector in loc_selectors:
                    loc_elem = soup.select_one(selector)
                    if loc_elem:
                        job['location'] = loc_elem.get_text(strip=True)
                        break

            # Extract requirements
            if job.get('description'):
                job = self._extract_requirements(job)

            return job

        except Exception:
            return job

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
        """Extract requirements from job description"""
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
            r'(\d{1,2}[,.]?\d{3})\s*(?:pic|command|p\.?i\.?c\.?)\s*hours?',
            r'pic[:\s]*(\d{1,2}[,.]?\d{3})',
            r'command\s*hours?[:\s]*(\d{1,2}[,.]?\d{3})',
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

        # Type rating
        type_rating_phrases = [
            'type rating required', 'type rated', 'current type rating',
            'must hold type rating', 'valid type rating', 'typerating'
        ]
        job['type_rating_required'] = any(phrase in description for phrase in type_rating_phrases)

        type_provided_phrases = [
            'type rating provided', 'type rating offered', 'will provide type',
            'type conversion provided', 'full type rating'
        ]
        job['type_rating_provided'] = any(phrase in description for phrase in type_provided_phrases)

        # License requirements
        license_patterns = [
            r'(easa|faa|icao|uk caa|tcca|casa)[\s-]*(atpl|cpl|mpl)',
            r'(atpl|cpl|mpl)[\s/]*(frozen|f)?',
        ]

        licenses = []
        for pattern in license_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if isinstance(match, tuple):
                    licenses.append(' '.join(m for m in match if m).upper().strip())
                else:
                    licenses.append(match.upper())

        if licenses:
            job['license_required'] = ', '.join(set(licenses))

        # Position type
        if any(term in description for term in ['captain', 'commander', 'kapitän', 'kapten', 'commandant']):
            job['position_type'] = 'captain'
        elif any(term in description for term in ['first officer', 'f/o', 'copilot', 'co-pilot', 'styrman']):
            job['position_type'] = 'first_officer'
        elif any(term in description for term in ['cadet', 'trainee', 'ab initio', 'mpl']):
            job['position_type'] = 'cadet'
        elif any(term in description for term in ['instructor', 'tri', 'tre', 'tki']):
            job['position_type'] = 'instructor'
        else:
            job['position_type'] = 'other'

        # Aircraft type
        aircraft_patterns = [
            r'(a320|a321|a319|a318|a330|a340|a350|a380)',
            r'(b737|b738|b739|737ng|737\s*max|b747|b757|b767|b777|b787|dreamliner)',
            r'(crj\s*\d{3}|erj\s*\d{3}|e\d{3}|embraer)',
            r'(atr\s*\d{2}|dash\s*8|q\d{3}|dhc)',
        ]

        aircraft_types = []
        for pattern in aircraft_patterns:
            matches = re.findall(pattern, description)
            aircraft_types.extend(matches)

        if aircraft_types:
            # Clean up aircraft types
            cleaned = []
            for t in aircraft_types:
                t = t.upper().strip()
                t = re.sub(r'\s+', '', t)
                cleaned.append(t)
            job['aircraft_type'] = ', '.join(set(cleaned))

        return job


async def test_successfactors_scraper():
    """Test the SuccessFactors scraper"""
    scraper = SuccessfactorsScraper()

    test_airlines = [
        {
            'name': 'Lufthansa',
            'careers_url': 'https://www.be-lufthansa.com/en/jobs',
            'region': 'europe',
            'headquarters': 'Frankfurt, Germany',
        },
        {
            'name': 'Swiss International',
            'careers_url': 'https://www.swiss.com/corporate/en/company/career',
            'region': 'europe',
            'headquarters': 'Zurich, Switzerland',
        },
    ]

    all_jobs = []
    for airline in test_airlines:
        jobs = await scraper.fetch_jobs(airline)
        all_jobs.extend(jobs)
        await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"Total pilot jobs found: {len(all_jobs)}")
    print(f"{'='*60}")

    for job in all_jobs[:10]:
        print(f"\n{job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Apply: {job['application_url']}")

    return all_jobs


if __name__ == '__main__':
    asyncio.run(test_successfactors_scraper())

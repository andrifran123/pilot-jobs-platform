"""
Qatar Airways REAL Scraper using Playwright

This script uses a real browser to:
1. Go to the actual Qatar Airways Pilots search page
2. Find ALL job listings
3. Visit each job individually to extract details
4. Extract flight hours from the job description text
"""

import re
import time
import sys
import os
from playwright.sync_api import sync_playwright

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def normalize_hours(text):
    """
    Finds hours in the messy text.
    Looks for patterns like '1000 hours', 'Min 500 hrs', '3,000 flying hours'
    """
    if not text:
        return 0

    # AGGRESSIVE CLEANING - Remove all non-ASCII characters, normalize whitespace
    # This handles bullet points, special characters, etc.
    cleaned = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
    cleaned = cleaned.lower()

    # PRIORITY patterns - these are the "total" requirements we want
    # Check these first and return if found
    priority_patterns = [
        # "Minimum 1000 hours total flight time" - THE ONE WE WANT
        r'minimum\s+(\d{3,5})\s+hours?\s+total\s+flight',
        # "1000 hours total time"
        r'(\d{3,5})\s+hours?\s+total\s+(?:flight\s+)?time',
        # "total flight time: 1000 hours"
        r'total\s+(?:flight\s+)?time[:\s]+(\d{3,5})',
    ]

    for pattern in priority_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            val = int(match.group(1).replace(',', ''))
            if 100 <= val < 30000:
                return val

    # Fallback patterns - less specific
    fallback_patterns = [
        # "minimum of 1000 hours"
        r'minimum\s+(?:of\s+)?(\d{3,5})\s+hours?',
        # "1000+ hours"
        r'(\d{3,5})\+?\s*hours?',
        # "1,000 hours"
        r'(\d{1,2},\d{3})\s*hours?',
    ]

    valid_hours = []
    for pattern in fallback_patterns:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        for m in matches:
            try:
                val = int(m.replace(',', ''))
                # Filter out crazy low numbers (like "24 hours" availability)
                if 100 <= val < 30000:
                    valid_hours.append(val)
            except:
                continue

    # Return the HIGHEST requirement found (total hours is usually highest)
    return max(valid_hours) if valid_hours else 0


def extract_position_type(title):
    """Determine position type from title"""
    title_lower = title.lower()
    if 'captain' in title_lower or 'command' in title_lower:
        return 'captain'
    elif 'first officer' in title_lower or 'f/o' in title_lower:
        return 'first_officer'
    elif 'second officer' in title_lower or 's/o' in title_lower:
        return 'second_officer'
    elif 'cadet' in title_lower or 'trainee' in title_lower:
        return 'cadet'
    elif 'instructor' in title_lower:
        return 'instructor'
    elif 'roadshow' in title_lower or 'event' in title_lower or 'permit' in title_lower:
        return 'other'
    else:
        return 'first_officer'


def extract_aircraft_type(text):
    """Extract aircraft types from text"""
    if not text:
        return None

    text_lower = text.lower()
    aircraft_patterns = [
        r'(a320|a321|a319|a318)',
        r'(a330|a340)',
        r'(a350)',
        r'(a380)',
        r'(b737|737ng|737\s*max|boeing\s*737)',
        r'(b777|777|boeing\s*777)',
        r'(b787|787|dreamliner)',
        r'(bd700|global\s*\d+|gulfstream)',
        r'(airbus)',
        r'(boeing)',
    ]

    aircraft_types = []
    for pattern in aircraft_patterns:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            cleaned = m.upper().replace(' ', '')
            if cleaned not in aircraft_types and cleaned not in ['AIRBUS', 'BOEING']:
                aircraft_types.append(cleaned)

    # Handle generic "Airbus" or "Boeing"
    if 'airbus' in text_lower and not any(a.startswith('A3') for a in aircraft_types):
        aircraft_types.append('Airbus')
    if 'boeing' in text_lower and not any(a.startswith(('B7', '737')) for a in aircraft_types):
        aircraft_types.append('Boeing')

    return ', '.join(aircraft_types) if aircraft_types else None


def scrape_qatar_real(headless=True):
    """
    Scrape Qatar Airways pilot jobs using Playwright browser automation

    Args:
        headless: If False, shows the browser window (useful for debugging)
    """
    print("🚀 Launching Qatar Airways Playwright Scraper...")

    results = []

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        # Use the Avature search URL that shows pilot jobs
        url = "https://careers.qatarairways.com/global/SearchJobs/?817=%5B9764%5D&817_format=449&listFilterMode=1"
        print(f"🌍 Navigating to: {url}")

        try:
            page.goto(url, timeout=60000)
            time.sleep(3)  # Wait for dynamic content
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            browser.close()
            return results

        # Find all job links
        all_links = page.query_selector_all('a')
        print(f"📋 Found {len(all_links)} total links")

        job_links = []
        for link in all_links:
            try:
                href = link.get_attribute('href') or ''
                text = link.inner_text().strip()

                # Filter for actual job links (JobDetail URLs, not social share)
                if text and len(text) > 5:
                    if '/JobDetail/' in href and 'facebook' not in href.lower() and 'linkedin' not in href.lower() and 'twitter' not in href.lower():
                        # Filter for pilot-related jobs
                        if any(kw in text.lower() for kw in ['pilot', 'officer', 'captain', 'type rated', 'flight']):
                            job_links.append({'title': text, 'url': href})
            except:
                continue

        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for job in job_links:
            if job['url'] not in seen:
                seen.add(job['url'])
                unique_jobs.append(job)

        print(f"✅ Found {len(unique_jobs)} unique pilot job links")

        # Visit each job page to get detailed info
        for i, job in enumerate(unique_jobs):
            print(f"   [{i+1}/{len(unique_jobs)}] {job['title'][:50]}...")

            try:
                # Navigate to job page
                page.goto(job['url'], timeout=30000)
                time.sleep(2)  # Wait for content

                # Get all text on the page
                description = ""
                try:
                    description = page.locator("body").inner_text()
                except:
                    pass

                # Extract hours requirement
                hours = normalize_hours(description)

                # Extract location
                location = "Doha, Qatar"  # Default

                # Build job data
                job_data = {
                    "title": job['title'],
                    "company": "Qatar Airways",
                    "location": location,
                    "region": "middle_east",
                    "min_total_hours": hours if hours > 0 else None,
                    "position_type": extract_position_type(job['title']),
                    "aircraft_type": extract_aircraft_type(job['title'] + " " + description[:1000]),
                    "application_url": job['url'],
                    "source": "Direct - Qatar Airways (Playwright)",
                    "type_rating_required": 'type rated' in job['title'].lower() or 'type rating required' in description.lower(),
                    "type_rating_provided": 'type rating provided' in description.lower(),
                    "visa_sponsorship": True,  # Qatar typically sponsors
                    "contract_type": "permanent",
                    "is_active": True,
                }

                # Entry level detection
                is_cadet = job_data['position_type'] == 'cadet'
                has_low_hours = hours and hours < 500
                job_data['is_entry_level'] = is_cadet or has_low_hours

                hours_str = f"{hours} hours" if hours else "Not found"
                print(f"      ✅ {hours_str}")

                results.append(job_data)

            except Exception as e:
                print(f"      ❌ Error: {str(e)[:50]}")

            # Rate limiting
            time.sleep(1.5)

        browser.close()

    print(f"\n🎯 Scraping complete! Found {len(results)} pilot jobs with details")
    return results


def main():
    """Main function to run the scraper"""
    # Run in headless mode (set headless=False to see the browser)
    jobs = scrape_qatar_real(headless=True)

    print("\n" + "="*70)
    print("FINAL RESULTS - Qatar Airways Pilot Jobs")
    print("="*70)

    for job in jobs:
        hours_str = f"{job['min_total_hours']} hrs" if job['min_total_hours'] else "Not specified"
        print(f"\n📌 {job['title']}")
        print(f"   Hours: {hours_str}")
        print(f"   Position: {job['position_type']}")
        print(f"   Aircraft: {job['aircraft_type'] or 'N/A'}")
        print(f"   Location: {job['location']}")
        print(f"   Apply: {job['application_url']}")

    return jobs


if __name__ == "__main__":
    main()

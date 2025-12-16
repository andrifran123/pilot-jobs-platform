"""
Master Scraper Orchestrator

Coordinates all scrapers to collect pilot jobs from multiple sources:
1. Direct airline ATS scrapers (Taleo, Workday, SuccessFactors)
2. Recruitment agency scrapers
3. Discovery bot for new airlines
4. Data normalization and deduplication

Usage:
    python orchestrator.py --full           # Full scrape of all sources
    python orchestrator.py --quick          # Quick scrape of top airlines only
    python orchestrator.py --discover       # Run discovery bot only
    python orchestrator.py --airline "Emirates"  # Scrape specific airline
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from airline_sources import AIRLINES_BY_ATS, get_all_airlines, get_airlines_by_ats
from normalizer import JobNormalizer
from scrapers.workday_scraper import WorkdayScraper
from scrapers.taleo_scraper import TaleoScraper
from scrapers.successfactors_scraper import SuccessfactorsScraper
from scrapers.discovery_bot import DiscoveryBot
from scrapers.agency_scrapers import AgencyOrchestrator


class ScraperOrchestrator:
    """Master orchestrator for all pilot job scrapers"""

    def __init__(self, output_dir: str = None):
        """
        Initialize orchestrator

        Args:
            output_dir: Directory to save scraped data
        """
        self.output_dir = output_dir or str(Path(__file__).parent / 'output')
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize scrapers
        self.taleo_scraper = TaleoScraper()
        self.workday_scraper = WorkdayScraper()
        self.successfactors_scraper = SuccessfactorsScraper()
        self.agency_orchestrator = AgencyOrchestrator()
        self.normalizer = JobNormalizer()

        # Stats tracking
        self.stats = {
            'start_time': None,
            'end_time': None,
            'airlines_scraped': 0,
            'jobs_found': 0,
            'jobs_after_dedup': 0,
            'errors': [],
        }

    async def run_full_scrape(self) -> List[Dict]:
        """
        Run full scrape of all known airlines

        Returns:
            List of normalized, deduplicated job dictionaries
        """
        print("\n" + "="*70)
        print("PILOT JOBS SCRAPER - FULL SCAN")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.stats['start_time'] = datetime.now().isoformat()
        all_jobs = []

        # Get all airlines from database
        airlines = get_all_airlines()
        print(f"\nTotal airlines to scrape: {len(airlines)}")

        # Group by ATS type for efficient scraping
        taleo_airlines = [a for a in airlines if a.get('ats_type') == 'taleo']
        workday_airlines = [a for a in airlines if a.get('ats_type') == 'workday']
        sf_airlines = [a for a in airlines if a.get('ats_type') == 'successfactors']
        direct_airlines = [a for a in airlines if a.get('ats_type') == 'direct']

        print(f"\nBy ATS type:")
        print(f"  Taleo: {len(taleo_airlines)}")
        print(f"  Workday: {len(workday_airlines)}")
        print(f"  SuccessFactors: {len(sf_airlines)}")
        print(f"  Direct: {len(direct_airlines)}")

        # Scrape each ATS type
        print("\n" + "-"*50)
        print("SCRAPING TALEO AIRLINES")
        print("-"*50)
        taleo_jobs = await self._scrape_airlines(taleo_airlines, self.taleo_scraper)
        all_jobs.extend(taleo_jobs)

        print("\n" + "-"*50)
        print("SCRAPING WORKDAY AIRLINES")
        print("-"*50)
        workday_jobs = await self._scrape_airlines(workday_airlines, self.workday_scraper)
        all_jobs.extend(workday_jobs)

        print("\n" + "-"*50)
        print("SCRAPING SUCCESSFACTORS AIRLINES")
        print("-"*50)
        sf_jobs = await self._scrape_airlines(sf_airlines, self.successfactors_scraper)
        all_jobs.extend(sf_jobs)

        # Scrape recruitment agencies
        print("\n" + "-"*50)
        print("SCRAPING RECRUITMENT AGENCIES")
        print("-"*50)
        agency_jobs = await self.agency_orchestrator.fetch_all_jobs()
        all_jobs.extend(agency_jobs)
        print(f"Agency jobs: {len(agency_jobs)}")

        # Normalize all jobs
        print("\n" + "-"*50)
        print("NORMALIZING DATA")
        print("-"*50)
        normalized_jobs = []
        for job in all_jobs:
            try:
                normalized = self.normalizer.normalize_job(job)
                normalized_jobs.append(normalized)
            except Exception as e:
                print(f"[Normalizer] Error: {e}")

        print(f"Normalized {len(normalized_jobs)} jobs")

        # Deduplicate
        print("\n" + "-"*50)
        print("DEDUPLICATING")
        print("-"*50)
        unique_jobs = self._deduplicate_jobs(normalized_jobs)
        print(f"Unique jobs after dedup: {len(unique_jobs)}")

        # Update stats
        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['jobs_found'] = len(all_jobs)
        self.stats['jobs_after_dedup'] = len(unique_jobs)

        # Save results
        self._save_results(unique_jobs)

        # Print summary
        self._print_summary(unique_jobs)

        return unique_jobs

    async def run_quick_scrape(self) -> List[Dict]:
        """
        Quick scrape of top priority airlines only
        """
        print("\n" + "="*70)
        print("PILOT JOBS SCRAPER - QUICK SCAN")
        print("="*70)

        self.stats['start_time'] = datetime.now().isoformat()

        # Top airlines to always check
        priority_airlines = [
            'Ryanair', 'EasyJet', 'Wizz Air', 'Vueling',
            'Emirates', 'Etihad', 'Qatar Airways',
            'Lufthansa', 'Swiss', 'British Airways',
        ]

        all_airlines = get_all_airlines()
        priority = [a for a in all_airlines if a['name'] in priority_airlines]

        print(f"Quick scan: {len(priority)} priority airlines")

        all_jobs = []

        for airline in priority:
            ats_type = airline.get('ats_type', 'direct')

            if ats_type == 'taleo':
                jobs = await self.taleo_scraper.fetch_jobs(airline)
            elif ats_type == 'workday':
                jobs = await self.workday_scraper.fetch_jobs(airline)
            elif ats_type == 'successfactors':
                jobs = await self.successfactors_scraper.fetch_jobs(airline)
            else:
                continue

            all_jobs.extend(jobs)
            self.stats['airlines_scraped'] += 1

            # Rate limiting
            await asyncio.sleep(2)

        # Normalize and dedupe
        normalized = [self.normalizer.normalize_job(j) for j in all_jobs]
        unique_jobs = self._deduplicate_jobs(normalized)

        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['jobs_found'] = len(all_jobs)
        self.stats['jobs_after_dedup'] = len(unique_jobs)

        self._save_results(unique_jobs, filename='quick_scan')
        self._print_summary(unique_jobs)

        return unique_jobs

    async def run_discovery(self) -> Dict:
        """
        Run discovery bot to find new airlines
        """
        print("\n" + "="*70)
        print("PILOT JOBS SCRAPER - DISCOVERY MODE")
        print("="*70)

        # Get known airline names
        all_airlines = get_all_airlines()
        known_names = {a['name'] for a in all_airlines}

        bot = DiscoveryBot(known_airlines=known_names)
        results = await bot.run_discovery()

        # Save discovery results
        output_path = os.path.join(self.output_dir, 'discovery_results.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nDiscovery results saved to: {output_path}")

        return results

    async def scrape_airline(self, airline_name: str) -> List[Dict]:
        """
        Scrape a specific airline by name
        """
        print(f"\nScraping: {airline_name}")

        all_airlines = get_all_airlines()
        airline = next((a for a in all_airlines if a['name'].lower() == airline_name.lower()), None)

        if not airline:
            print(f"Airline not found: {airline_name}")
            return []

        ats_type = airline.get('ats_type', 'direct')
        jobs = []

        if ats_type == 'taleo':
            jobs = await self.taleo_scraper.fetch_jobs(airline)
        elif ats_type == 'workday':
            jobs = await self.workday_scraper.fetch_jobs(airline)
        elif ats_type == 'successfactors':
            jobs = await self.successfactors_scraper.fetch_jobs(airline)
        else:
            print(f"No scraper for ATS type: {ats_type}")

        if jobs:
            normalized = [self.normalizer.normalize_job(j) for j in jobs]
            self._save_results(normalized, filename=f'airline_{airline_name.lower().replace(" ", "_")}')
            print(f"Found {len(jobs)} jobs")

        return jobs

    async def _scrape_airlines(self, airlines: List[Dict], scraper) -> List[Dict]:
        """Scrape a list of airlines with a specific scraper"""
        all_jobs = []

        for airline in airlines:
            try:
                jobs = await scraper.fetch_jobs(airline)
                all_jobs.extend(jobs)
                self.stats['airlines_scraped'] += 1
            except Exception as e:
                error_msg = f"Error scraping {airline.get('name')}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.stats['errors'].append(error_msg)

            # Rate limiting between airlines
            await asyncio.sleep(2)

        return all_jobs

    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on key fields"""
        seen = set()
        unique = []

        for job in jobs:
            # Create unique key from title, company, location
            key_parts = [
                job.get('title', '').lower().strip(),
                job.get('company', '').lower().strip(),
                job.get('location', '').lower().strip()[:50],  # Truncate location
            ]
            key = '|'.join(key_parts)

            if key not in seen:
                seen.add(key)
                unique.append(job)

        return unique

    def _save_results(self, jobs: List[Dict], filename: str = 'jobs'):
        """Save scraped jobs to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save as JSON
        json_path = os.path.join(self.output_dir, f'{filename}_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'total_jobs': len(jobs),
                    'stats': self.stats,
                },
                'jobs': jobs
            }, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {json_path}")

        # Also save as CSV for easy viewing
        csv_path = os.path.join(self.output_dir, f'{filename}_{timestamp}.csv')
        self._save_csv(jobs, csv_path)
        print(f"CSV saved to: {csv_path}")

        # Save latest (overwrite)
        latest_path = os.path.join(self.output_dir, 'latest_jobs.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump({'jobs': jobs}, f, indent=2, ensure_ascii=False)

    def _save_csv(self, jobs: List[Dict], filepath: str):
        """Save jobs as CSV"""
        import csv

        if not jobs:
            return

        # Define columns
        columns = [
            'title', 'company', 'location', 'region', 'position_type',
            'aircraft_type', 'type_rating_required', 'type_rating_provided',
            'min_total_hours', 'min_pic_hours', 'license_required',
            'contract_type', 'salary_info', 'date_posted', 'application_url'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()

            for job in jobs:
                writer.writerow(job)

    def _print_summary(self, jobs: List[Dict]):
        """Print scraping summary"""
        print("\n" + "="*70)
        print("SCRAPING SUMMARY")
        print("="*70)
        print(f"Airlines scraped: {self.stats['airlines_scraped']}")
        print(f"Raw jobs found: {self.stats['jobs_found']}")
        print(f"Unique jobs: {self.stats['jobs_after_dedup']}")

        if self.stats['errors']:
            print(f"\nErrors: {len(self.stats['errors'])}")

        # Breakdown by region
        regions = {}
        for job in jobs:
            region = job.get('region', 'unknown')
            regions[region] = regions.get(region, 0) + 1

        print("\nJobs by region:")
        for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region}: {count}")

        # Breakdown by position type
        positions = {}
        for job in jobs:
            pos = job.get('position_type', 'unknown')
            positions[pos] = positions.get(pos, 0) + 1

        print("\nJobs by position:")
        for pos, count in sorted(positions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {pos}: {count}")

        # Non-type-rated jobs (user's focus!)
        non_type_rated = [j for j in jobs if not j.get('type_rating_required', True)]
        print(f"\nNon-type-rated positions: {len(non_type_rated)}")

        print("\n" + "="*70)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pilot Jobs Scraper Orchestrator')
    parser.add_argument('--full', action='store_true', help='Run full scrape of all airlines')
    parser.add_argument('--quick', action='store_true', help='Quick scrape of priority airlines')
    parser.add_argument('--agencies', action='store_true', help='Scrape recruitment agencies only')
    parser.add_argument('--discover', action='store_true', help='Run discovery bot only')
    parser.add_argument('--airline', type=str, help='Scrape specific airline by name')
    parser.add_argument('--output', type=str, help='Output directory')

    args = parser.parse_args()

    orchestrator = ScraperOrchestrator(output_dir=args.output)

    if args.full:
        await orchestrator.run_full_scrape()
    elif args.quick:
        await orchestrator.run_quick_scrape()
    elif args.agencies:
        jobs = await orchestrator.agency_orchestrator.fetch_all_jobs()
        normalized = [orchestrator.normalizer.normalize_job(j) for j in jobs]
        orchestrator._save_results(normalized, filename='agency_jobs')
        print(f"\nFound {len(jobs)} jobs from recruitment agencies")
    elif args.discover:
        await orchestrator.run_discovery()
    elif args.airline:
        await orchestrator.scrape_airline(args.airline)
    else:
        # Default: run quick scrape
        print("No mode specified, running quick scrape...")
        await orchestrator.run_quick_scrape()


if __name__ == '__main__':
    asyncio.run(main())

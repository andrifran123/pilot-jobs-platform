"""
Pilot Job Scrapers

ATS-specific scrapers:
- TaleoScraper: For Taleo/Oracle career sites
- WorkdayScraper: For Workday career sites
- SuccessfactorsScraper: For SAP SuccessFactors sites

Utility scrapers:
- DiscoveryBot: Discovers new airlines from aggregator sites
- AgencyOrchestrator: Scrapes recruitment agencies

Usage:
    from scrapers import TaleoScraper, WorkdayScraper, SuccessfactorsScraper
    from scrapers.discovery_bot import DiscoveryBot
    from scrapers.agency_scrapers import AgencyOrchestrator
"""

from .taleo_scraper import TaleoScraper
from .workday_scraper import WorkdayScraper
from .successfactors_scraper import SuccessfactorsScraper
from .discovery_bot import DiscoveryBot
from .agency_scrapers import AgencyOrchestrator, RishworthScraper, PARCScraper, OSMScraper

__all__ = [
    'TaleoScraper',
    'WorkdayScraper',
    'SuccessfactorsScraper',
    'DiscoveryBot',
    'AgencyOrchestrator',
    'RishworthScraper',
    'PARCScraper',
    'OSMScraper',
]

"""
Airline Career Page Sources Database
Organized by ATS (Applicant Tracking System) type for efficient scraping

Each ATS has a consistent structure, so we can build one scraper per ATS
and apply it to dozens of airlines.
"""

# ============================================================
# TALEO ATS - Used by many legacy carriers
# URL Pattern: Usually contains "taleo" or specific tenant ID
# ============================================================
TALEO_AIRLINES = {
    "emirates": {
        "name": "Emirates",
        "careers_url": "https://www.emiratesgroupcareers.com/pilots/",
        "api_base": "https://emiratesgroupcareers.taleo.net/careersection/",
        "region": "middle_east",
        "country": "UAE"
    },
    "etihad": {
        "name": "Etihad Airways",
        "careers_url": "https://careers.etihad.com/",
        "search_url": "https://careers.etihad.com/search/?q=pilot",
        "region": "middle_east",
        "country": "UAE"
    },
    "british_airways": {
        "name": "British Airways",
        "careers_url": "https://careers.ba.com/",
        "search_url": "https://careers.ba.com/search-and-apply?search=pilot",
        "region": "europe",
        "country": "UK"
    },
    "air_france": {
        "name": "Air France",
        "careers_url": "https://recrutement.airfrance.com/",
        "search_url": "https://recrutement.airfrance.com/offre-emploi/pilote",
        "region": "europe",
        "country": "France"
    },
    "klm": {
        "name": "KLM Royal Dutch Airlines",
        "careers_url": "https://careers.klm.com/",
        "search_url": "https://careers.klm.com/go/Pilots/8730801/",
        "region": "europe",
        "country": "Netherlands"
    },
    "qatar_airways": {
        "name": "Qatar Airways",
        "careers_url": "https://careers.qatarairways.com/global/SearchJobs/?817=%5B9764%5D&817_format=449&listFilterMode=1",
        "taleo_base": "https://aa115.taleo.net/careersection/QA_External_CS/",
        "region": "middle_east",
        "country": "Qatar",
        "headquarters": "Doha, Qatar"
    },
}

# ============================================================
# WORKDAY ATS - Modern cloud-based ATS
# URL Pattern: Usually myworkdayjobs.com or wd5.myworkdayjobs.com
# ============================================================
WORKDAY_AIRLINES = {
    "virgin_atlantic": {
        "name": "Virgin Atlantic",
        "careers_url": "https://careersuk.virgin-atlantic.com/",
        "workday_url": "https://careers.virginatlantic.com/global/en/search-results?keywords=pilot",
        "region": "europe",
        "country": "UK"
    },
    "singapore_airlines": {
        "name": "Singapore Airlines",
        "careers_url": "https://www.singaporeair.com/en_UK/flying-with-us/our-story/careers/",
        "workday_url": "https://singaporeair.wd3.myworkdayjobs.com/SIA",
        "region": "asia",
        "country": "Singapore"
    },
    "cathay_pacific": {
        "name": "Cathay Pacific",
        "careers_url": "https://careers.cathaypacific.com/",
        "workday_url": "https://careers.cathaypacific.com/search-results?keywords=pilot",
        "region": "asia",
        "country": "Hong Kong"
    },
    "lufthansa": {
        "name": "Lufthansa",
        "careers_url": "https://www.be-lufthansa.com/en/",
        "workday_url": "https://lufthansagroup.wd3.myworkdayjobs.com/",
        "region": "europe",
        "country": "Germany"
    },
    "swiss": {
        "name": "SWISS",
        "careers_url": "https://www.swiss.com/corporate/en/company/jobs-career",
        "workday_url": "https://swiss.wd3.myworkdayjobs.com/",
        "region": "europe",
        "country": "Switzerland"
    },
    "qantas": {
        "name": "Qantas",
        "careers_url": "https://www.qantas.com/au/en/about-us/qantas-careers.html",
        "workday_url": "https://qantas.wd3.myworkdayjobs.com/qantasjobs",
        "region": "oceania",
        "country": "Australia"
    },
}

# ============================================================
# SUCCESSFACTORS ATS - SAP-based ATS
# URL Pattern: Usually contains successfactors or jobs.sap.com
# ============================================================
SUCCESSFACTORS_AIRLINES = {
    "turkish_airlines": {
        "name": "Turkish Airlines",
        "careers_url": "https://www.turkishairlines.com/en-int/careers/",
        "sf_url": "https://career5.successfactors.eu/career?company=TurkishAir",
        "region": "europe",
        "country": "Turkey"
    },
    "finnair": {
        "name": "Finnair",
        "careers_url": "https://company.finnair.com/en/careers",
        "sf_url": "https://careers.finnair.com/",
        "region": "europe",
        "country": "Finland"
    },
    "sas": {
        "name": "SAS Scandinavian Airlines",
        "careers_url": "https://www.sasgroup.net/careers/",
        "sf_url": "https://performancemanager5.successfactors.eu/sfcareer/jobreqcareerpvt?jobId=",
        "region": "europe",
        "country": "Sweden"
    },
}

# ============================================================
# CUSTOM/DIRECT CAREER PAGES - Airlines with their own systems
# These need individual scrapers
# ============================================================
DIRECT_CAREER_PAGES = {
    # Low Cost Carriers - Europe
    "ryanair": {
        "name": "Ryanair",
        "careers_url": "https://careers.ryanair.com/",
        "pilot_url": "https://careers.ryanair.com/jobs?department=pilots",
        "region": "europe",
        "country": "Ireland",
        "notes": "Custom React app, offers cadet programs"
    },
    "easyjet": {
        "name": "easyJet",
        "careers_url": "https://careers.easyjet.com/",
        "pilot_url": "https://careers.easyjet.com/vacancies/?search=pilot",
        "region": "europe",
        "country": "UK",
        "notes": "Custom career site"
    },
    "wizz_air": {
        "name": "Wizz Air",
        "careers_url": "https://careers.wizzair.com/",
        "pilot_url": "https://careers.wizzair.com/jobs?department=Flight%20Crew",
        "region": "europe",
        "country": "Hungary",
        "notes": "Fast-growing LCC"
    },
    "vueling": {
        "name": "Vueling",
        "careers_url": "https://careers.vueling.com/",
        "pilot_url": "https://careers.vueling.com/jobs?q=pilot",
        "region": "europe",
        "country": "Spain",
        "notes": "IAG group"
    },
    "eurowings": {
        "name": "Eurowings",
        "careers_url": "https://www.eurowings.com/en/information/career.html",
        "pilot_url": "https://www.be-lufthansa.com/en/", # Part of Lufthansa Group
        "region": "europe",
        "country": "Germany",
        "notes": "Lufthansa Group LCC"
    },
    "norwegian": {
        "name": "Norwegian Air",
        "careers_url": "https://www.norwegian.com/en/about/careers/",
        "pilot_url": "https://careers.norwegian.com/jobs?department=pilots",
        "region": "europe",
        "country": "Norway"
    },

    # Middle East
    "saudia": {
        "name": "Saudi Arabian Airlines (Saudia)",
        "careers_url": "https://www.saudia.com/about-saudia/careers",
        "pilot_url": "https://jobs.saudia.com/",
        "region": "middle_east",
        "country": "Saudi Arabia"
    },
    "flydubai": {
        "name": "flydubai",
        "careers_url": "https://careers.flydubai.com/",
        "pilot_url": "https://careers.flydubai.com/en/jobs/?search=pilot",
        "region": "middle_east",
        "country": "UAE"
    },
    "gulf_air": {
        "name": "Gulf Air",
        "careers_url": "https://www.gulfair.com/about-gulf-air/careers",
        "pilot_url": "https://careers.gulfair.com/",
        "region": "middle_east",
        "country": "Bahrain"
    },
    "oman_air": {
        "name": "Oman Air",
        "careers_url": "https://www.omanair.com/en/about-us/careers",
        "pilot_url": "https://careers.omanair.com/",
        "region": "middle_east",
        "country": "Oman"
    },

    # Asia Pacific
    "air_asia": {
        "name": "AirAsia",
        "careers_url": "https://www.airasia.com/aa/about-us/careers/",
        "pilot_url": "https://careers.airasia.com/",
        "region": "asia",
        "country": "Malaysia"
    },
    "vietnam_airlines": {
        "name": "Vietnam Airlines",
        "careers_url": "https://www.vietnamairlines.com/vn/en/about-us/careers",
        "pilot_url": "https://careers.vietnamairlines.com/",
        "region": "asia",
        "country": "Vietnam",
        "notes": "Often recruits through Rishworth"
    },
    "korean_air": {
        "name": "Korean Air",
        "careers_url": "https://www.koreanair.com/global/en/about/careers/",
        "pilot_url": "https://recruit.koreanair.com/",
        "region": "asia",
        "country": "South Korea"
    },
    "thai_airways": {
        "name": "Thai Airways",
        "careers_url": "https://www.thaiairways.com/en/about_thai/careers/",
        "pilot_url": "https://careers.thaiairways.com/",
        "region": "asia",
        "country": "Thailand"
    },
    "garuda": {
        "name": "Garuda Indonesia",
        "careers_url": "https://career.garuda-indonesia.com/",
        "pilot_url": "https://career.garuda-indonesia.com/vacancy",
        "region": "asia",
        "country": "Indonesia"
    },
    "air_new_zealand": {
        "name": "Air New Zealand",
        "careers_url": "https://careers.airnewzealand.co.nz/",
        "pilot_url": "https://careers.airnewzealand.co.nz/search/?q=pilot",
        "region": "oceania",
        "country": "New Zealand"
    },

    # Africa
    "ethiopian": {
        "name": "Ethiopian Airlines",
        "careers_url": "https://www.ethiopianairlines.com/aa/about-us/career",
        "pilot_url": "https://careers.ethiopianairlines.com/",
        "region": "africa",
        "country": "Ethiopia"
    },
    "kenya_airways": {
        "name": "Kenya Airways",
        "careers_url": "https://www.kenya-airways.com/global/en/information/about-kenya-airways/careers/",
        "pilot_url": "https://careers.kenya-airways.com/",
        "region": "africa",
        "country": "Kenya"
    },
    "south_african": {
        "name": "South African Airways",
        "careers_url": "https://www.flysaa.com/about-us/careers",
        "pilot_url": "https://careers.flysaa.com/",
        "region": "africa",
        "country": "South Africa"
    },

    # Americas (for completeness, though filtering out US)
    "air_canada": {
        "name": "Air Canada",
        "careers_url": "https://careers.aircanada.com/",
        "pilot_url": "https://careers.aircanada.com/search/?q=pilot",
        "region": "north_america",
        "country": "Canada"
    },
    "westjet": {
        "name": "WestJet",
        "careers_url": "https://careers.westjet.com/",
        "pilot_url": "https://careers.westjet.com/search/?q=pilot",
        "region": "north_america",
        "country": "Canada"
    },
    "latam": {
        "name": "LATAM Airlines",
        "careers_url": "https://www.latamairlinesgroup.net/careers",
        "pilot_url": "https://careers.latam.com/",
        "region": "south_america",
        "country": "Chile"
    },
    "avianca": {
        "name": "Avianca",
        "careers_url": "https://www.avianca.com/otr/en/about-us/careers/",
        "pilot_url": "https://jobs.avianca.com/",
        "region": "south_america",
        "country": "Colombia"
    },

    # Europe - Flag Carriers
    "iberia": {
        "name": "Iberia",
        "careers_url": "https://careers.iberia.com/",
        "pilot_url": "https://careers.iberia.com/jobs?department=pilots",
        "region": "europe",
        "country": "Spain"
    },
    "tap_portugal": {
        "name": "TAP Air Portugal",
        "careers_url": "https://www.flytap.com/en-pt/careers",
        "pilot_url": "https://jobs.flytap.com/",
        "region": "europe",
        "country": "Portugal"
    },
    "aer_lingus": {
        "name": "Aer Lingus",
        "careers_url": "https://careers.aerlingus.com/",
        "pilot_url": "https://careers.aerlingus.com/go/Pilots/4656301/",
        "region": "europe",
        "country": "Ireland"
    },
    "lot_polish": {
        "name": "LOT Polish Airlines",
        "careers_url": "https://www.lot.com/pl/en/career",
        "pilot_url": "https://career.lot.com/",
        "region": "europe",
        "country": "Poland"
    },
    "icelandair": {
        "name": "Icelandair",
        "careers_url": "https://www.icelandairgroup.is/careers/",
        "pilot_url": "https://jobs.icelandairgroup.is/",
        "region": "europe",
        "country": "Iceland"
    },
    "air_baltic": {
        "name": "airBaltic",
        "careers_url": "https://careers.airbaltic.com/",
        "pilot_url": "https://careers.airbaltic.com/en/vacancies/pilots/",
        "region": "europe",
        "country": "Latvia"
    },
}

# ============================================================
# RECRUITMENT AGENCIES - They handle placements for many airlines
# These are legitimate sources of contract jobs
# ============================================================
RECRUITMENT_AGENCIES = {
    "rishworth": {
        "name": "Rishworth Aviation",
        "url": "https://www.rishworthaviation.com/",
        "jobs_url": "https://www.rishworthaviation.com/pilot-jobs/",
        "api_pattern": "https://www.rishworthaviation.com/job/",
        "notes": "Major expat pilot recruiter - Vietnam Airlines, Air Peace, etc."
    },
    "parc_aviation": {
        "name": "PARC Aviation",
        "url": "https://www.parcaviation.aero/",
        "jobs_url": "https://www.parcaviation.aero/jobs/",
        "notes": "European pilot recruitment"
    },
    "osm_aviation": {
        "name": "OSM Aviation",
        "url": "https://www.osm-aviation.com/",
        "jobs_url": "https://www.osm-aviation.com/pilots/",
        "notes": "Nordic pilot recruiter"
    },
    "cae": {
        "name": "CAE",
        "url": "https://www.cae.com/",
        "jobs_url": "https://www.cae.com/careers/",
        "notes": "Training and placement programs"
    },
    "aerviva": {
        "name": "Aerviva",
        "url": "https://www.aerviva.com/",
        "jobs_url": "https://www.aerviva.com/jobs/",
        "notes": "Irish recruitment agency"
    },
    "balpa_jobs": {
        "name": "BALPA Flight Deck",
        "url": "https://www.balpa.org/",
        "jobs_url": "https://www.balpa.org/careers/flight-deck-jobs/",
        "notes": "British pilot union job board"
    },
}

# ============================================================
# AGGREGATED DATA STRUCTURE (Used by orchestrator)
# ============================================================
AIRLINES_BY_ATS = {
    'taleo': TALEO_AIRLINES,
    'workday': WORKDAY_AIRLINES,
    'successfactors': SUCCESSFACTORS_AIRLINES,
    'direct': DIRECT_CAREER_PAGES,
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_airlines():
    """Return all airlines as a list with ats_type added to each"""
    all_airlines = []

    for airline_key, config in TALEO_AIRLINES.items():
        all_airlines.append({**config, 'ats_type': 'taleo', 'key': airline_key})

    for airline_key, config in WORKDAY_AIRLINES.items():
        all_airlines.append({**config, 'ats_type': 'workday', 'key': airline_key})

    for airline_key, config in SUCCESSFACTORS_AIRLINES.items():
        all_airlines.append({**config, 'ats_type': 'successfactors', 'key': airline_key})

    for airline_key, config in DIRECT_CAREER_PAGES.items():
        all_airlines.append({**config, 'ats_type': 'direct', 'key': airline_key})

    return all_airlines

def get_airlines_by_region(region: str):
    """Filter airlines by region"""
    all_airlines = get_all_airlines()
    return [a for a in all_airlines if a.get('region') == region]

def get_airlines_by_ats(ats_type: str):
    """Get airlines using a specific ATS as a list"""
    ats_map = {
        'taleo': TALEO_AIRLINES,
        'workday': WORKDAY_AIRLINES,
        'successfactors': SUCCESSFACTORS_AIRLINES,
        'direct': DIRECT_CAREER_PAGES,
    }
    source = ats_map.get(ats_type, {})
    return [{**config, 'ats_type': ats_type, 'key': key} for key, config in source.items()]

# Print summary
if __name__ == "__main__":
    all_airlines = get_all_airlines()
    print(f"\nTotal airlines tracked: {len(all_airlines)}")
    print(f"  - Taleo ATS: {len(TALEO_AIRLINES)}")
    print(f"  - Workday ATS: {len(WORKDAY_AIRLINES)}")
    print(f"  - SuccessFactors ATS: {len(SUCCESSFACTORS_AIRLINES)}")
    print(f"  - Direct career pages: {len(DIRECT_CAREER_PAGES)}")
    print(f"  - Recruitment agencies: {len(RECRUITMENT_AGENCIES)}")

    print("\nAirlines by region:")
    regions = {}
    for airline in all_airlines:
        region = airline.get('region', 'unknown')
        regions[region] = regions.get(region, 0) + 1
    for region, count in sorted(regions.items()):
        print(f"  - {region}: {count}")

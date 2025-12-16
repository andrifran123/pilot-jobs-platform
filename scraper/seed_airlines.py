#!/usr/bin/env python3
"""Seed missing airlines into the database"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from supabase import create_client

client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

# All 56 airlines from the schema
all_airlines = [
    # Tier 1: Major Airlines
    ('Emirates', 'https://www.emiratesgroupcareers.com/pilots/', 'CUSTOM_AI', 1, 3, 'middle_east', 'United Arab Emirates', 'EK', 'UAE'),
    ('Qatar Airways', 'https://careers.qatarairways.com/global/en/c/pilots-jobs', 'CUSTOM_AI', 1, 3, 'middle_east', 'Qatar', 'QR', 'QTR'),
    ('Etihad Airways', 'https://www.etihad.com/en/careers/pilots', 'CUSTOM_AI', 1, 3, 'middle_east', 'United Arab Emirates', 'EY', 'ETD'),
    ('Ryanair', 'https://careers.ryanair.com/search/?q=pilot', 'CUSTOM_AI', 1, 3, 'europe', 'Ireland', 'FR', 'RYR'),
    ('easyJet', 'https://careers.easyjet.com/vacancies', 'CUSTOM_AI', 1, 3, 'europe', 'United Kingdom', 'U2', 'EZY'),
    ('Delta Air Lines', 'https://delta.avature.net/careers', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'DL', 'DAL'),
    ('United Airlines', 'https://careers.united.com/us/en/search-results', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'UA', 'UAL'),
    ('American Airlines', 'https://jobs.aa.com/search-jobs', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'AA', 'AAL'),
    ('Singapore Airlines', 'https://www.singaporeair.com/en_UK/sg/flying-withus/our-story/sia-careers/cabin-crew-pilots/', 'CUSTOM_AI', 1, 3, 'asia', 'Singapore', 'SQ', 'SIA'),
    ('Cathay Pacific', 'https://careers.cathaypacific.com/jobs', 'CUSTOM_AI', 1, 3, 'asia', 'Hong Kong', 'CX', 'CPA'),
    ('Lufthansa', 'https://www.be-lufthansa.com/en/themes/pilots', 'CUSTOM_AI', 1, 3, 'europe', 'Germany', 'LH', 'DLH'),
    ('British Airways', 'https://careers.ba.com/pilots', 'CUSTOM_AI', 1, 3, 'europe', 'United Kingdom', 'BA', 'BAW'),

    # Tier 2: Medium Airlines
    ('Wizz Air', 'https://wizzair.com/en-gb/information-and-services/about-us/careers/pilot-jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Hungary', 'W6', 'WZZ'),
    ('flydubai', 'https://careers.flydubai.com/jobs', 'CUSTOM_AI', 2, 12, 'middle_east', 'United Arab Emirates', 'FZ', 'FDB'),
    ('Air France', 'https://recrutement.airfranceklm.com/en/pilot', 'CUSTOM_AI', 2, 12, 'europe', 'France', 'AF', 'AFR'),
    ('KLM', 'https://careers.klm.com/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Netherlands', 'KL', 'KLM'),
    ('SWISS', 'https://www.swiss.com/ch/en/career/pilots', 'CUSTOM_AI', 2, 12, 'europe', 'Switzerland', 'LX', 'SWR'),
    ('Qantas', 'https://www.qantas.com/au/en/about-us/qantas-careers/pilots.html', 'CUSTOM_AI', 2, 12, 'oceania', 'Australia', 'QF', 'QFA'),
    ('Virgin Atlantic', 'https://careers.virginatlantic.com/global/en/pilots', 'CUSTOM_AI', 2, 12, 'europe', 'United Kingdom', 'VS', 'VIR'),
    ('Turkish Airlines', 'https://www.turkishairlines.com/en-int/corporate/career/pilot-recruitment/', 'CUSTOM_AI', 2, 12, 'europe', 'Turkey', 'TK', 'THY'),
    ('Iberia', 'https://careers.iberia.com/pilots', 'CUSTOM_AI', 2, 12, 'europe', 'Spain', 'IB', 'IBE'),
    ('Vueling', 'https://careers.vueling.com/pilots', 'CUSTOM_AI', 2, 12, 'europe', 'Spain', 'VY', 'VLG'),
    ('Norwegian', 'https://www.norwegian.com/en/about/careers/pilots/', 'CUSTOM_AI', 2, 12, 'europe', 'Norway', 'DY', 'NAX'),
    ('JetBlue', 'https://careers.jetblue.com/pilots', 'CUSTOM_AI', 2, 12, 'north_america', 'United States', 'B6', 'JBU'),
    ('Southwest Airlines', 'https://careers.southwestair.com/career-areas/pilots', 'CUSTOM_AI', 2, 12, 'north_america', 'United States', 'WN', 'SWA'),
    ('Air Canada', 'https://careers.aircanada.com/pilots', 'CUSTOM_AI', 2, 12, 'north_america', 'Canada', 'AC', 'ACA'),
    ('Japan Airlines', 'https://www.job-jal.com/english/pilot/', 'CUSTOM_AI', 2, 12, 'asia', 'Japan', 'JL', 'JAL'),
    ('ANA', 'https://www.anahd.co.jp/group/en/recruit/pilot/', 'CUSTOM_AI', 2, 12, 'asia', 'Japan', 'NH', 'ANA'),
    ('Korean Air', 'https://recruit.koreanair.com/en/pilot', 'CUSTOM_AI', 2, 12, 'asia', 'South Korea', 'KE', 'KAL'),
    ('Thai Airways', 'https://www.thaiairways.com/en_TH/news/pilot_recruitment.page', 'CUSTOM_AI', 2, 12, 'asia', 'Thailand', 'TG', 'THA'),
    ('Malaysia Airlines', 'https://careers.malaysiaairlines.com/pilots', 'CUSTOM_AI', 2, 12, 'asia', 'Malaysia', 'MH', 'MAS'),
    ('Rishworth Aviation', 'https://www.rishworthaviation.com/vacancies/', 'CUSTOM_AI', 2, 12, 'global', None, None, None),
    ('PARC Aviation', 'https://www.parcaviation.aero/pilot-jobs', 'CUSTOM_AI', 2, 12, 'global', None, None, None),
    ('Goose Recruitment', 'https://www.goose.aero/jobs', 'CUSTOM_AI', 2, 12, 'global', None, None, None),
    ('CAE Parc', 'https://www.caeparc.com/pilots', 'CUSTOM_AI', 2, 12, 'global', None, None, None),
    ('OSM Aviation', 'https://osmaviationacademy.com/careers/', 'CUSTOM_AI', 2, 12, 'global', None, None, None),

    # Tier 3: Smaller/Regional Airlines
    ('SAS', 'https://www.flysas.com/en/about-us/jobs/pilots/', 'CUSTOM_AI', 3, 24, 'europe', 'Sweden', 'SK', 'SAS'),
    ('Finnair', 'https://careers.finnair.com/pilots', 'CUSTOM_AI', 3, 24, 'europe', 'Finland', 'AY', 'FIN'),
    ('LOT Polish', 'https://career.lot.com/pilot', 'CUSTOM_AI', 3, 24, 'europe', 'Poland', 'LO', 'LOT'),
    ('TAP Air Portugal', 'https://careers.flytap.com/pilots', 'CUSTOM_AI', 3, 24, 'europe', 'Portugal', 'TP', 'TAP'),
    ('Aer Lingus', 'https://careers.aerlingus.com/pilots', 'CUSTOM_AI', 3, 24, 'europe', 'Ireland', 'EI', 'EIN'),
    ('ITA Airways', 'https://www.itaspa.com/en/careers', 'CUSTOM_AI', 3, 24, 'europe', 'Italy', 'AZ', 'ITY'),
    ('Eurowings', 'https://www.be-lufthansa.com/en/eurowings', 'CUSTOM_AI', 3, 24, 'europe', 'Germany', 'EW', 'EWG'),
    ('Austrian Airlines', 'https://www.austrian.com/at/en/about-us/career/pilots', 'CUSTOM_AI', 3, 24, 'europe', 'Austria', 'OS', 'AUA'),
    ('Brussels Airlines', 'https://careers.brusselsairlines.com/pilots', 'CUSTOM_AI', 3, 24, 'europe', 'Belgium', 'SN', 'BEL'),
    ('Saudia', 'https://www.saudia.com/about-us/careers', 'CUSTOM_AI', 3, 24, 'middle_east', 'Saudi Arabia', 'SV', 'SVA'),
    ('Gulf Air', 'https://www.gulfair.com/about-gulf-air/careers', 'CUSTOM_AI', 3, 24, 'middle_east', 'Bahrain', 'GF', 'GFA'),
    ('Oman Air', 'https://www.omanair.com/en/about-us/careers', 'CUSTOM_AI', 3, 24, 'middle_east', 'Oman', 'WY', 'OMA'),
    ('Kuwait Airways', 'https://www.kuwaitairways.com/en/careers', 'CUSTOM_AI', 3, 24, 'middle_east', 'Kuwait', 'KU', 'KAC'),
    ('Air India', 'https://www.airindia.com/in/en/careers.html', 'CUSTOM_AI', 3, 24, 'asia', 'India', 'AI', 'AIC'),
    ('IndiGo', 'https://www.goindigo.in/information/career.html', 'CUSTOM_AI', 3, 24, 'asia', 'India', '6E', 'IGO'),
    ('Garuda Indonesia', 'https://career.garuda-indonesia.com/', 'CUSTOM_AI', 3, 24, 'asia', 'Indonesia', 'GA', 'GIA'),
    ('Philippine Airlines', 'https://www.philippineairlines.com/about-us/careers', 'CUSTOM_AI', 3, 24, 'asia', 'Philippines', 'PR', 'PAL'),
    ('Cebu Pacific', 'https://www.cebupacificair.com/pages/about-us/careers', 'CUSTOM_AI', 3, 24, 'asia', 'Philippines', '5J', 'CEB'),
    ('AirAsia', 'https://www.airasia.com/aa/about-us/en/gb/our-people.page', 'CUSTOM_AI', 3, 24, 'asia', 'Malaysia', 'AK', 'AXM'),
    ('Jetstar', 'https://www.jetstar.com/au/en/about-us/careers', 'CUSTOM_AI', 3, 24, 'oceania', 'Australia', 'JQ', 'JST'),
    ('Air New Zealand', 'https://careers.airnewzealand.co.nz/pilots', 'CUSTOM_AI', 3, 24, 'oceania', 'New Zealand', 'NZ', 'ANZ'),
    ('LATAM', 'https://www.latamairlines.com/us/en/careers', 'CUSTOM_AI', 3, 24, 'south_america', 'Chile', 'LA', 'LAN'),
    ('Avianca', 'https://www.avianca.com/us/en/about-us/careers/', 'CUSTOM_AI', 3, 24, 'south_america', 'Colombia', 'AV', 'AVA'),
    ('Copa Airlines', 'https://careers.copaair.com/pilots', 'CUSTOM_AI', 3, 24, 'south_america', 'Panama', 'CM', 'CMP'),
    ('Ethiopian Airlines', 'https://www.ethiopianairlines.com/aa/about-us/careers', 'CUSTOM_AI', 3, 24, 'africa', 'Ethiopia', 'ET', 'ETH'),
    ('South African Airways', 'https://www.flysaa.com/about-us/careers', 'CUSTOM_AI', 3, 24, 'africa', 'South Africa', 'SA', 'SAA'),
    ('EgyptAir', 'https://www.egyptair.com/en/AboutEgyptAir/careers/Pages/default.aspx', 'CUSTOM_AI', 3, 24, 'africa', 'Egypt', 'MS', 'MSR'),
    ('Royal Air Maroc', 'https://www.royalairmaroc.com/ma-en/careers', 'CUSTOM_AI', 3, 24, 'africa', 'Morocco', 'AT', 'RAM'),
]

print(f"Processing {len(all_airlines)} airlines...")

inserted = 0
updated = 0
skipped = 0

for airline in all_airlines:
    name = airline[0]
    data = {
        'name': name,
        'career_page_url': airline[1],
        'ats_type': airline[2],
        'tier': airline[3],
        'scrape_frequency_hours': airline[4],
        'region': airline[5],
        'country': airline[6],
        'iata_code': airline[7],
        'icao_code': airline[8]
    }

    try:
        # Check if exists
        existing = client.table('airlines_to_scrape').select('id, career_page_url').eq('name', name).execute()

        if existing.data:
            # Update URL if different
            if existing.data[0]['career_page_url'] != airline[1]:
                client.table('airlines_to_scrape').update({
                    'career_page_url': airline[1],
                    'ats_type': airline[2]
                }).eq('name', name).execute()
                print(f"  ~ {name} (URL updated)")
                updated += 1
            else:
                skipped += 1
        else:
            # Insert new
            client.table('airlines_to_scrape').insert(data).execute()
            print(f"  + {name}")
            inserted += 1

    except Exception as e:
        print(f"  x {name}: {str(e)[:60]}")

print(f"\n{'='*50}")
print(f"Results: {inserted} inserted, {updated} updated, {skipped} unchanged")

# Final count
result = client.table('airlines_to_scrape').select('id', count='exact').execute()
print(f"Total airlines in database: {result.count}")

# Show by tier
tiers = client.table('airlines_to_scrape').select('tier').execute()
tier_counts = {}
for t in tiers.data:
    tier_counts[t['tier']] = tier_counts.get(t['tier'], 0) + 1

print(f"\nBy Tier:")
for tier in sorted(tier_counts.keys()):
    print(f"  Tier {tier}: {tier_counts[tier]} airlines")

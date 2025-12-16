"""
Job Data Normalizer

Different airlines describe the same jobs in different ways:
- "First Officer A320" vs "A320 F/O" vs "Co-Pilot Airbus 320"
- "Captain B737" vs "B737 Commander" vs "PIC Boeing 737"

This normalizer standardizes everything into a consistent format.
"""

import re
from typing import Dict, Optional, Tuple
from rapidfuzz import fuzz, process

# ============================================================
# AIRCRAFT STANDARDIZATION
# ============================================================

AIRCRAFT_ALIASES = {
    # Airbus narrowbody
    'a318': 'A318', 'airbus 318': 'A318', 'a-318': 'A318',
    'a319': 'A319', 'airbus 319': 'A319', 'a-319': 'A319',
    'a320': 'A320', 'airbus 320': 'A320', 'a-320': 'A320', 'a320neo': 'A320neo', 'a320 neo': 'A320neo',
    'a321': 'A321', 'airbus 321': 'A321', 'a-321': 'A321', 'a321neo': 'A321neo', 'a321xlr': 'A321XLR',
    'a32x': 'A320 Family', 'a320 family': 'A320 Family', 'a319/320/321': 'A320 Family',

    # Airbus widebody
    'a330': 'A330', 'airbus 330': 'A330', 'a-330': 'A330',
    'a340': 'A340', 'airbus 340': 'A340', 'a-340': 'A340',
    'a350': 'A350', 'airbus 350': 'A350', 'a-350': 'A350', 'a350xwb': 'A350',
    'a380': 'A380', 'airbus 380': 'A380', 'a-380': 'A380',

    # Boeing narrowbody
    'b737': 'B737', 'boeing 737': 'B737', '737': 'B737', 'b-737': 'B737',
    '737ng': 'B737NG', 'b737ng': 'B737NG', '737-800': 'B737NG', '737-900': 'B737NG',
    '737max': 'B737MAX', 'b737max': 'B737MAX', '737 max': 'B737MAX',
    '737 classic': 'B737 Classic', 'b737 classic': 'B737 Classic',

    # Boeing widebody
    'b747': 'B747', 'boeing 747': 'B747', '747': 'B747', 'b-747': 'B747', 'jumbo': 'B747',
    'b757': 'B757', 'boeing 757': 'B757', '757': 'B757',
    'b767': 'B767', 'boeing 767': 'B767', '767': 'B767',
    'b777': 'B777', 'boeing 777': 'B777', '777': 'B777', 'triple seven': 'B777',
    'b787': 'B787', 'boeing 787': 'B787', '787': 'B787', 'dreamliner': 'B787',

    # Embraer
    'e170': 'E170', 'embraer 170': 'E170', 'erj 170': 'E170',
    'e175': 'E175', 'embraer 175': 'E175', 'erj 175': 'E175',
    'e190': 'E190', 'embraer 190': 'E190', 'erj 190': 'E190',
    'e195': 'E195', 'embraer 195': 'E195', 'erj 195': 'E195',
    'e2': 'E2', 'e190-e2': 'E190-E2', 'e195-e2': 'E195-E2',

    # Regional jets
    'crj': 'CRJ', 'crj200': 'CRJ200', 'crj700': 'CRJ700', 'crj900': 'CRJ900',
    'atr': 'ATR', 'atr42': 'ATR 42', 'atr72': 'ATR 72', 'atr 42': 'ATR 42', 'atr 72': 'ATR 72',
    'dash 8': 'Dash 8', 'q400': 'Dash 8 Q400', 'dhc-8': 'Dash 8',
    'saab 340': 'Saab 340', 'sf340': 'Saab 340',

    # Business jets
    'citation': 'Citation', 'cessna citation': 'Citation',
    'learjet': 'Learjet', 'lear jet': 'Learjet',
    'gulfstream': 'Gulfstream', 'g550': 'Gulfstream G550', 'g650': 'Gulfstream G650',
    'global': 'Bombardier Global', 'global 7500': 'Global 7500',
    'challenger': 'Challenger', 'challenger 350': 'Challenger 350',
    'falcon': 'Dassault Falcon', 'falcon 900': 'Falcon 900', 'falcon 7x': 'Falcon 7X',
    'phenom': 'Embraer Phenom', 'phenom 300': 'Phenom 300',
    'pc-12': 'PC-12', 'pilatus pc-12': 'PC-12', 'pc12': 'PC-12',
    'pc-24': 'PC-24', 'pilatus pc-24': 'PC-24',
    'tbm': 'TBM', 'tbm 900': 'TBM 900', 'tbm 940': 'TBM 940',
}

# ============================================================
# POSITION STANDARDIZATION
# ============================================================

POSITION_PATTERNS = {
    'captain': [
        r'\bcaptain\b', r'\bcommander\b', r'\bpic\b', r'\bp\.i\.c\.?\b',
        r'\bleft\s*seat\b', r'\bcommand\b(?!.*course)',
    ],
    'first_officer': [
        r'\bfirst\s*officer\b', r'\bf/?o\b', r'\bco-?pilot\b',
        r'\bsecond\s*in\s*command\b', r'\bsic\b', r'\bright\s*seat\b',
        r'\bsenior\s*first\s*officer\b', r'\bjunior\s*first\s*officer\b',
    ],
    'second_officer': [
        r'\bsecond\s*officer\b', r'\bs/?o\b', r'\bcruise\s*(?:relief\s*)?pilot\b',
        r'\brelief\s*pilot\b',
    ],
    'cadet': [
        r'\bcadet\b', r'\bab[\s-]*initio\b', r'\btrainee\b',
        r'\bmentor(?:ed)?\s*program\b', r'\bpathway\b',
    ],
    'instructor': [
        r'\binstructor\b', r'\btri\b', r'\btre\b', r'\bsfi\b',
        r'\btraining\s*captain\b', r'\bcheck\s*(?:pilot|airman)\b',
    ],
}

# ============================================================
# LICENSE STANDARDIZATION
# ============================================================

LICENSE_PATTERNS = {
    'ATPL': [r'\batpl\b', r'\bairline\s*transport\b'],
    'Frozen ATPL': [r'\bf(?:rozen\s*)?atpl\b', r'\bfatpl\b'],
    'CPL': [r'\bcpl\b', r'\bcommercial\s*pilot\b'],
    'MPL': [r'\bmpl\b', r'\bmulti[\s-]*crew\s*pilot\b'],
    'PPL': [r'\bppl\b', r'\bprivate\s*pilot\b'],
}

REGULATORY_PATTERNS = {
    'EASA': [r'\beasa\b', r'\beuropean\b'],
    'FAA': [r'\bfaa\b', r'\b14\s*cfr\b'],
    'UK CAA': [r'\buk\s*caa\b', r'\bcaa\s*uk\b'],
    'ICAO': [r'\bicao\b'],
    'CASA': [r'\bcasa\b', r'\baustralian\b'],
    'TCCA': [r'\btcca\b', r'\btransport\s*canada\b'],
    'GCAA': [r'\bgcaa\b', r'\buae\b'],
    'CAAS': [r'\bcaas\b', r'\bsingapore\b'],
}

# ============================================================
# NORMALIZER CLASS
# ============================================================

class JobNormalizer:
    """Normalizes job data into consistent format"""

    def normalize_job(self, job: Dict) -> Dict:
        """
        Normalize a job dictionary.

        Args:
            job: Raw job data from scraper

        Returns:
            Normalized job data
        """
        normalized = job.copy()

        # Normalize title and extract info
        title = job.get('title', '')
        normalized['original_title'] = title

        # Extract and normalize position type
        normalized['position_type'] = self.extract_position_type(title)

        # Extract and normalize aircraft type
        aircraft = self.extract_aircraft(title + ' ' + job.get('description', ''))
        normalized['aircraft_type'] = aircraft['type']
        normalized['aircraft_category'] = aircraft['category']

        # Clean up the title
        normalized['title'] = self.clean_title(title)

        # Normalize location
        normalized['location'] = self.normalize_location(job.get('location', ''))

        # Extract requirements from description
        requirements = self.extract_requirements(job.get('description', ''))
        normalized.update(requirements)

        # Normalize license requirements
        normalized['license_required'] = self.extract_license(
            job.get('description', '') + ' ' + title
        )

        # Determine contract type
        normalized['contract_type'] = self.extract_contract_type(job)

        return normalized

    def extract_position_type(self, title: str) -> str:
        """Extract position type from job title"""
        title_lower = title.lower()

        for position, patterns in POSITION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    return position

        # Default to first_officer if pilot-related but unclear
        if any(kw in title_lower for kw in ['pilot', 'flight crew']):
            return 'first_officer'

        return 'other'

    def extract_aircraft(self, text: str) -> Dict:
        """Extract aircraft type from text"""
        text_lower = text.lower()

        # Direct match
        for alias, standard in AIRCRAFT_ALIASES.items():
            if alias in text_lower:
                return {
                    'type': standard,
                    'category': self._get_aircraft_category(standard)
                }

        # Fuzzy match for aircraft mentions
        aircraft_pattern = r'(?:a|b|e)?-?\d{3}(?:ng|max|neo|xlr)?'
        matches = re.findall(aircraft_pattern, text_lower)

        for match in matches:
            normalized = match.upper().replace('-', '')
            # Check if it looks like an aircraft
            if normalized in AIRCRAFT_ALIASES.values():
                return {
                    'type': normalized,
                    'category': self._get_aircraft_category(normalized)
                }

        return {'type': 'Various', 'category': 'unknown'}

    def _get_aircraft_category(self, aircraft: str) -> str:
        """Determine aircraft category"""
        aircraft_upper = aircraft.upper()

        narrowbody = ['A318', 'A319', 'A320', 'A321', 'B737', 'A320 Family']
        widebody = ['A330', 'A340', 'A350', 'A380', 'B747', 'B757', 'B767', 'B777', 'B787']
        regional = ['E170', 'E175', 'E190', 'E195', 'CRJ', 'ATR', 'Dash 8', 'Saab']
        turboprop = ['ATR', 'Dash 8', 'Saab 340', 'PC-12']
        business = ['Citation', 'Learjet', 'Gulfstream', 'Global', 'Challenger', 'Falcon', 'Phenom']

        for nb in narrowbody:
            if nb in aircraft_upper:
                return 'narrowbody'
        for wb in widebody:
            if wb in aircraft_upper:
                return 'widebody'
        for rj in regional:
            if rj in aircraft_upper:
                return 'regional'
        for tp in turboprop:
            if tp in aircraft_upper:
                return 'turboprop'
        for bj in business:
            if bj in aircraft_upper:
                return 'business'

        return 'unknown'

    def clean_title(self, title: str) -> str:
        """Clean up job title to be more readable"""
        # Remove excessive whitespace
        title = ' '.join(title.split())

        # Standardize common abbreviations
        replacements = [
            (r'\bF/?O\b', 'First Officer'),
            (r'\bCpt\.?\b', 'Captain'),
            (r'\bCapt\.?\b', 'Captain'),
            (r'\bCo-?Pilot\b', 'First Officer'),
            (r'\bSFO\b', 'Senior First Officer'),
            (r'\bTR\b', 'Type Rated'),
            (r'\bNTR\b', 'Non-Type Rated'),
            (r'\bDE\b', 'Direct Entry'),
        ]

        for pattern, replacement in replacements:
            title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)

        return title.strip()

    def normalize_location(self, location: str) -> str:
        """Normalize location string"""
        if not location:
            return 'Multiple Locations'

        # Clean up
        location = ' '.join(location.split())

        # Remove common prefixes
        location = re.sub(r'^(?:based\s*(?:in|at)?|location:)\s*', '', location, flags=re.IGNORECASE)

        return location.strip() or 'Multiple Locations'

    def extract_requirements(self, description: str) -> Dict:
        """Extract flight hour requirements from description"""
        requirements = {
            'min_total_hours': None,
            'min_pic_hours': None,
            'min_type_hours': None,
            'min_multi_hours': None,
            'type_rating_required': False,
            'type_rating_provided': False,
            'visa_sponsorship': False,
            'is_entry_level': False,
            'tags': [],
        }

        if not description:
            return requirements

        # Clean the text - handle non-breaking spaces, normalize whitespace
        # This is critical for multi-line job postings where "2000" is on one line
        # and "hours" is on the next line due to HTML rendering
        clean_text = description.replace('\u00A0', ' ').replace('\r', '\n')
        desc_lower = clean_text.lower()

        # =================================================================
        # MULTI-LINE HOUR EXTRACTION
        # The \s* matches ANY whitespace including newlines, so patterns like:
        #   "2000
        #    hours"
        # will correctly match even with HTML line breaks between them
        # =================================================================

        # Total hours - "Super Regex" that handles multi-line text
        # Pattern: number (3-5 digits) + optional "+" + whitespace/newlines + hours/hrs/total time
        total_patterns = [
            r'(\d{3,5})\+?\s*(?:hrs?|hours?|total\s*flying\s*time|total\s*time)',
            r'(\d{3,5})\s*\+?\s*(?:hours?|hrs?)?\s*(?:total|tt|total\s*time|total\s*flight)',
            r'total\s*(?:time|hours?|flight)[\s:]*(\d{3,5})',
            r'minimum\s*(?:of\s*)?(\d{3,5})\s*(?:hours?|hrs?)',
            r'(\d{3,5})\s*(?:hours?|hrs?)\s*(?:minimum|required)',
        ]

        for pattern in total_patterns:
            match = re.search(pattern, desc_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                hours = int(match.group(1))
                if 100 <= hours <= 25000:  # Reasonable range
                    requirements['min_total_hours'] = hours
                    break

        # PIC hours - also multi-line aware
        pic_patterns = [
            r'(\d{3,5})\+?\s*(?:hrs?|hours?)?\s*(?:pic|command|p\.i\.c)',
            r'(?:pic|command|p\.i\.c)[\s:]*(\d{3,5})',
            r'(\d{3,5})\s*(?:hours?|hrs?)\s*(?:in\s*command|as\s*pic)',
        ]

        for pattern in pic_patterns:
            match = re.search(pattern, desc_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                hours = int(match.group(1))
                if 100 <= hours <= 15000:
                    requirements['min_pic_hours'] = hours
                    break

        # Type hours - also multi-line aware
        type_patterns = [
            r'(\d{2,5})\+?\s*(?:hrs?|hours?)?\s*(?:on\s*type|type)',
            r'(?:on\s*type|type\s*hours?)[\s:]*(\d{2,5})',
            r'(\d{2,5})\s*(?:hours?|hrs?)\s*on\s*(?:the\s*)?type',
        ]

        for pattern in type_patterns:
            match = re.search(pattern, desc_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                hours = int(match.group(1))
                if 50 <= hours <= 10000:
                    requirements['min_type_hours'] = hours
                    break

        # Type rating required
        if any(re.search(p, desc_lower) for p in [
            r'type\s*rat(?:ed|ing)\s*(?:is\s*)?required',
            r'must\s*(?:have|hold).*type\s*rat',
            r'current\s*(?:and\s*valid\s*)?type\s*rat',
            r'valid\s*type\s*rating\s*(?:on|for)',
        ]):
            requirements['type_rating_required'] = True

        # Type rating provided
        if any(re.search(p, desc_lower) for p in [
            r'type\s*rat(?:ed|ing).*(?:will\s*be\s*)?provided',
            r'(?:we\s*)?(?:will\s*)?provide.*type\s*rat',
            r'training\s*(?:will\s*be\s*)?provided',
            r'non[\s-]*type[\s-]*rated.*(?:welcome|accepted|considered)',
        ]):
            requirements['type_rating_provided'] = True

        # Visa sponsorship detection
        visa_patterns = [
            r'visa\s*(?:sponsorship|sponsored|support)',
            r'sponsor(?:ed|ship)?\s*(?:for\s*)?visa',
            r'work\s*permit\s*(?:provided|sponsored|support)',
            r'relocation\s*(?:assistance|support|package)',
            r'will\s*sponsor',
            r'sponsorship\s*(?:is\s*)?available',
            r'international\s*(?:candidates?|applicants?)\s*(?:welcome|considered|accepted)',
            r'no\s*(?:visa|work\s*permit)\s*restrictions',
        ]
        if any(re.search(p, desc_lower) for p in visa_patterns):
            requirements['visa_sponsorship'] = True
            requirements['tags'].append('Visa Sponsored')

        # Commuting/Home-based detection
        commute_patterns = [
            r'home[\s-]*bas(?:ed|ing)',
            r'commut(?:ing|er)\s*(?:contract|roster|pattern)',
            r'roster[\s:]*\d+[\s/]+\d+',  # e.g., "roster: 5/4" or "5/2 pattern"
            r'days?\s*(?:on|off)[\s/:]+\d+',
        ]
        if any(re.search(p, desc_lower) for p in commute_patterns):
            requirements['tags'].append('Commuting Contract')

        # =================================================================
        # ENTRY LEVEL DETECTION - Conservative Approach
        # Only mark as entry-level with HIGH CONFIDENCE to protect reputation
        # It's better to show "Unknown" than incorrectly label a Captain job
        # =================================================================
        min_hours = requirements['min_total_hours']

        # HIGH CONFIDENCE: Explicit low hour requirement extracted from text
        if min_hours is not None and min_hours < 500:
            requirements['is_entry_level'] = True
            requirements['tags'].append('Entry Level')

        # NOTE: We removed the "type rating provided = entry level" assumption
        # A Captain position can have type rating provided but still require
        # 5000+ hours. Don't guess without evidence.

        # HIGH CONFIDENCE: Explicit cadet/trainee keywords
        if any(re.search(p, desc_lower) for p in [
            r'\bcadet\b', r'\bab[\s-]*initio\b', r'\btrainee\b',
            r'no\s*(?:prior\s*)?experience\s*(?:required|needed|necessary)',
            r'zero[\s-]*(?:hour|time|experience)',
            r'low[\s-]*hour',
        ]):
            requirements['is_entry_level'] = True
            if 'Entry Level' not in requirements['tags']:
                requirements['tags'].append('Entry Level')

        return requirements

    def extract_license(self, text: str) -> str:
        """Extract license requirements"""
        text_lower = text.lower()
        licenses = []
        regulators = []

        # Find license types
        for license_type, patterns in LICENSE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    licenses.append(license_type)
                    break

        # Find regulatory body
        for regulator, patterns in REGULATORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    regulators.append(regulator)
                    break

        # Build license string
        if licenses and regulators:
            return f"{regulators[0]} {licenses[0]}"
        elif licenses:
            return licenses[0]
        elif regulators:
            return f"{regulators[0]} ATPL/CPL"
        else:
            return "ATPL/CPL"

    def extract_contract_type(self, job: Dict) -> str:
        """Determine contract type"""
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()

        if any(kw in text for kw in ['permanent', 'full-time', 'full time', 'direct hire']):
            return 'permanent'
        if any(kw in text for kw in ['contract', 'fixed term', 'fixed-term', 'temporary']):
            return 'contract'
        if any(kw in text for kw in ['seasonal', 'summer', 'winter']):
            return 'seasonal'
        if any(kw in text for kw in ['freelance', 'part-time', 'part time']):
            return 'freelance'

        return 'permanent'  # Default assumption


# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":
    normalizer = JobNormalizer()

    # Test cases - including multi-line scenarios
    test_jobs = [
        {
            'title': 'F/O A320 - Direct Entry',
            'description': 'Minimum 1500 hours total time, 500 hours on type. Type rating required. EASA ATPL.',
            'location': 'Based in Dublin, Ireland'
        },
        {
            'title': 'B737NG Captain - Seasonal Contract',
            'description': '4000+ TT, 1000 PIC on type. Valid EASA type rating.',
            'location': 'Warsaw'
        },
        {
            'title': 'Ab-Initio Cadet Pilot Programme',
            'description': 'No experience required. Full training provided including type rating. Visa sponsorship available.',
            'location': 'Singapore'
        },
        # Multi-line test case - simulates HTML rendering where number and "hours" are separated
        {
            'title': 'First Officer B777 - Dubai',
            'description': '''Requirements:
            2000
            hours total time
            500
            hours PIC
            Visa sponsorship provided.
            Relocation assistance included.''',
            'location': 'Dubai, UAE'
        },
        # Non-breaking space test case
        {
            'title': 'Captain A350 - Qatar',
            'description': 'Minimum 5000\u00A0hours total flight time. 2500\u00A0hours PIC required.',
            'location': 'Doha'
        },
    ]

    for job in test_jobs:
        normalized = normalizer.normalize_job(job)
        print(f"\n{'='*60}")
        print(f"Original: {job['title']}")
        print(f"Normalized: {normalized['title']}")
        print(f"Position: {normalized['position_type']}")
        print(f"Aircraft: {normalized['aircraft_type']} ({normalized['aircraft_category']})")
        print(f"Hours: {normalized['min_total_hours']} total, {normalized['min_pic_hours']} PIC, {normalized.get('min_type_hours')} type")
        print(f"Type Rating: Required={normalized['type_rating_required']}, Provided={normalized['type_rating_provided']}")
        print(f"Entry Level: {normalized['is_entry_level']}")
        print(f"Visa Sponsorship: {normalized['visa_sponsorship']}")
        print(f"Tags: {normalized['tags']}")
        print(f"License: {normalized['license_required']}")

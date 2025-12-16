export interface PilotJob {
  id: string;
  title: string;
  company: string;
  location: string;
  region: string;
  position_type: 'captain' | 'first_officer' | 'cadet' | 'instructor' | 'other';
  aircraft_type: string;
  type_rating_required: boolean;
  type_rating_provided: boolean;
  min_total_hours: number | null;
  min_pic_hours: number | null;
  min_type_hours: number | null;
  license_required: string;
  visa_sponsorship: boolean;
  is_entry_level: boolean;
  tags: string[];
  contract_type: 'permanent' | 'contract' | 'seasonal' | 'freelance';
  salary_info: string | null;
  benefits: string | null;
  description: string;
  application_url: string;
  source: string;
  date_posted: string;
  date_scraped: string;
  is_active: boolean;
}

export interface JobFilters {
  search: string;
  position_type: string[];
  region: string[];
  type_rating_required: boolean | null;
  max_hours_required: number | null;
  contract_type: string[];
  aircraft_category: string[];
  visa_sponsorship: boolean | null;
  is_entry_level: boolean | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  total_hours: number | null;
  pic_hours: number | null;
  licenses: string[];
  type_ratings: string[];
  preferred_regions: string[];
  created_at: string;
}

export type Region =
  | 'europe'
  | 'middle_east'
  | 'asia'
  | 'africa'
  | 'oceania'
  | 'north_america'
  | 'south_america'
  | 'caribbean';

export const REGIONS: { value: Region; label: string }[] = [
  { value: 'europe', label: 'Europe' },
  { value: 'middle_east', label: 'Middle East' },
  { value: 'asia', label: 'Asia Pacific' },
  { value: 'africa', label: 'Africa' },
  { value: 'oceania', label: 'Australia/NZ' },
  { value: 'north_america', label: 'North America' },
  { value: 'south_america', label: 'South America' },
  { value: 'caribbean', label: 'Caribbean' },
];

export const POSITION_TYPES = [
  { value: 'captain', label: 'Captain' },
  { value: 'first_officer', label: 'First Officer' },
  { value: 'cadet', label: 'Cadet Program' },
  { value: 'instructor', label: 'Flight Instructor' },
  { value: 'other', label: 'Other' },
];

export const CONTRACT_TYPES = [
  { value: 'permanent', label: 'Permanent' },
  { value: 'contract', label: 'Contract' },
  { value: 'seasonal', label: 'Seasonal' },
  { value: 'freelance', label: 'Freelance' },
];

export const AIRCRAFT_CATEGORIES = [
  { value: 'narrowbody', label: 'Narrowbody (A320, B737)' },
  { value: 'widebody', label: 'Widebody (A350, B777)' },
  { value: 'regional', label: 'Regional Jets' },
  { value: 'turboprop', label: 'Turboprop' },
  { value: 'business', label: 'Business Jets' },
  { value: 'helicopter', label: 'Helicopter' },
];

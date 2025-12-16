-- SkyLink Pilot Jobs Platform - Supabase Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Pilot Jobs Table
-- Many fields have defaults because scrapers may not always get all data
CREATE TABLE IF NOT EXISTS pilot_jobs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  company VARCHAR(255) NOT NULL,
  location VARCHAR(255) DEFAULT 'Not specified',
  region VARCHAR(50) DEFAULT 'global' CHECK (region IN ('europe', 'middle_east', 'asia', 'africa', 'oceania', 'north_america', 'south_america', 'caribbean', 'global')),
  position_type VARCHAR(50) DEFAULT 'other' CHECK (position_type IN ('captain', 'first_officer', 'cadet', 'instructor', 'other')),
  aircraft_type VARCHAR(255),
  type_rating_required BOOLEAN DEFAULT false,
  type_rating_provided BOOLEAN DEFAULT false,
  min_total_hours INTEGER,
  min_pic_hours INTEGER,
  min_type_hours INTEGER,
  license_required VARCHAR(255) DEFAULT 'ATPL/CPL',
  visa_sponsorship BOOLEAN DEFAULT false,
  is_entry_level BOOLEAN DEFAULT false,
  tags TEXT[] DEFAULT '{}',
  contract_type VARCHAR(50) DEFAULT 'permanent' CHECK (contract_type IN ('permanent', 'contract', 'seasonal', 'freelance')),
  salary_info TEXT,
  benefits TEXT,
  description TEXT,
  application_url TEXT NOT NULL UNIQUE,
  source VARCHAR(255) DEFAULT 'Scraped',
  date_posted VARCHAR(100),
  date_scraped TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Profiles Table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  total_hours INTEGER,
  pic_hours INTEGER,
  licenses TEXT[] DEFAULT '{}',
  type_ratings TEXT[] DEFAULT '{}',
  preferred_regions TEXT[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Saved Jobs Table
CREATE TABLE IF NOT EXISTS saved_jobs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  job_id UUID REFERENCES pilot_jobs(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, job_id)
);

-- Job Alerts Table
CREATE TABLE IF NOT EXISTS job_alerts (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  name VARCHAR(255) NOT NULL,
  filters JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  frequency VARCHAR(50) DEFAULT 'daily' CHECK (frequency IN ('instant', 'daily', 'weekly')),
  last_sent_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_region ON pilot_jobs(region);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_position_type ON pilot_jobs(position_type);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_type_rating ON pilot_jobs(type_rating_required);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_min_hours ON pilot_jobs(min_total_hours);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_is_active ON pilot_jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_date_scraped ON pilot_jobs(date_scraped DESC);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_visa_sponsorship ON pilot_jobs(visa_sponsorship);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_is_entry_level ON pilot_jobs(is_entry_level);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_search ON pilot_jobs USING gin(to_tsvector('english', title || ' ' || company || ' ' || location));

CREATE INDEX IF NOT EXISTS idx_saved_jobs_user ON saved_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_job_alerts_user ON job_alerts(user_id);

-- Row Level Security (RLS)
ALTER TABLE pilot_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_alerts ENABLE ROW LEVEL SECURITY;

-- Policies for pilot_jobs (public read, admin write)
CREATE POLICY "Jobs are viewable by everyone" ON pilot_jobs
  FOR SELECT USING (true);

CREATE POLICY "Jobs can be inserted by service role" ON pilot_jobs
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Jobs can be updated by service role" ON pilot_jobs
  FOR UPDATE USING (true);

-- Policies for profiles
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

-- Policies for saved_jobs
CREATE POLICY "Users can view own saved jobs" ON saved_jobs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own saved jobs" ON saved_jobs
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own saved jobs" ON saved_jobs
  FOR DELETE USING (auth.uid() = user_id);

-- Policies for job_alerts
CREATE POLICY "Users can view own alerts" ON job_alerts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own alerts" ON job_alerts
  FOR ALL USING (auth.uid() = user_id);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_pilot_jobs_updated_at
  BEFORE UPDATE ON pilot_jobs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create profile on signup
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================================
-- UNIVERSAL SCRAPER SYSTEM - Airlines to Scrape Table
-- ============================================================================
-- This table is the "Source of Truth" for the Universal ATS Router.
-- Add new airlines here - NO CODE CHANGES NEEDED.

CREATE TABLE IF NOT EXISTS airlines_to_scrape (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  career_page_url TEXT NOT NULL,

  -- ATS Detection (auto-detected or manually set)
  ats_type VARCHAR(50) DEFAULT 'UNKNOWN' CHECK (ats_type IN (
    'TALEO', 'WORKDAY', 'SUCCESSFACTORS', 'BRASSRING', 'ICIMS',
    'GREENHOUSE', 'LEVER', 'SMARTRECRUITERS', 'CUSTOM_AI', 'UNKNOWN'
  )),

  -- Tier System for Smart Scheduling
  tier INTEGER DEFAULT 2 CHECK (tier IN (1, 2, 3)),
  -- Tier 1: Major airlines (Emirates, Delta) - check every 2-3 hours
  -- Tier 2: Medium airlines - check every 12 hours
  -- Tier 3: Small/regional - check every 24 hours

  -- Scheduling
  scrape_frequency_hours INTEGER DEFAULT 12,
  last_checked TIMESTAMP WITH TIME ZONE DEFAULT '2000-01-01',
  last_successful_scrape TIMESTAMP WITH TIME ZONE,

  -- Status & Health
  status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error', 'pending_review')),
  consecutive_failures INTEGER DEFAULT 0,
  last_error TEXT,

  -- Metadata
  region VARCHAR(50) DEFAULT 'global' CHECK (region IN ('europe', 'middle_east', 'asia', 'africa', 'oceania', 'north_america', 'south_america', 'caribbean', 'global')),
  country VARCHAR(100),
  iata_code VARCHAR(3),
  icao_code VARCHAR(4),

  -- Discovery metadata
  discovered_by VARCHAR(50) DEFAULT 'manual', -- 'manual', 'hunter', 'google_dork'
  jobs_found_last_scrape INTEGER DEFAULT 0,
  total_jobs_found INTEGER DEFAULT 0,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Scrape History Log (for debugging and analytics)
CREATE TABLE IF NOT EXISTS scrape_logs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  airline_id UUID REFERENCES airlines_to_scrape(id) ON DELETE CASCADE,
  airline_name VARCHAR(255) NOT NULL,

  -- Scrape Details
  ats_type_detected VARCHAR(50),
  scraper_used VARCHAR(100),

  -- Results
  status VARCHAR(50) CHECK (status IN ('success', 'partial', 'failed', 'timeout')),
  jobs_found INTEGER DEFAULT 0,
  jobs_new INTEGER DEFAULT 0,
  jobs_updated INTEGER DEFAULT 0,

  -- Performance
  duration_seconds DECIMAL(10,2),

  -- Error tracking
  error_message TEXT,
  error_stack TEXT,

  -- Timestamps
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for the new tables
CREATE INDEX IF NOT EXISTS idx_airlines_status ON airlines_to_scrape(status);
CREATE INDEX IF NOT EXISTS idx_airlines_tier ON airlines_to_scrape(tier);
CREATE INDEX IF NOT EXISTS idx_airlines_last_checked ON airlines_to_scrape(last_checked);
CREATE INDEX IF NOT EXISTS idx_airlines_ats_type ON airlines_to_scrape(ats_type);
CREATE INDEX IF NOT EXISTS idx_airlines_region ON airlines_to_scrape(region);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_airline ON scrape_logs(airline_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON scrape_logs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_started ON scrape_logs(started_at DESC);

-- RLS for airlines_to_scrape (public read, service role write)
ALTER TABLE airlines_to_scrape ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Airlines are viewable by everyone" ON airlines_to_scrape
  FOR SELECT USING (true);

CREATE POLICY "Airlines can be modified by service role" ON airlines_to_scrape
  FOR ALL USING (true);

CREATE POLICY "Scrape logs are viewable by everyone" ON scrape_logs
  FOR SELECT USING (true);

CREATE POLICY "Scrape logs can be inserted by service role" ON scrape_logs
  FOR INSERT WITH CHECK (true);

-- Trigger for updated_at on airlines_to_scrape
CREATE TRIGGER update_airlines_to_scrape_updated_at
  BEFORE UPDATE ON airlines_to_scrape
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Sample data for testing (optional)
-- ============================================================================
INSERT INTO pilot_jobs (title, company, location, region, position_type, aircraft_type, type_rating_required, type_rating_provided, min_total_hours, license_required, contract_type, description, application_url, source, date_posted)
VALUES
  ('A320 First Officer - Cadet Program', 'Ryanair', 'Dublin, Ireland', 'europe', 'cadet', 'Airbus A320', false, true, 250, 'EASA CPL/ME/IR', 'permanent', 'Join Ryanair''s industry-leading cadet program.', 'https://careers.ryanair.com/fo-cadet', 'Direct', '2 days ago'),
  ('B737 Captain', 'Enter Air', 'Warsaw, Poland', 'europe', 'captain', 'Boeing 737NG/MAX', true, false, 4000, 'EASA ATPL', 'contract', 'Charter airline seeking experienced B737NG Captains.', 'https://www.rishworthaviation.com/enter-air', 'Rishworth Aviation', '1 day ago'),
  ('A320 First Officer', 'Etihad Airways', 'Abu Dhabi, UAE', 'middle_east', 'first_officer', 'Airbus A320', true, false, 1500, 'ICAO ATPL/fATPL', 'permanent', 'Join Etihad Airways as an A320 First Officer.', 'https://careers.etihad.com/a320-fo', 'Direct', '3 days ago');

-- ============================================================================
-- Seed Initial Airlines for Universal Scraper
-- ============================================================================
INSERT INTO airlines_to_scrape (name, career_page_url, ats_type, tier, scrape_frequency_hours, region, country, iata_code, icao_code) VALUES
-- Tier 1: Major Airlines (Check every 2-3 hours)
('Emirates', 'https://emirates.taleo.net/careersection/2/jobsearch.ftl', 'TALEO', 1, 3, 'middle_east', 'United Arab Emirates', 'EK', 'UAE'),
('Qatar Airways', 'https://careers.qatarairways.com/global/en/c/pilots-jobs', 'CUSTOM_AI', 1, 3, 'middle_east', 'Qatar', 'QR', 'QTR'),
('Etihad Airways', 'https://etihad.taleo.net/careersection/etihad_careers/jobsearch.ftl', 'TALEO', 1, 3, 'middle_east', 'United Arab Emirates', 'EY', 'ETD'),
('Ryanair', 'https://careers.ryanair.com/search/?q=pilot', 'CUSTOM_AI', 1, 3, 'europe', 'Ireland', 'FR', 'RYR'),
('easyJet', 'https://careers.easyjet.com/vacancies', 'CUSTOM_AI', 1, 3, 'europe', 'United Kingdom', 'U2', 'EZY'),
('Delta Air Lines', 'https://delta.avature.net/careers', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'DL', 'DAL'),
('United Airlines', 'https://careers.united.com/us/en/search-results', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'UA', 'UAL'),
('American Airlines', 'https://jobs.aa.com/search-jobs', 'CUSTOM_AI', 1, 3, 'north_america', 'United States', 'AA', 'AAL'),
('Singapore Airlines', 'https://singaporeair.wd3.myworkdayjobs.com/SIA', 'WORKDAY', 1, 3, 'asia', 'Singapore', 'SQ', 'SIA'),
('Cathay Pacific', 'https://careers.cathaypacific.com/jobs', 'CUSTOM_AI', 1, 3, 'asia', 'Hong Kong', 'CX', 'CPA'),
('Lufthansa', 'https://career.lufthansagroup.careers/LUFTHANSA/search', 'CUSTOM_AI', 1, 3, 'europe', 'Germany', 'LH', 'DLH'),
('British Airways', 'https://careers.ba.com/jobs', 'CUSTOM_AI', 1, 3, 'europe', 'United Kingdom', 'BA', 'BAW'),

-- Tier 2: Medium Airlines (Check every 12 hours)
('Wizz Air', 'https://wizzair.com/en-gb/information-and-services/about-us/careers/pilot-jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Hungary', 'W6', 'WZZ'),
('flydubai', 'https://careers.flydubai.com/jobs', 'CUSTOM_AI', 2, 12, 'middle_east', 'United Arab Emirates', 'FZ', 'FDB'),
('Air France', 'https://airfranceklm-group.hiringplatform.eu/en/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'France', 'AF', 'AFR'),
('KLM', 'https://careers.klm.com/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Netherlands', 'KL', 'KLM'),
('SWISS', 'https://swiss.wd3.myworkdayjobs.com/External', 'WORKDAY', 2, 12, 'europe', 'Switzerland', 'LX', 'SWR'),
('Qantas', 'https://qantas.wd3.myworkdayjobs.com/Qantas_Careers', 'WORKDAY', 2, 12, 'oceania', 'Australia', 'QF', 'QFA'),
('Virgin Atlantic', 'https://careers.virginatlantic.com/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'United Kingdom', 'VS', 'VIR'),
('Turkish Airlines', 'https://www.turkishairlines.com/en-int/corporate/career/pilot-recruitment/', 'CUSTOM_AI', 2, 12, 'europe', 'Turkey', 'TK', 'THY'),
('Iberia', 'https://careers.iberia.com/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Spain', 'IB', 'IBE'),
('Vueling', 'https://careers.vueling.com/en/pilot', 'CUSTOM_AI', 2, 12, 'europe', 'Spain', 'VY', 'VLG'),
('Norwegian', 'https://careers.norwegian.com/jobs', 'CUSTOM_AI', 2, 12, 'europe', 'Norway', 'DY', 'NAX'),
('JetBlue', 'https://jetblue.wd1.myworkdayjobs.com/JetBlue', 'WORKDAY', 2, 12, 'north_america', 'United States', 'B6', 'JBU'),
('Southwest Airlines', 'https://careers.southwestair.com/career-areas/pilots', 'CUSTOM_AI', 2, 12, 'north_america', 'United States', 'WN', 'SWA'),
('Air Canada', 'https://careers.aircanada.com/search-jobs', 'CUSTOM_AI', 2, 12, 'north_america', 'Canada', 'AC', 'ACA'),
('Japan Airlines', 'https://career.jal.com/pilot/', 'CUSTOM_AI', 2, 12, 'asia', 'Japan', 'JL', 'JAL'),
('ANA', 'https://www.ana.co.jp/group/en/about-us/jobs/', 'CUSTOM_AI', 2, 12, 'asia', 'Japan', 'NH', 'ANA'),
('Korean Air', 'https://recruit.koreanair.com/careers', 'CUSTOM_AI', 2, 12, 'asia', 'South Korea', 'KE', 'KAL'),
('Thai Airways', 'https://career.thaiairways.com/pilot', 'CUSTOM_AI', 2, 12, 'asia', 'Thailand', 'TG', 'THA'),
('Malaysia Airlines', 'https://careers.malaysiaairlines.com/jobs', 'CUSTOM_AI', 2, 12, 'asia', 'Malaysia', 'MH', 'MAS'),

-- Tier 3: Smaller/Regional Airlines (Check every 24 hours)
('SAS', 'https://www.sasgroup.net/about-sas/careers/', 'CUSTOM_AI', 3, 24, 'europe', 'Sweden', 'SK', 'SAS'),
('Finnair', 'https://finnair.wd3.myworkdayjobs.com/Finnair_External', 'WORKDAY', 3, 24, 'europe', 'Finland', 'AY', 'FIN'),
('LOT Polish', 'https://career.lot.com/search', 'CUSTOM_AI', 3, 24, 'europe', 'Poland', 'LO', 'LOT'),
('TAP Air Portugal', 'https://careers.flytap.com/jobs', 'CUSTOM_AI', 3, 24, 'europe', 'Portugal', 'TP', 'TAP'),
('Aer Lingus', 'https://careers.aerlingus.com/jobs', 'CUSTOM_AI', 3, 24, 'europe', 'Ireland', 'EI', 'EIN'),
('ITA Airways', 'https://careers.ita-airways.com/jobs', 'CUSTOM_AI', 3, 24, 'europe', 'Italy', 'AZ', 'ITY'),
('Eurowings', 'https://career.lufthansagroup.careers/EUROWINGS/search', 'CUSTOM_AI', 3, 24, 'europe', 'Germany', 'EW', 'EWG'),
('Austrian Airlines', 'https://career.lufthansagroup.careers/AUSTRIAN/search', 'CUSTOM_AI', 3, 24, 'europe', 'Austria', 'OS', 'AUA'),
('Brussels Airlines', 'https://career.lufthansagroup.careers/BRUSSELS/search', 'CUSTOM_AI', 3, 24, 'europe', 'Belgium', 'SN', 'BEL'),
('Saudia', 'https://careers.saudia.com/en/jobs', 'CUSTOM_AI', 3, 24, 'middle_east', 'Saudi Arabia', 'SV', 'SVA'),
('Gulf Air', 'https://careers.gulfair.com/jobs', 'CUSTOM_AI', 3, 24, 'middle_east', 'Bahrain', 'GF', 'GFA'),
('Oman Air', 'https://careers.omanair.com/jobs', 'CUSTOM_AI', 3, 24, 'middle_east', 'Oman', 'WY', 'OMA'),
('Kuwait Airways', 'https://careers.kuwaitairways.com/jobs', 'CUSTOM_AI', 3, 24, 'middle_east', 'Kuwait', 'KU', 'KAC'),
('Air India', 'https://careers.airindia.in/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'India', 'AI', 'AIC'),
('IndiGo', 'https://careers.goindigo.in/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'India', '6E', 'IGO'),
('China Eastern', 'https://careers.ceair.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'China', 'MU', 'CES'),
('China Southern', 'https://careers.csair.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'China', 'CZ', 'CSN'),
('Vietnam Airlines', 'https://careers.vietnamairlines.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'Vietnam', 'VN', 'HVN'),
('Garuda Indonesia', 'https://career.garuda-indonesia.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'Indonesia', 'GA', 'GIA'),
('Philippine Airlines', 'https://careers.philippineairlines.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'Philippines', 'PR', 'PAL'),
('Cebu Pacific', 'https://careers.cebupacificair.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'Philippines', '5J', 'CEB'),
('AirAsia', 'https://careers.airasia.com/jobs', 'CUSTOM_AI', 3, 24, 'asia', 'Malaysia', 'AK', 'AXM'),
('Jetstar', 'https://jetstar.wd3.myworkdayjobs.com/Jetstar_Careers', 'WORKDAY', 3, 24, 'oceania', 'Australia', 'JQ', 'JST'),
('Air New Zealand', 'https://careers.airnewzealand.co.nz/jobs', 'CUSTOM_AI', 3, 24, 'oceania', 'New Zealand', 'NZ', 'ANZ'),
('LATAM', 'https://careers.latam.com/jobs', 'CUSTOM_AI', 3, 24, 'south_america', 'Chile', 'LA', 'LAN'),
('Avianca', 'https://careers.avianca.com/jobs', 'CUSTOM_AI', 3, 24, 'south_america', 'Colombia', 'AV', 'AVA'),
('Copa Airlines', 'https://careers.copaair.com/jobs', 'CUSTOM_AI', 3, 24, 'south_america', 'Panama', 'CM', 'CMP'),
('Ethiopian Airlines', 'https://careers.ethiopianairlines.com/jobs', 'CUSTOM_AI', 3, 24, 'africa', 'Ethiopia', 'ET', 'ETH'),
('South African Airways', 'https://careers.flysaa.com/jobs', 'CUSTOM_AI', 3, 24, 'africa', 'South Africa', 'SA', 'SAA'),
('EgyptAir', 'https://careers.egyptair.com/jobs', 'CUSTOM_AI', 3, 24, 'africa', 'Egypt', 'MS', 'MSR'),
('Royal Air Maroc', 'https://careers.royalairmaroc.com/jobs', 'CUSTOM_AI', 3, 24, 'africa', 'Morocco', 'AT', 'RAM'),

-- Recruitment Agencies (Tier 2)
('Rishworth Aviation', 'https://www.rishworthaviation.com/vacancies/', 'CUSTOM_AI', 2, 12, 'global', NULL, NULL, NULL),
('PARC Aviation', 'https://www.parcaviation.aero/pilot-jobs', 'CUSTOM_AI', 2, 12, 'global', NULL, NULL, NULL),
('Goose Recruitment', 'https://www.goose.aero/jobs', 'CUSTOM_AI', 2, 12, 'global', NULL, NULL, NULL),
('CAE Parc', 'https://www.caeparc.com/pilots', 'CUSTOM_AI', 2, 12, 'global', NULL, NULL, NULL),
('OSM Aviation', 'https://jobs.osm.aero/jobs', 'CUSTOM_AI', 2, 12, 'global', NULL, NULL, NULL)
ON CONFLICT (name) DO NOTHING;

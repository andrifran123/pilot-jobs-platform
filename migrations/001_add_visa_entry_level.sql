-- Migration: Add visa_sponsorship, is_entry_level, and tags columns
-- Run this in your Supabase SQL Editor to add the new columns

-- Add new columns to pilot_jobs table
ALTER TABLE pilot_jobs
ADD COLUMN IF NOT EXISTS visa_sponsorship BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_entry_level BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- Create indexes for better query performance on new columns
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_visa_sponsorship ON pilot_jobs(visa_sponsorship);
CREATE INDEX IF NOT EXISTS idx_pilot_jobs_is_entry_level ON pilot_jobs(is_entry_level);

-- Update existing jobs to set is_entry_level based on type_rating_provided or low hours
UPDATE pilot_jobs
SET is_entry_level = true
WHERE type_rating_provided = true
   OR position_type = 'cadet'
   OR (min_total_hours IS NOT NULL AND min_total_hours < 500);

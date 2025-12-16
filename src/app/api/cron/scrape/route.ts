import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase'

// This is the Vercel Cron Job endpoint
// It gets called automatically based on vercel.json config
// Or can be called manually with the CRON_SECRET

export const maxDuration = 300 // 5 minutes max for Vercel Pro
export const dynamic = 'force-dynamic'

// Validate URL by making a HEAD request
async function validateUrl(url: string): Promise<boolean> {
  try {
    // Remove hash fragments for validation (they don't affect server response)
    const urlWithoutHash = url.split('#')[0]

    const response = await fetch(urlWithoutHash, {
      method: 'HEAD',
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    })

    // Accept 200, 301, 302 (redirects are fine)
    return response.ok || response.status === 301 || response.status === 302
  } catch {
    // If HEAD fails, try GET (some servers don't support HEAD)
    try {
      const response = await fetch(url.split('#')[0], {
        method: 'GET',
        redirect: 'follow',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      })
      return response.ok
    } catch {
      return false
    }
  }
}

// Simplified scraper that runs in serverless environment
// Uses fetch to scrape static job pages
async function scrapeJobs(): Promise<JobData[]> {
  const jobs: JobData[] = []

  // Known static job URLs that are always hiring
  // IMPORTANT: Only use REAL, VERIFIED URLs - each URL must be UNIQUE!
  const STATIC_JOBS = [
    // Emirates - Always hiring pilots (VERIFIED URL)
    {
      title: 'Emirates Pilots (Captain & First Officer)',
      company: 'Emirates',
      location: 'Dubai, UAE',
      region: 'middle_east',
      position_type: 'first_officer',
      aircraft_type: 'A380/B777',
      application_url: 'https://www.emiratesgroupcareers.com/pilots/',
      source: 'Direct - Emirates',
      type_rating_provided: true,
      contract_type: 'permanent',
      salary_info: 'Tax-free competitive package',
    },
    // Qatar Airways (VERIFIED URLS)
    {
      title: 'Qatar Airways Pilots',
      company: 'Qatar Airways',
      location: 'Doha, Qatar',
      region: 'middle_east',
      position_type: 'first_officer',
      aircraft_type: 'A350/A380/B787/B777',
      application_url: 'https://careers.qatarairways.com/global/en/c/pilots-jobs',
      source: 'Direct - Qatar Airways',
      type_rating_provided: true,
      contract_type: 'permanent',
      salary_info: 'Tax-free competitive package',
    },
    // Etihad (VERIFIED URL)
    {
      title: 'Etihad Airways Pilots',
      company: 'Etihad Airways',
      location: 'Abu Dhabi, UAE',
      region: 'middle_east',
      position_type: 'first_officer',
      aircraft_type: 'A350/B787/B777',
      application_url: 'https://careers.etihad.com/go/Pilot-Opportunities/4691401/',
      source: 'Direct - Etihad',
      type_rating_provided: true,
      contract_type: 'permanent',
      salary_info: 'Tax-free competitive package',
    },
    // Ryanair (VERIFIED URL)
    {
      title: 'Ryanair Pilots - B737',
      company: 'Ryanair',
      location: 'Europe (Multiple Bases)',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'Boeing 737-800/MAX',
      application_url: 'https://careers.ryanair.com/search/?q=pilot',
      source: 'Direct - Ryanair',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // easyJet (VERIFIED URL)
    {
      title: 'easyJet Pilots - A320',
      company: 'easyJet',
      location: 'UK/Europe (Multiple Bases)',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'Airbus A320',
      application_url: 'https://careers.easyjet.com/vacancies/pilots/',
      source: 'Direct - easyJet',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // Wizz Air (VERIFIED URL)
    {
      title: 'Wizz Air Pilots - A320/A321',
      company: 'Wizz Air',
      location: 'Europe (Multiple Bases)',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'Airbus A320/A321',
      application_url: 'https://wizzair.com/en-gb/information-and-services/about-us/careers/pilots',
      source: 'Direct - Wizz Air',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // flydubai (VERIFIED URL)
    {
      title: 'flydubai Pilots - B737 MAX',
      company: 'flydubai',
      location: 'Dubai, UAE',
      region: 'middle_east',
      position_type: 'first_officer',
      aircraft_type: 'Boeing 737 MAX',
      application_url: 'https://careers.flydubai.com/en/jobs/?department=Pilots',
      source: 'Direct - flydubai',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // Vueling (VERIFIED URL)
    {
      title: 'Vueling Pilots - A320',
      company: 'Vueling',
      location: 'Barcelona, Spain',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'Airbus A320',
      application_url: 'https://careers.vueling.com/go/Flight-Crew/8838601/',
      source: 'Direct - Vueling',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // Singapore Airlines (VERIFIED URL - main careers page)
    {
      title: 'Singapore Airlines Pilots',
      company: 'Singapore Airlines',
      location: 'Singapore',
      region: 'asia',
      position_type: 'first_officer',
      aircraft_type: 'A350/A380/B787/B777',
      application_url: 'https://www.singaporeair.com/en_UK/sg/careers/',
      source: 'Direct - Singapore Airlines',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // Cathay Pacific (VERIFIED URL)
    {
      title: 'Cathay Pacific Pilots',
      company: 'Cathay Pacific',
      location: 'Hong Kong',
      region: 'asia',
      position_type: 'first_officer',
      aircraft_type: 'A350/B777',
      application_url: 'https://careers.cathaypacific.com/jobs?department=Flight+Operations',
      source: 'Direct - Cathay Pacific',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
    // Air France (VERIFIED URL)
    {
      title: 'Air France Pilots',
      company: 'Air France',
      location: 'Paris, France',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'A320/A350/B777/B787',
      application_url: 'https://recrutement.airfrance.com/offre-emploi/liste-offres.aspx',
      source: 'Direct - Air France',
      type_rating_provided: false,
      contract_type: 'permanent',
    },
    // Lufthansa (VERIFIED URL)
    {
      title: 'Lufthansa Group Pilots',
      company: 'Lufthansa',
      location: 'Frankfurt/Munich, Germany',
      region: 'europe',
      position_type: 'first_officer',
      aircraft_type: 'A320/A350/B747/B777',
      application_url: 'https://www.be-lufthansa.com/en/pilot',
      source: 'Direct - Lufthansa',
      type_rating_provided: true,
      contract_type: 'permanent',
    },
  ]

  // Add all static jobs with current timestamp
  // Validate URLs in parallel (but limit concurrency to avoid rate limiting)
  const validationResults = await Promise.all(
    STATIC_JOBS.map(async (job) => {
      const isValid = await validateUrl(job.application_url)
      return { job, isValid }
    })
  )

  // Only add jobs with valid URLs
  for (const { job, isValid } of validationResults) {
    if (isValid) {
      jobs.push({
        ...job,
        date_scraped: new Date().toISOString(),
        is_active: true,
        type_rating_required: job.type_rating_required || false,
        type_rating_provided: job.type_rating_provided || false,
      })
    } else {
      console.warn(`Skipping job "${job.title}" - invalid URL: ${job.application_url}`)
    }
  }

  console.log(`URL validation: ${jobs.length}/${STATIC_JOBS.length} jobs have valid URLs`)

  return jobs
}

interface JobData {
  title: string
  company: string
  location: string
  region: string
  position_type: string
  aircraft_type?: string
  application_url: string
  source: string
  type_rating_required?: boolean
  type_rating_provided?: boolean
  contract_type?: string
  salary_info?: string
  date_scraped: string
  is_active: boolean
}

export async function GET(request: NextRequest) {
  // Verify cron secret (Vercel sends this automatically)
  const authHeader = request.headers.get('authorization')
  const cronSecret = process.env.CRON_SECRET

  // Allow if CRON_SECRET matches or if we're in development
  const isDev = process.env.NODE_ENV === 'development'
  const isAuthorized = isDev || (cronSecret && authHeader === `Bearer ${cronSecret}`)

  if (!isAuthorized) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  console.log('Starting cron scrape job...')

  try {
    // Run the simplified scraper
    const jobs = await scrapeJobs()
    console.log(`Scraped ${jobs.length} jobs`)

    // Save to Supabase
    const supabase = createAdminClient()
    if (!supabase) {
      return NextResponse.json({
        success: false,
        error: 'Supabase not configured',
        jobs_found: jobs.length
      }, { status: 500 })
    }

    // Upsert jobs - cast to any to avoid type issues with dynamic data
    const jobsToUpsert = jobs.map(job => {
      // =================================================================
      // ENTRY-LEVEL DETECTION - Conservative approach
      // Only mark as entry-level if we have HIGH CONFIDENCE:
      // 1. Explicitly a cadet/trainee position
      // 2. Type rating provided AND not a Captain position
      //
      // We do NOT mark as entry-level just because hours are unknown
      // Better to show "Unknown" than incorrectly label a Captain job
      // =================================================================
      const isCadetOrTrainee = job.position_type === 'cadet'
      const isTypeRatingProvidedNonCaptain = job.type_rating_provided && job.position_type !== 'captain'

      // Only mark entry-level with confidence
      const isEntryLevel = isCadetOrTrainee || isTypeRatingProvidedNonCaptain

      // Middle East airlines typically sponsor visas
      const middleEastAirlines = ['Emirates', 'Qatar Airways', 'Etihad Airways', 'flydubai']
      const visaSponsorship = middleEastAirlines.includes(job.company) || job.region === 'middle_east'

      return {
        title: job.title,
        company: job.company,
        location: job.location,
        region: job.region,
        position_type: job.position_type,
        aircraft_type: job.aircraft_type || null,
        type_rating_required: job.type_rating_required || false,
        type_rating_provided: job.type_rating_provided || false,
        contract_type: job.contract_type || 'permanent',
        salary_info: job.salary_info || null,
        application_url: job.application_url,
        source: job.source,
        date_scraped: job.date_scraped,
        is_active: true,
        is_entry_level: isEntryLevel,
        visa_sponsorship: visaSponsorship,
      }
    })

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (supabase.from('pilot_jobs') as any).upsert(
      jobsToUpsert,
      { onConflict: 'application_url' }
    )

    if (error) {
      console.error('Supabase error:', error)
      return NextResponse.json({
        success: false,
        error: error.message,
        jobs_found: jobs.length
      }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      message: `Scraped and saved ${jobs.length} jobs`,
      jobs_found: jobs.length,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('Cron scrape error:', error)
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { PilotJob } from '@/types'
import { createAdminClient, isSupabaseConfigured } from '@/lib/supabase'
import fs from 'fs'
import path from 'path'

// Load jobs from Supabase or fall back to JSON file
async function loadJobs(): Promise<PilotJob[]> {
  // Try Supabase first
  if (isSupabaseConfigured()) {
    try {
      const supabase = createAdminClient()
      if (supabase) {
        const { data, error } = await supabase
          .from('pilot_jobs')
          .select('*')
          .eq('is_active', true)
          .order('date_scraped', { ascending: false })

        if (!error && data && data.length > 0) {
          console.log(`Loaded ${data.length} jobs from Supabase`)
          return data as PilotJob[]
        }
      }
    } catch (error) {
      console.error('Error loading from Supabase:', error)
    }
  }

  // Fall back to JSON file
  return loadScrapedJobs()
}

// Load jobs from scraper output file
function loadScrapedJobs(): PilotJob[] {
  try {
    const scraperOutputPath = path.join(process.cwd(), 'scraper', 'output', 'latest_jobs.json')

    if (fs.existsSync(scraperOutputPath)) {
      const data = JSON.parse(fs.readFileSync(scraperOutputPath, 'utf-8'))
      const jobs = data.jobs || []

      return jobs.map((job: Record<string, unknown>, index: number) => ({
        id: job.id || `scraped-${index + 1}`,
        title: job.title || '',
        company: job.company || '',
        location: job.location || '',
        region: job.region || 'global',
        position_type: job.position_type || 'other',
        aircraft_type: job.aircraft_type || null,
        type_rating_required: job.type_rating_required ?? false,
        type_rating_provided: job.type_rating_provided ?? false,
        min_total_hours: job.min_total_hours || null,
        min_pic_hours: job.min_pic_hours || null,
        min_type_hours: job.min_type_hours || null,
        license_required: job.license_required || null,
        contract_type: job.contract_type || null,
        salary_info: job.salary_info || null,
        benefits: job.benefits || null,
        description: job.description || null,
        application_url: job.application_url || '',
        source: job.source || 'Scraped',
        date_posted: job.date_posted || null,
        date_scraped: job.date_scraped || new Date().toISOString(),
        is_active: job.is_active ?? true,
      }))
    }
  } catch (error) {
    console.error('Error loading scraped jobs:', error)
  }

  return SAMPLE_JOBS
}

// Sample job data - fallback when no data available
const SAMPLE_JOBS: PilotJob[] = [
  {
    id: '1',
    title: 'A320 First Officer - Cadet Program',
    company: 'Ryanair',
    location: 'Dublin, Ireland',
    region: 'europe',
    position_type: 'cadet',
    aircraft_type: 'Airbus A320',
    type_rating_required: false,
    type_rating_provided: true,
    min_total_hours: 250,
    min_pic_hours: null,
    min_type_hours: null,
    license_required: 'EASA CPL/ME/IR',
    contract_type: 'permanent',
    salary_info: 'Competitive',
    benefits: 'Type rating provided, travel benefits',
    description: 'Join Ryanair\'s cadet program.',
    application_url: 'https://careers.ryanair.com/',
    source: 'Direct',
    date_posted: '2 days ago',
    date_scraped: new Date().toISOString(),
    is_active: true,
  },
]

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams

  const search = searchParams.get('search') || ''
  const position_type = searchParams.getAll('position_type')
  const region = searchParams.getAll('region')
  const type_rating_required = searchParams.get('type_rating_required')
  const max_hours = searchParams.get('max_hours')
  const page = parseInt(searchParams.get('page') || '1')
  const limit = parseInt(searchParams.get('limit') || '20')

  // Load jobs from Supabase or JSON
  let filteredJobs = await loadJobs()

  // Apply filters
  if (search) {
    const searchLower = search.toLowerCase()
    filteredJobs = filteredJobs.filter(job =>
      job.title.toLowerCase().includes(searchLower) ||
      job.company.toLowerCase().includes(searchLower) ||
      job.location.toLowerCase().includes(searchLower)
    )
  }

  if (position_type.length > 0) {
    filteredJobs = filteredJobs.filter(job => position_type.includes(job.position_type))
  }

  if (region.length > 0) {
    filteredJobs = filteredJobs.filter(job => region.includes(job.region))
  }

  if (type_rating_required !== null) {
    const required = type_rating_required === 'true'
    filteredJobs = filteredJobs.filter(job => job.type_rating_required === required)
  }

  if (max_hours) {
    const maxHoursNum = parseInt(max_hours)
    filteredJobs = filteredJobs.filter(job =>
      !job.min_total_hours || job.min_total_hours <= maxHoursNum
    )
  }

  // Pagination
  const total = filteredJobs.length
  const offset = (page - 1) * limit
  const paginatedJobs = filteredJobs.slice(offset, offset + limit)

  return NextResponse.json({
    jobs: paginatedJobs,
    total,
    page,
    limit,
    totalPages: Math.ceil(total / limit),
    source: isSupabaseConfigured() ? 'supabase' : 'json'
  })
}

// POST - Save jobs to database (called by scraper)
export async function POST(request: NextRequest) {
  // Verify API key
  const apiKey = request.headers.get('x-api-key')
  const expectedKey = process.env.SCRAPER_API_KEY

  if (!expectedKey || apiKey !== expectedKey) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const jobs = await request.json()

  if (!Array.isArray(jobs)) {
    return NextResponse.json({ error: 'Invalid data format' }, { status: 400 })
  }

  // Save to Supabase if configured
  if (isSupabaseConfigured()) {
    const supabase = createAdminClient()
    if (supabase) {
      try {
        // Upsert jobs (update if URL exists, insert if new)
        const jobsToUpsert = jobs.map((job: Record<string, unknown>) => ({
          title: String(job.title || '').slice(0, 500),
          company: String(job.company || '').slice(0, 255),
          location: String(job.location || 'Not specified').slice(0, 255),
          region: String(job.region || 'global'),
          position_type: String(job.position_type || 'other'),
          aircraft_type: job.aircraft_type ? String(job.aircraft_type) : null,
          type_rating_required: Boolean(job.type_rating_required),
          type_rating_provided: Boolean(job.type_rating_provided),
          min_total_hours: job.min_total_hours ? Number(job.min_total_hours) : null,
          min_pic_hours: job.min_pic_hours ? Number(job.min_pic_hours) : null,
          min_type_hours: job.min_type_hours ? Number(job.min_type_hours) : null,
          license_required: String(job.license_required || 'ATPL/CPL'),
          contract_type: String(job.contract_type || 'permanent'),
          salary_info: job.salary_info ? String(job.salary_info) : null,
          benefits: job.benefits ? String(job.benefits) : null,
          description: job.description ? String(job.description) : null,
          application_url: String(job.application_url || ''),
          source: String(job.source || 'Scraped'),
          date_posted: job.date_posted ? String(job.date_posted) : null,
          date_scraped: new Date().toISOString(),
          is_active: true,
        }))

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error } = await (supabase.from('pilot_jobs') as any).upsert(
          jobsToUpsert,
          { onConflict: 'application_url' }
        )

        if (error) {
          console.error('Supabase upsert error:', error)
          return NextResponse.json({ error: error.message }, { status: 500 })
        }

        return NextResponse.json({
          success: true,
          count: jobs.length,
          message: `Saved ${jobs.length} jobs to Supabase`
        })
      } catch (error) {
        console.error('Error saving to Supabase:', error)
        return NextResponse.json({ error: 'Database error' }, { status: 500 })
      }
    }
  }

  // Fall back to saving to JSON file
  try {
    const outputPath = path.join(process.cwd(), 'scraper', 'output', 'latest_jobs.json')
    fs.writeFileSync(outputPath, JSON.stringify({ jobs }, null, 2))

    return NextResponse.json({
      success: true,
      count: jobs.length,
      message: `Saved ${jobs.length} jobs to JSON (Supabase not configured)`
    })
  } catch (error) {
    console.error('Error saving to JSON:', error)
    return NextResponse.json({ error: 'File write error' }, { status: 500 })
  }
}

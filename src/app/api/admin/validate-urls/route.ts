import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase'

// This endpoint validates all job URLs in the database
// and marks jobs with dead URLs as inactive

export const maxDuration = 300 // 5 minutes max
export const dynamic = 'force-dynamic'

// Validate URL by making a HEAD request
async function validateUrl(url: string): Promise<{ valid: boolean; status?: number; error?: string }> {
  try {
    // Remove hash fragments for validation
    const urlWithoutHash = url.split('#')[0]

    const response = await fetch(urlWithoutHash, {
      method: 'HEAD',
      redirect: 'follow',
      signal: AbortSignal.timeout(10000), // 10 second timeout
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    })

    // 404 is definitely bad
    if (response.status === 404) {
      return { valid: false, status: response.status, error: 'Page not found (404)' }
    }

    // Accept 200, 301, 302 (redirects are fine)
    if (response.ok || response.status === 301 || response.status === 302) {
      return { valid: true, status: response.status }
    }

    return { valid: false, status: response.status, error: `HTTP ${response.status}` }
  } catch (error) {
    // If HEAD fails, try GET (some servers don't support HEAD)
    try {
      const response = await fetch(url.split('#')[0], {
        method: 'GET',
        redirect: 'follow',
        signal: AbortSignal.timeout(10000),
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      })

      if (response.status === 404) {
        return { valid: false, status: response.status, error: 'Page not found (404)' }
      }

      return { valid: response.ok, status: response.status }
    } catch (e) {
      return { valid: false, error: e instanceof Error ? e.message : 'Request failed' }
    }
  }
}

export async function GET(request: NextRequest) {
  // Require admin auth
  const authHeader = request.headers.get('authorization')
  const adminSecret = process.env.CRON_SECRET || process.env.ADMIN_SECRET

  const isDev = process.env.NODE_ENV === 'development'
  const isAuthorized = isDev || (adminSecret && authHeader === `Bearer ${adminSecret}`)

  if (!isAuthorized) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const supabase = createAdminClient()
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 500 })
  }

  console.log('Starting URL validation...')

  // Get all active jobs
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: jobs, error } = await (supabase.from('pilot_jobs') as any)
    .select('id, title, application_url, company')
    .eq('is_active', true)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  console.log(`Found ${jobs.length} active jobs to validate`)

  const results = {
    total: jobs.length,
    valid: 0,
    invalid: 0,
    deactivated: [] as { id: string; title: string; url: string; error: string }[],
    errors: [] as string[]
  }

  // Validate URLs in batches of 5 to avoid rate limiting
  const batchSize = 5
  for (let i = 0; i < jobs.length; i += batchSize) {
    const batch = jobs.slice(i, i + batchSize)

    const validations = await Promise.all(
      batch.map(async (job: { id: string; title: string; application_url: string; company: string }) => {
        const result = await validateUrl(job.application_url)
        return { job, result }
      })
    )

    for (const { job, result } of validations) {
      if (result.valid) {
        results.valid++
      } else {
        results.invalid++

        // Mark job as inactive
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: updateError } = await (supabase.from('pilot_jobs') as any)
          .update({ is_active: false })
          .eq('id', job.id)

        if (updateError) {
          results.errors.push(`Failed to deactivate ${job.id}: ${updateError.message}`)
        } else {
          results.deactivated.push({
            id: job.id,
            title: job.title,
            url: job.application_url,
            error: result.error || 'Unknown error'
          })
          console.log(`Deactivated: ${job.title} (${job.company}) - ${result.error}`)
        }
      }
    }

    // Small delay between batches to be respectful
    if (i + batchSize < jobs.length) {
      await new Promise(resolve => setTimeout(resolve, 500))
    }
  }

  console.log(`Validation complete: ${results.valid} valid, ${results.invalid} invalid`)

  return NextResponse.json({
    success: true,
    message: `Validated ${results.total} jobs, deactivated ${results.invalid} with invalid URLs`,
    results
  })
}

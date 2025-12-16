import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase'

// This endpoint recalculates is_entry_level for all jobs
// using conservative logic (only high-confidence classifications)

export const dynamic = 'force-dynamic'

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

  console.log('Recalculating is_entry_level with conservative logic...')

  // Get all jobs
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: jobs, error } = await (supabase.from('pilot_jobs') as any)
    .select('id, title, position_type, type_rating_provided, min_total_hours')

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  let updated = 0
  let entryLevelCount = 0
  const changes: { title: string; was: boolean; now: boolean }[] = []

  for (const job of jobs) {
    // =================================================================
    // CONSERVATIVE ENTRY-LEVEL LOGIC
    // Only mark as entry-level with HIGH CONFIDENCE
    // =================================================================

    // Check 1: Explicit cadet position
    const isCadet = job.position_type === 'cadet'

    // Check 2: Low hours explicitly stated (< 500)
    const hasLowHours = job.min_total_hours !== null && job.min_total_hours < 500

    // Check 3: Type rating provided AND not a captain position
    // (Captains with type rating provided are NOT entry level)
    const isTypeRatingProvidedNonCaptain =
      job.type_rating_provided === true && job.position_type !== 'captain'

    // Final determination
    const shouldBeEntryLevel = isCadet || hasLowHours || isTypeRatingProvidedNonCaptain

    // Update if needed
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error: updateError } = await (supabase.from('pilot_jobs') as any)
      .update({ is_entry_level: shouldBeEntryLevel })
      .eq('id', job.id)

    if (!updateError) {
      updated++
      if (shouldBeEntryLevel) entryLevelCount++

      // Track significant changes (Captain positions that were wrongly marked)
      if (job.position_type === 'captain' && !shouldBeEntryLevel) {
        changes.push({ title: job.title, was: true, now: false })
      }
    }
  }

  console.log(`Updated ${updated} jobs, ${entryLevelCount} marked as entry-level`)

  return NextResponse.json({
    success: true,
    message: `Recalculated entry-level status for ${updated} jobs`,
    stats: {
      total: jobs.length,
      entry_level: entryLevelCount,
      non_entry_level: jobs.length - entryLevelCount,
    },
    captain_fixes: changes,
  })
}

import { createClient } from '@supabase/supabase-js'

// Database types for Supabase
export type Database = {
  public: {
    Tables: {
      pilot_jobs: {
        Row: {
          id: string
          title: string
          company: string
          location: string
          region: string
          position_type: string
          aircraft_type: string | null
          type_rating_required: boolean
          type_rating_provided: boolean
          min_total_hours: number | null
          min_pic_hours: number | null
          min_type_hours: number | null
          license_required: string | null
          contract_type: string | null
          salary_info: string | null
          benefits: string | null
          description: string | null
          application_url: string
          source: string
          date_posted: string | null
          date_scraped: string
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: Partial<Database['public']['Tables']['pilot_jobs']['Row']> & {
          title: string
          company: string
          application_url: string
        }
        Update: Partial<Database['public']['Tables']['pilot_jobs']['Row']>
      }
      profiles: {
        Row: {
          id: string
          email: string
          full_name: string | null
          total_hours: number | null
          pic_hours: number | null
          licenses: string[]
          type_ratings: string[]
          preferred_regions: string[]
          created_at: string
          updated_at: string
        }
        Insert: Omit<Database['public']['Tables']['profiles']['Row'], 'created_at' | 'updated_at'>
        Update: Partial<Database['public']['Tables']['profiles']['Insert']>
      }
      saved_jobs: {
        Row: {
          id: string
          user_id: string
          job_id: string
          created_at: string
        }
        Insert: Omit<Database['public']['Tables']['saved_jobs']['Row'], 'id' | 'created_at'>
        Update: Partial<Database['public']['Tables']['saved_jobs']['Insert']>
      }
    }
  }
}

// Create Supabase client for frontend (uses anon key)
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Only create client if credentials are available
export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient<Database>(supabaseUrl, supabaseAnonKey)
  : null

// Create admin client for server-side operations (uses service key)
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_KEY

  if (!url || !serviceKey) {
    return null
  }

  return createClient<Database>(url, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  })
}

// Check if Supabase is configured
export function isSupabaseConfigured(): boolean {
  return !!(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
}

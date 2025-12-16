'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Filter, X, SlidersHorizontal, Loader2 } from 'lucide-react'
import Navbar from '@/components/Navbar'
import JobFilters from '@/components/JobFilters'
import JobCard from '@/components/JobCard'
import { JobFilters as FilterType, PilotJob } from '@/types'

export default function JobsPage() {
  const [filters, setFilters] = useState<FilterType>({
    search: '',
    position_type: [],
    region: [],
    type_rating_required: null,
    max_hours_required: null,
    contract_type: [],
    aircraft_category: [],
    visa_sponsorship: null,
    is_entry_level: null,
  })
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [jobs, setJobs] = useState<PilotJob[]>([])
  const [filteredJobs, setFilteredJobs] = useState<PilotJob[]>([])
  const [loading, setLoading] = useState(true)
  const [totalJobs, setTotalJobs] = useState(0)

  // Fetch jobs from API
  useEffect(() => {
    async function fetchJobs() {
      try {
        setLoading(true)
        const response = await fetch('/api/jobs?limit=100')
        const data = await response.json()
        setJobs(data.jobs || [])
        setTotalJobs(data.total || 0)
      } catch (error) {
        console.error('Error fetching jobs:', error)
        setJobs([])
      } finally {
        setLoading(false)
      }
    }
    fetchJobs()
  }, [])

  // Filter jobs client-side
  const applyFilters = useCallback(() => {
    let result = [...jobs]

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      result = result.filter(job =>
        job.title.toLowerCase().includes(searchLower) ||
        job.company.toLowerCase().includes(searchLower) ||
        job.location.toLowerCase().includes(searchLower) ||
        job.aircraft_type?.toLowerCase().includes(searchLower)
      )
    }

    // Position type filter
    if (filters.position_type.length > 0) {
      result = result.filter(job => filters.position_type.includes(job.position_type))
    }

    // Region filter
    if (filters.region.length > 0) {
      result = result.filter(job => filters.region.includes(job.region))
    }

    // Type rating filter
    if (filters.type_rating_required !== null) {
      result = result.filter(job => job.type_rating_required === filters.type_rating_required)
    }

    // Max hours filter
    if (filters.max_hours_required !== null) {
      result = result.filter(job =>
        !job.min_total_hours || job.min_total_hours <= filters.max_hours_required!
      )
    }

    // Contract type filter
    if (filters.contract_type.length > 0) {
      result = result.filter(job => filters.contract_type.includes(job.contract_type || ''))
    }

    // Visa sponsorship filter
    if (filters.visa_sponsorship !== null) {
      result = result.filter(job => job.visa_sponsorship === filters.visa_sponsorship)
    }

    // Entry level filter
    if (filters.is_entry_level !== null) {
      result = result.filter(job => job.is_entry_level === filters.is_entry_level)
    }

    setFilteredJobs(result)
  }, [jobs, filters])

  useEffect(() => {
    applyFilters()
  }, [applyFilters])

  return (
    <main className="min-h-screen">
      <Navbar />

      {/* Header */}
      <section className="pt-24 pb-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="font-display text-4xl font-bold mb-4">
              Find Your Next <span className="text-cyber-blue">Pilot Position</span>
            </h1>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Browse {totalJobs}+ pilot jobs worldwide. Filter by position, region, experience, and more.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Main Content */}
      <section className="px-4 sm:px-6 lg:px-8 pb-16">
        <div className="max-w-7xl mx-auto">
          <div className="flex gap-8">
            {/* Desktop Filters */}
            <div className="hidden lg:block w-80 flex-shrink-0">
              <JobFilters
                filters={filters}
                onFilterChange={setFilters}
                jobCount={filteredJobs.length}
              />
            </div>

            {/* Job Listings */}
            <div className="flex-1">
              {/* Mobile Filter Button */}
              <div className="lg:hidden mb-6">
                <button
                  onClick={() => setShowMobileFilters(true)}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl cyber-btn"
                >
                  <SlidersHorizontal className="w-5 h-5" />
                  Filters
                  {Object.values(filters).flat().filter(Boolean).length > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-cyber-blue/20 text-cyber-blue text-xs">
                      Active
                    </span>
                  )}
                </button>
              </div>

              {/* Results Header */}
              <div className="flex items-center justify-between mb-6">
                <p className="text-gray-400">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading jobs...
                    </span>
                  ) : (
                    <>
                      Showing <span className="text-white font-medium">{filteredJobs.length}</span> jobs
                    </>
                  )}
                </p>
                <select className="bg-dark-700 border border-cyan-500/10 rounded-lg px-4 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyber-blue">
                  <option>Most Recent</option>
                  <option>Lowest Hours</option>
                  <option>Highest Hours</option>
                </select>
              </div>

              {/* Job Cards */}
              <div className="space-y-4">
                {loading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
                  </div>
                ) : filteredJobs.length > 0 ? (
                  filteredJobs.map((job, index) => (
                    <JobCard key={job.id} job={job} index={index} />
                  ))
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-16"
                  >
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-dark-700 flex items-center justify-center">
                      <Filter className="w-8 h-8 text-gray-600" />
                    </div>
                    <h3 className="text-xl font-medium mb-2">No jobs found</h3>
                    <p className="text-gray-500 mb-4">
                      Try adjusting your filters to see more results
                    </p>
                    <button
                      onClick={() => setFilters({
                        search: '',
                        position_type: [],
                        region: [],
                        type_rating_required: null,
                        max_hours_required: null,
                        contract_type: [],
                        aircraft_category: [],
                        visa_sponsorship: null,
                        is_entry_level: null,
                      })}
                      className="text-cyber-blue hover:underline"
                    >
                      Clear all filters
                    </button>
                  </motion.div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Mobile Filter Sheet */}
      {showMobileFilters && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 lg:hidden"
        >
          <div
            className="absolute inset-0 bg-black/80"
            onClick={() => setShowMobileFilters(false)}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            className="absolute right-0 top-0 bottom-0 w-full max-w-md bg-dark-900 overflow-y-auto"
          >
            <div className="sticky top-0 flex items-center justify-between p-4 border-b border-cyan-500/10 bg-dark-900">
              <h2 className="font-display text-lg font-bold">Filters</h2>
              <button
                onClick={() => setShowMobileFilters(false)}
                className="p-2 rounded-lg hover:bg-dark-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4">
              <JobFilters
                filters={filters}
                onFilterChange={setFilters}
                jobCount={filteredJobs.length}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </main>
  )
}

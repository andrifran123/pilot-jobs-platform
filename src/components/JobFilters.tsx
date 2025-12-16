'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  MapPin,
  Plane,
  Clock,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Globe,
  Sparkles,
} from 'lucide-react'
import { JobFilters as FilterType, REGIONS, POSITION_TYPES, CONTRACT_TYPES, AIRCRAFT_CATEGORIES } from '@/types'

interface JobFiltersProps {
  filters: FilterType
  onFilterChange: (filters: FilterType) => void
  jobCount: number
}

export default function JobFilters({ filters, onFilterChange, jobCount }: JobFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [openSection, setOpenSection] = useState<string | null>(null)

  const updateFilter = (key: keyof FilterType, value: any) => {
    onFilterChange({ ...filters, [key]: value })
  }

  const toggleArrayFilter = (key: 'position_type' | 'region' | 'contract_type' | 'aircraft_category', value: string) => {
    const current = filters[key] as string[]
    const updated = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]
    updateFilter(key, updated)
  }

  const resetFilters = () => {
    onFilterChange({
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
  }

  const activeFiltersCount = [
    filters.position_type.length,
    filters.region.length,
    filters.contract_type.length,
    filters.aircraft_category.length,
    filters.type_rating_required !== null ? 1 : 0,
    filters.max_hours_required !== null ? 1 : 0,
    filters.visa_sponsorship !== null ? 1 : 0,
    filters.is_entry_level !== null ? 1 : 0,
  ].reduce((a, b) => a + b, 0)

  return (
    <div className="cyber-card rounded-2xl p-6 sticky top-20">
      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <input
          type="text"
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          placeholder="Search jobs, airlines, aircraft..."
          className="w-full pl-12 pr-4 py-3 rounded-xl cyber-input text-white placeholder:text-gray-600"
        />
      </div>

      {/* Quick Stats */}
      <div className="flex items-center justify-between mb-6 pb-6 border-b border-cyan-500/10">
        <div>
          <span className="text-2xl font-display font-bold text-cyber-blue">{jobCount}</span>
          <span className="text-gray-500 ml-2">jobs found</span>
        </div>
        {activeFiltersCount > 0 && (
          <button
            onClick={resetFilters}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset ({activeFiltersCount})
          </button>
        )}
      </div>

      {/* Filter Sections */}
      <div className="space-y-4">
        {/* Entry Level - Big Feature Toggle */}
        <FilterSection
          title="Entry Level / Low Hours"
          icon={Sparkles}
          isOpen={openSection === 'entry_level'}
          onToggle={() => setOpenSection(openSection === 'entry_level' ? null : 'entry_level')}
          activeCount={filters.is_entry_level !== null ? 1 : 0}
        >
          <div className="space-y-2">
            <FilterChip
              label="Any Experience"
              isActive={filters.is_entry_level === null}
              onClick={() => updateFilter('is_entry_level', null)}
            />
            <FilterChip
              label="Entry Level / Low Hour Jobs"
              isActive={filters.is_entry_level === true}
              onClick={() => updateFilter('is_entry_level', true)}
              accent="green"
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Jobs with &lt;500 hours or training provided
          </p>
        </FilterSection>

        {/* Visa Sponsorship - Big Feature Toggle */}
        <FilterSection
          title="Visa Sponsorship"
          icon={Globe}
          isOpen={openSection === 'visa'}
          onToggle={() => setOpenSection(openSection === 'visa' ? null : 'visa')}
          activeCount={filters.visa_sponsorship !== null ? 1 : 0}
        >
          <div className="space-y-2">
            <FilterChip
              label="Any"
              isActive={filters.visa_sponsorship === null}
              onClick={() => updateFilter('visa_sponsorship', null)}
            />
            <FilterChip
              label="Visa Sponsorship Available"
              isActive={filters.visa_sponsorship === true}
              onClick={() => updateFilter('visa_sponsorship', true)}
              accent="green"
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Jobs offering work permits or relocation support
          </p>
        </FilterSection>

        {/* Position Type */}
        <FilterSection
          title="Position Type"
          icon={Plane}
          isOpen={openSection === 'position'}
          onToggle={() => setOpenSection(openSection === 'position' ? null : 'position')}
          activeCount={filters.position_type.length}
        >
          <div className="grid grid-cols-2 gap-2">
            {POSITION_TYPES.map((type) => (
              <FilterChip
                key={type.value}
                label={type.label}
                isActive={filters.position_type.includes(type.value)}
                onClick={() => toggleArrayFilter('position_type', type.value)}
              />
            ))}
          </div>
        </FilterSection>

        {/* Region */}
        <FilterSection
          title="Region"
          icon={MapPin}
          isOpen={openSection === 'region'}
          onToggle={() => setOpenSection(openSection === 'region' ? null : 'region')}
          activeCount={filters.region.length}
        >
          <div className="grid grid-cols-2 gap-2">
            {REGIONS.map((region) => (
              <FilterChip
                key={region.value}
                label={region.label}
                isActive={filters.region.includes(region.value)}
                onClick={() => toggleArrayFilter('region', region.value)}
              />
            ))}
          </div>
        </FilterSection>

        {/* Type Rating */}
        <FilterSection
          title="Type Rating"
          icon={Filter}
          isOpen={openSection === 'type_rating'}
          onToggle={() => setOpenSection(openSection === 'type_rating' ? null : 'type_rating')}
          activeCount={filters.type_rating_required !== null ? 1 : 0}
        >
          <div className="space-y-2">
            <FilterChip
              label="Any"
              isActive={filters.type_rating_required === null}
              onClick={() => updateFilter('type_rating_required', null)}
            />
            <FilterChip
              label="Not Required"
              isActive={filters.type_rating_required === false}
              onClick={() => updateFilter('type_rating_required', false)}
              accent="green"
            />
            <FilterChip
              label="Required"
              isActive={filters.type_rating_required === true}
              onClick={() => updateFilter('type_rating_required', true)}
            />
          </div>
        </FilterSection>

        {/* Experience */}
        <FilterSection
          title="Max Hours Required"
          icon={Clock}
          isOpen={openSection === 'hours'}
          onToggle={() => setOpenSection(openSection === 'hours' ? null : 'hours')}
          activeCount={filters.max_hours_required !== null ? 1 : 0}
        >
          <div className="space-y-3">
            <input
              type="range"
              min="0"
              max="5000"
              step="100"
              value={filters.max_hours_required || 5000}
              onChange={(e) => {
                const value = parseInt(e.target.value)
                updateFilter('max_hours_required', value === 5000 ? null : value)
              }}
              className="w-full accent-cyber-blue"
            />
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">0 hrs</span>
              <span className="text-cyber-blue font-mono">
                {filters.max_hours_required ? `${filters.max_hours_required} hrs` : 'Any'}
              </span>
              <span className="text-gray-500">5000+ hrs</span>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {[500, 1000, 1500].map((hours) => (
                <button
                  key={hours}
                  onClick={() => updateFilter('max_hours_required', hours)}
                  className={`py-2 px-3 rounded-lg text-sm transition-colors ${
                    filters.max_hours_required === hours
                      ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/50'
                      : 'bg-dark-700 text-gray-400 hover:text-white border border-transparent'
                  }`}
                >
                  {hours} hrs
                </button>
              ))}
            </div>
          </div>
        </FilterSection>

        {/* Contract Type */}
        <FilterSection
          title="Contract Type"
          icon={Filter}
          isOpen={openSection === 'contract'}
          onToggle={() => setOpenSection(openSection === 'contract' ? null : 'contract')}
          activeCount={filters.contract_type.length}
        >
          <div className="grid grid-cols-2 gap-2">
            {CONTRACT_TYPES.map((type) => (
              <FilterChip
                key={type.value}
                label={type.label}
                isActive={filters.contract_type.includes(type.value)}
                onClick={() => toggleArrayFilter('contract_type', type.value)}
              />
            ))}
          </div>
        </FilterSection>

        {/* Aircraft Category */}
        <FilterSection
          title="Aircraft Type"
          icon={Plane}
          isOpen={openSection === 'aircraft'}
          onToggle={() => setOpenSection(openSection === 'aircraft' ? null : 'aircraft')}
          activeCount={filters.aircraft_category.length}
        >
          <div className="space-y-2">
            {AIRCRAFT_CATEGORIES.map((cat) => (
              <FilterChip
                key={cat.value}
                label={cat.label}
                isActive={filters.aircraft_category.includes(cat.value)}
                onClick={() => toggleArrayFilter('aircraft_category', cat.value)}
              />
            ))}
          </div>
        </FilterSection>
      </div>
    </div>
  )
}

function FilterSection({
  title,
  icon: Icon,
  isOpen,
  onToggle,
  activeCount,
  children,
}: {
  title: string
  icon: typeof Filter
  isOpen: boolean
  onToggle: () => void
  activeCount: number
  children: React.ReactNode
}) {
  return (
    <div className="border border-cyan-500/10 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-cyan-500/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-4 h-4 text-cyber-blue" />
          <span className="text-sm font-medium">{title}</span>
          {activeCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-cyber-blue/20 text-cyber-blue text-xs">
              {activeCount}
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-4 pt-0">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function FilterChip({
  label,
  isActive,
  onClick,
  accent = 'blue',
}: {
  label: string
  isActive: boolean
  onClick: () => void
  accent?: 'blue' | 'green' | 'purple'
}) {
  const accentColors = {
    blue: 'bg-cyber-blue/20 text-cyber-blue border-cyber-blue/50',
    green: 'bg-green-500/20 text-green-400 border-green-500/50',
    purple: 'bg-cyber-purple/20 text-cyber-purple border-cyber-purple/50',
  }

  return (
    <button
      onClick={onClick}
      className={`py-2 px-3 rounded-lg text-sm transition-all ${
        isActive
          ? accentColors[accent]
          : 'bg-dark-700 text-gray-400 hover:text-white border-transparent'
      } border`}
    >
      {label}
    </button>
  )
}

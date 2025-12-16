'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MapPin,
  Plane,
  Clock,
  Building2,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { PilotJob } from '@/types'

interface JobCardProps {
  job: PilotJob
  index: number
}

export default function JobCard({ job, index }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isSaved, setIsSaved] = useState(false)

  const positionColors: Record<string, string> = {
    captain: 'from-amber-500/20 to-orange-500/20 text-amber-400 border-amber-500/30',
    first_officer: 'from-cyber-blue/20 to-blue-500/20 text-cyber-blue border-cyber-blue/30',
    cadet: 'from-green-500/20 to-emerald-500/20 text-green-400 border-green-500/30',
    instructor: 'from-purple-500/20 to-violet-500/20 text-purple-400 border-purple-500/30',
    other: 'from-gray-500/20 to-slate-500/20 text-gray-400 border-gray-500/30',
  }

  const formatHours = (hours: number | null) => {
    if (!hours) return 'Not specified'
    return `${hours.toLocaleString()} hrs`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="group cyber-card rounded-2xl overflow-hidden hover:border-cyber-blue/30 transition-all duration-300"
    >
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1">
            {/* Position Badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border bg-gradient-to-r ${
                positionColors[job.position_type]
              } mb-3`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              {job.position_type.replace('_', ' ').toUpperCase()}
            </span>

            {/* Title */}
            <h3 className="text-xl font-semibold text-white group-hover:text-cyber-blue transition-colors mb-2">
              {job.title}
            </h3>

            {/* Company & Location */}
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
              <span className="flex items-center gap-1.5">
                <Building2 className="w-4 h-4" />
                {job.company}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin className="w-4 h-4" />
                {job.location}
              </span>
              <span className="flex items-center gap-1.5">
                <Plane className="w-4 h-4" />
                {job.aircraft_type || 'Various'}
              </span>
            </div>
          </div>

          {/* Save Button */}
          <button
            onClick={() => setIsSaved(!isSaved)}
            className={`p-2 rounded-lg transition-colors ${
              isSaved
                ? 'bg-cyber-blue/20 text-cyber-blue'
                : 'bg-dark-700 text-gray-500 hover:text-white'
            }`}
          >
            {isSaved ? (
              <BookmarkCheck className="w-5 h-5" />
            ) : (
              <Bookmark className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Quick Info */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <InfoBadge
            label="Total Time"
            value={formatHours(job.min_total_hours)}
            icon={Clock}
          />
          <InfoBadge
            label="PIC Hours"
            value={formatHours(job.min_pic_hours)}
            icon={Clock}
          />
          <InfoBadge
            label="Type Rating"
            value={job.type_rating_required ? 'Required' : 'Not Required'}
            icon={job.type_rating_required ? XCircle : CheckCircle2}
            accent={job.type_rating_required ? 'red' : 'green'}
          />
          <InfoBadge
            label="Contract"
            value={job.contract_type}
            icon={Building2}
          />
        </div>
      </div>

      {/* Expandable Section */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-cyan-500/10 overflow-hidden"
          >
            <div className="p-6 space-y-4">
              {/* Description */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">Description</h4>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {job.description}
                </p>
              </div>

              {/* Requirements */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Requirements</h4>
                  <ul className="space-y-2 text-sm">
                    <li className="flex items-center gap-2 text-gray-300">
                      <span className="w-1 h-1 rounded-full bg-cyber-blue" />
                      License: {job.license_required}
                    </li>
                    {job.min_total_hours && (
                      <li className="flex items-center gap-2 text-gray-300">
                        <span className="w-1 h-1 rounded-full bg-cyber-blue" />
                        Min Total: {job.min_total_hours} hrs
                      </li>
                    )}
                    {job.min_type_hours && (
                      <li className="flex items-center gap-2 text-gray-300">
                        <span className="w-1 h-1 rounded-full bg-cyber-blue" />
                        Type Hours: {job.min_type_hours} hrs
                      </li>
                    )}
                  </ul>
                </div>

                {job.benefits && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Benefits</h4>
                    <p className="text-sm text-gray-300">{job.benefits}</p>
                  </div>
                )}
              </div>

              {/* Type Rating Provided */}
              {job.type_rating_provided && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                  <span className="text-sm text-green-400 font-medium">
                    Type rating will be provided by the airline
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <div className="flex items-center justify-between p-4 border-t border-cyan-500/10 bg-dark-800/50">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                Show More
              </>
            )}
          </button>

          <span className="text-xs text-gray-600">
            Posted {job.date_posted}
          </span>
        </div>

        <a
          href={job.application_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyber-blue to-cyber-purple text-white text-sm font-medium hover:shadow-lg hover:shadow-cyber-blue/25 transition-all"
        >
          Apply Now
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </motion.div>
  )
}

function InfoBadge({
  label,
  value,
  icon: Icon,
  accent = 'default',
}: {
  label: string
  value: string
  icon: typeof Clock
  accent?: 'default' | 'green' | 'red'
}) {
  const accentColors = {
    default: 'text-gray-400',
    green: 'text-green-400',
    red: 'text-red-400',
  }

  return (
    <div className="p-3 rounded-xl bg-dark-700/50 border border-cyan-500/5">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-3.5 h-3.5 ${accentColors[accent]}`} />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <span className={`text-sm font-medium ${accentColors[accent]}`}>
        {value}
      </span>
    </div>
  )
}

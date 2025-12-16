'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import { Search, MapPin, Plane, Users, Briefcase, ArrowRight, ChevronDown } from 'lucide-react'
import Navbar from '@/components/Navbar'

// Dynamic import for Globe to avoid SSR issues with Three.js
const Globe = dynamic(() => import('@/components/Globe'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-16 h-16 border-4 border-cyber-blue/20 border-t-cyber-blue rounded-full animate-spin" />
    </div>
  ),
})

const stats = [
  { value: '2,500+', label: 'Active Jobs', icon: Briefcase },
  { value: '150+', label: 'Airlines', icon: Plane },
  { value: '45+', label: 'Countries', icon: MapPin },
  { value: '10K+', label: 'Pilots', icon: Users },
]

const features = [
  {
    title: 'Smart Filtering',
    description: 'Find jobs matching your exact qualifications - hours, ratings, and preferences.',
    icon: '01',
  },
  {
    title: 'Global Coverage',
    description: 'Jobs from every continent. Europe, Middle East, Asia, and beyond.',
    icon: '02',
  },
  {
    title: 'Real-Time Updates',
    description: 'Fresh job listings scraped daily from 50+ sources worldwide.',
    icon: '03',
  },
  {
    title: 'Direct Applications',
    description: 'One-click apply directly to airline career pages.',
    icon: '04',
  },
]

export default function HomePage() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <main className="relative min-h-screen overflow-hidden">
      <Navbar />

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center">
        {/* Globe Background */}
        <div className="absolute inset-0 z-0">
          {mounted && <Globe />}
        </div>

        {/* Gradient Overlays */}
        <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/80 to-transparent z-10" />
        <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-transparent to-dark-900/50 z-10" />

        {/* Content */}
        <div className="relative z-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20">
          <div className="max-w-2xl">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyber-blue/10 border border-cyber-blue/20 text-cyber-blue text-sm mb-6">
                <span className="w-2 h-2 rounded-full bg-cyber-blue animate-pulse" />
                Now tracking 2,500+ pilot positions worldwide
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
              className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold leading-tight mb-6"
            >
              Your Next
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue via-cyber-purple to-cyber-pink">
                Flight Deck
              </span>
              <br />
              Awaits
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-lg text-gray-400 mb-8 leading-relaxed"
            >
              The most comprehensive pilot job platform. Find Captain, First Officer,
              and Cadet positions worldwide. Filter by hours, type ratings, and location.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="flex flex-col sm:flex-row gap-4"
            >
              <Link
                href="/jobs"
                className="group flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyber-blue to-cyber-purple text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyber-blue/25 transition-all duration-300"
              >
                <Search className="w-5 h-5" />
                Find Jobs
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>

              <Link
                href="/auth/signup"
                className="flex items-center justify-center gap-2 px-8 py-4 rounded-xl cyber-btn text-gray-300 hover:text-white font-semibold text-lg"
              >
                Create Profile
              </Link>
            </motion.div>
          </div>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="flex flex-col items-center gap-2 text-gray-500"
          >
            <span className="text-xs uppercase tracking-widest">Scroll</span>
            <ChevronDown className="w-5 h-5" />
          </motion.div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="relative z-20 -mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="cyber-card rounded-2xl p-6 text-center group hover:scale-105 transition-transform duration-300"
              >
                <stat.icon className="w-8 h-8 text-cyber-blue mx-auto mb-3 group-hover:scale-110 transition-transform" />
                <div className="font-display text-3xl font-bold text-white mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-500">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-20 py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl font-bold mb-4">
              Why <span className="text-cyber-blue">SkyLink</span>?
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              We aggregate pilot jobs from across the globe, so you can focus on what matters - flying.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="cyber-card rounded-2xl p-6 group"
              >
                <div className="font-display text-5xl font-bold text-cyber-blue/20 group-hover:text-cyber-blue/40 transition-colors mb-4">
                  {feature.icon}
                </div>
                <h3 className="font-semibold text-xl text-white mb-2">{feature.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-20 py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="cyber-card rounded-3xl p-12 relative overflow-hidden"
          >
            {/* Background Effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-cyber-blue/5 via-cyber-purple/5 to-cyber-pink/5" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyber-blue/10 rounded-full blur-3xl" />

            <div className="relative">
              <h2 className="font-display text-4xl font-bold mb-4">
                Ready to Take Off?
              </h2>
              <p className="text-gray-400 mb-8 max-w-xl mx-auto">
                Create your pilot profile and get matched with opportunities that fit your experience.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/auth/signup"
                  className="group flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyber-blue to-cyber-purple text-white font-semibold hover:shadow-lg hover:shadow-cyber-blue/25 transition-all"
                >
                  Get Started Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  href="/jobs"
                  className="flex items-center justify-center gap-2 px-8 py-4 rounded-xl cyber-btn text-gray-300 hover:text-white font-semibold"
                >
                  Browse Jobs First
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-20 border-t border-cyan-500/10 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-3">
              <Plane className="w-6 h-6 text-cyber-blue transform -rotate-45" />
              <span className="font-display text-lg font-bold">
                <span className="text-white">SKY</span>
                <span className="text-cyber-blue">LINK</span>
              </span>
            </div>

            <div className="flex items-center gap-8 text-sm text-gray-500">
              <Link href="/privacy" className="hover:text-white transition-colors">
                Privacy
              </Link>
              <Link href="/terms" className="hover:text-white transition-colors">
                Terms
              </Link>
              <Link href="/contact" className="hover:text-white transition-colors">
                Contact
              </Link>
            </div>

            <p className="text-sm text-gray-600">
              &copy; {new Date().getFullYear()} SkyLink. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </main>
  )
}

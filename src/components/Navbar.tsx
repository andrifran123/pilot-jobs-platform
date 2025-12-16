'use client'

import Link from 'next/link'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plane, Menu, X, User, LogOut, Bookmark, Settings } from 'lucide-react'

interface NavbarProps {
  user?: { email: string; full_name?: string } | null
}

export default function Navbar({ user }: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isProfileOpen, setIsProfileOpen] = useState(false)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-dark-900/80 backdrop-blur-xl border-b border-cyan-500/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              <Plane className="w-8 h-8 text-cyber-blue transform -rotate-45 group-hover:rotate-0 transition-transform duration-300" />
              <div className="absolute inset-0 bg-cyber-blue/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <span className="font-display text-xl font-bold tracking-wider">
              <span className="text-white">SKY</span>
              <span className="text-cyber-blue glow-text">LINK</span>
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <NavLink href="/jobs">Find Jobs</NavLink>
            <NavLink href="/airlines">Airlines</NavLink>
            <NavLink href="/resources">Resources</NavLink>
            <NavLink href="/about">About</NavLink>
          </div>

          {/* Auth Section */}
          <div className="hidden md:flex items-center gap-4">
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setIsProfileOpen(!isProfileOpen)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg cyber-btn"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyber-blue to-cyber-purple flex items-center justify-center">
                    <span className="text-sm font-bold">
                      {user.full_name?.[0] || user.email[0].toUpperCase()}
                    </span>
                  </div>
                  <span className="text-sm text-gray-300">{user.full_name || user.email}</span>
                </button>

                <AnimatePresence>
                  {isProfileOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute right-0 mt-2 w-56 cyber-card rounded-xl overflow-hidden"
                    >
                      <div className="p-2">
                        <ProfileMenuItem href="/profile" icon={User}>
                          My Profile
                        </ProfileMenuItem>
                        <ProfileMenuItem href="/saved" icon={Bookmark}>
                          Saved Jobs
                        </ProfileMenuItem>
                        <ProfileMenuItem href="/settings" icon={Settings}>
                          Settings
                        </ProfileMenuItem>
                        <hr className="my-2 border-cyan-500/10" />
                        <button className="w-full flex items-center gap-3 px-4 py-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                          <LogOut className="w-4 h-4" />
                          Sign Out
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <>
                <Link
                  href="/auth/login"
                  className="px-4 py-2 text-sm text-gray-300 hover:text-cyber-blue transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/auth/signup"
                  className="px-6 py-2 rounded-lg cyber-btn font-medium text-cyber-blue hover:text-white transition-colors"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 rounded-lg cyber-btn"
          >
            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-dark-900/95 backdrop-blur-xl border-b border-cyan-500/10"
          >
            <div className="px-4 py-6 space-y-4">
              <MobileNavLink href="/jobs" onClick={() => setIsMenuOpen(false)}>
                Find Jobs
              </MobileNavLink>
              <MobileNavLink href="/airlines" onClick={() => setIsMenuOpen(false)}>
                Airlines
              </MobileNavLink>
              <MobileNavLink href="/resources" onClick={() => setIsMenuOpen(false)}>
                Resources
              </MobileNavLink>
              <MobileNavLink href="/about" onClick={() => setIsMenuOpen(false)}>
                About
              </MobileNavLink>

              <hr className="border-cyan-500/10" />

              {user ? (
                <div className="space-y-2">
                  <MobileNavLink href="/profile" onClick={() => setIsMenuOpen(false)}>
                    My Profile
                  </MobileNavLink>
                  <MobileNavLink href="/saved" onClick={() => setIsMenuOpen(false)}>
                    Saved Jobs
                  </MobileNavLink>
                  <button className="w-full text-left px-4 py-3 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                    Sign Out
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <Link
                    href="/auth/login"
                    className="px-4 py-3 text-center text-gray-300 hover:text-white transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/auth/signup"
                    className="px-4 py-3 text-center rounded-lg cyber-btn font-medium text-cyber-blue"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="relative text-sm text-gray-400 hover:text-white transition-colors group"
    >
      {children}
      <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-cyber-blue to-cyber-purple group-hover:w-full transition-all duration-300" />
    </Link>
  )
}

function MobileNavLink({
  href,
  children,
  onClick
}: {
  href: string
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="block px-4 py-3 text-gray-300 hover:text-white hover:bg-cyan-500/5 rounded-lg transition-colors"
    >
      {children}
    </Link>
  )
}

function ProfileMenuItem({
  href,
  icon: Icon,
  children
}: {
  href: string
  icon: typeof User
  children: React.ReactNode
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-4 py-2 text-gray-300 hover:text-white hover:bg-cyan-500/10 rounded-lg transition-colors"
    >
      <Icon className="w-4 h-4" />
      {children}
    </Link>
  )
}

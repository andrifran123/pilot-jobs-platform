'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Plane, Mail, Lock, Eye, EyeOff, ArrowRight, Chrome } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      // TODO: Implement Supabase auth
      // For now, simulate login
      await new Promise(resolve => setTimeout(resolve, 1500))
      router.push('/jobs')
    } catch (err) {
      setError('Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    setIsLoading(true)
    // TODO: Implement Google OAuth with Supabase
    await new Promise(resolve => setTimeout(resolve, 1000))
    router.push('/jobs')
  }

  return (
    <main className="min-h-screen flex">
      {/* Left Panel - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 mb-12">
            <Plane className="w-8 h-8 text-cyber-blue transform -rotate-45" />
            <span className="font-display text-2xl font-bold">
              <span className="text-white">SKY</span>
              <span className="text-cyber-blue">LINK</span>
            </span>
          </Link>

          {/* Header */}
          <div className="mb-8">
            <h1 className="font-display text-3xl font-bold mb-2">Welcome Back</h1>
            <p className="text-gray-400">Sign in to continue your pilot journey</p>
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 rounded-xl cyber-input text-white placeholder:text-gray-600"
                  placeholder="pilot@example.com"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-12 pr-12 py-3 rounded-xl cyber-input text-white placeholder:text-gray-600"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Remember & Forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-cyan-500/30 bg-transparent text-cyber-blue focus:ring-cyber-blue/50"
                />
                <span className="text-sm text-gray-400">Remember me</span>
              </label>
              <Link href="/auth/forgot-password" className="text-sm text-cyber-blue hover:underline">
                Forgot password?
              </Link>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-gradient-to-r from-cyber-blue to-cyber-purple text-white font-semibold hover:shadow-lg hover:shadow-cyber-blue/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-cyan-500/10" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-dark-900 text-gray-500">or continue with</span>
            </div>
          </div>

          {/* Social Login */}
          <button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 py-4 rounded-xl cyber-btn text-gray-300 hover:text-white transition-colors disabled:opacity-50"
          >
            <Chrome className="w-5 h-5" />
            Continue with Google
          </button>

          {/* Sign Up Link */}
          <p className="mt-8 text-center text-gray-500">
            Don't have an account?{' '}
            <Link href="/auth/signup" className="text-cyber-blue hover:underline">
              Create one
            </Link>
          </p>
        </motion.div>
      </div>

      {/* Right Panel - Visual */}
      <div className="hidden lg:flex w-1/2 relative overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyber-blue/20 via-cyber-purple/20 to-cyber-pink/20" />

        {/* Grid */}
        <div className="absolute inset-0 cyber-grid-bg opacity-50" />

        {/* Content */}
        <div className="relative z-10 flex flex-col items-center justify-center p-12 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
          >
            {/* Animated Plane */}
            <motion.div
              animate={{
                y: [0, -20, 0],
                rotate: [-5, 5, -5],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
              className="mb-12"
            >
              <div className="relative">
                <Plane className="w-32 h-32 text-cyber-blue transform -rotate-45" />
                <div className="absolute inset-0 bg-cyber-blue/30 blur-3xl rounded-full" />
              </div>
            </motion.div>

            <h2 className="font-display text-3xl font-bold mb-4 glow-text">
              2,500+ Jobs Waiting
            </h2>
            <p className="text-gray-400 max-w-sm">
              From cadet programs to captain positions. Your next opportunity is just a click away.
            </p>

            {/* Stats */}
            <div className="mt-12 flex gap-8">
              <div className="text-center">
                <div className="font-display text-2xl font-bold text-cyber-blue">150+</div>
                <div className="text-sm text-gray-500">Airlines</div>
              </div>
              <div className="text-center">
                <div className="font-display text-2xl font-bold text-cyber-purple">45+</div>
                <div className="text-sm text-gray-500">Countries</div>
              </div>
              <div className="text-center">
                <div className="font-display text-2xl font-bold text-cyber-pink">Daily</div>
                <div className="text-sm text-gray-500">Updates</div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Decorative Elements */}
        <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-cyber-blue/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-64 h-64 bg-cyber-purple/10 rounded-full blur-3xl" />
      </div>
    </main>
  )
}

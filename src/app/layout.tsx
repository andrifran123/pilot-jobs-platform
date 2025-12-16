import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SkyLink | Global Pilot Jobs Platform',
  description: 'Find your next aviation career opportunity worldwide. Non-type rated pilot jobs for CPL/ME/IR holders.',
  keywords: 'pilot jobs, aviation careers, first officer, captain, airline jobs, CPL, ATPL',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-dark-900 cyber-grid-bg noise-overlay">
        {children}
      </body>
    </html>
  )
}

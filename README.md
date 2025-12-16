# SkyLink - Global Pilot Jobs Platform

A futuristic web platform for pilots to find aviation job opportunities worldwide. Built with Next.js 14, Three.js, Tailwind CSS, and Supabase.

![SkyLink Preview](preview.png)

## Features

- **Interactive 3D Globe** - Stunning Three.js globe animation on homepage
- **Smart Filtering** - Filter jobs by position, region, hours, type rating requirements
- **Real-time Job Search** - Search across titles, companies, locations, and aircraft
- **User Authentication** - Secure signup/login with Supabase Auth
- **Save Jobs** - Bookmark interesting positions for later
- **Responsive Design** - Works perfectly on desktop and mobile
- **Futuristic UI** - Cyberpunk-inspired design with glowing effects

## Tech Stack

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript
- **Styling**: Tailwind CSS, Framer Motion
- **3D Graphics**: Three.js, React Three Fiber, React Three Drei
- **Backend**: Supabase (PostgreSQL, Auth, Realtime)
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Supabase account

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/skylink-pilot-jobs.git
cd skylink-pilot-jobs
```

2. Install dependencies:
```bash
npm install
```

3. Set up Supabase:
   - Create a new project at [supabase.com](https://supabase.com)
   - Run the SQL schema in `supabase-schema.sql` in the SQL Editor
   - Copy your project URL and anon key

4. Configure environment variables:
```bash
cp .env.example .env.local
```
Edit `.env.local` with your Supabase credentials:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

5. Run the development server:
```bash
npm run dev
```

6. Open [http://localhost:3000](http://localhost:3000)

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Import project in [Vercel](https://vercel.com)
3. Add environment variables in Vercel dashboard
4. Deploy!

### Manual Deployment

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/
│   ├── api/
│   │   └── jobs/          # API routes for job data
│   ├── auth/
│   │   ├── login/         # Login page
│   │   └── signup/        # Signup page
│   ├── jobs/              # Job search page
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Homepage with globe
├── components/
│   ├── Globe.tsx          # 3D globe component
│   ├── JobCard.tsx        # Job listing card
│   ├── JobFilters.tsx     # Filter sidebar
│   └── Navbar.tsx         # Navigation bar
├── lib/
│   └── supabase.ts        # Supabase client
└── types/
    └── index.ts           # TypeScript types
```

## Scraper Integration

The platform includes an API endpoint for the job scraper:

```bash
POST /api/jobs
Headers: x-api-key: your_scraper_key
Body: [array of job objects]
```

See the Python scraper in `/scraper` directory for reference.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (server only) |
| `SCRAPER_API_KEY` | API key for scraper endpoint |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

---

Built with passion for pilots worldwide.

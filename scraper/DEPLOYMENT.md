# Deploying Your 24/7 Pilot Job Scraper

This guide explains how to deploy your scraper to run automatically and continuously, making your site "The Google of Pilot Jobs."

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR USERS                                   │
│                         ↓                                        │
├─────────────────────────────────────────────────────────────────┤
│              FRONTEND (Vercel - Next.js)                         │
│              https://your-site.vercel.app                        │
│                         ↓ reads from                             │
├─────────────────────────────────────────────────────────────────┤
│              SUPABASE (PostgreSQL Database)                      │
│              • pilot_jobs table with all jobs                    │
│              • Real-time updates                                 │
│              • User accounts & saved jobs                        │
│                         ↑ writes to                              │
├─────────────────────────────────────────────────────────────────┤
│              SCRAPER SERVER (VPS - Always Running)               │
│              • Runs every 4 hours automatically                  │
│              • Scrapes 50+ airline career sites                  │
│              • Normalizes & deduplicates data                    │
│              • Cost: ~$5-12/month                                │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Set Up Supabase

### 1.1 Create a Supabase Project

1. Go to https://supabase.com and create a free account
2. Create a new project (choose a region close to your users)
3. Wait for the project to initialize (~2 minutes)

### 1.2 Run the Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Copy and paste the contents of `supabase-schema.sql`
3. Click **Run** to create all tables

### 1.3 Get Your API Keys

Go to **Project Settings > API** and copy:
- `SUPABASE_URL` - Your project URL
- `SUPABASE_ANON_KEY` - For frontend (public)
- `SUPABASE_SERVICE_KEY` - For scraper (secret, full access)

### 1.4 Update Environment Variables

Create `.env` file in the scraper folder:

```bash
# Supabase credentials for scraper
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs... (your service key)
```

Update `.env.local` in the main project folder (for frontend):

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs... (your anon key)
```

## Step 2: Deploy the Scraper Server

You have several options for running the scraper 24/7:

### Option A: Railway (Easiest - Recommended)

Railway offers a free tier and easy Python deployment.

1. Go to https://railway.app and sign up
2. Click **New Project > Deploy from GitHub**
3. Connect your repo and select the `scraper` folder
4. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
5. Create a `Procfile` in the scraper folder:
   ```
   worker: python scheduler.py
   ```

**Cost**: Free tier available, then ~$5/month

### Option B: DigitalOcean Droplet

1. Create a $6/month Basic Droplet (Ubuntu 22.04)
2. SSH into your server:
   ```bash
   ssh root@your-server-ip
   ```

3. Install dependencies:
   ```bash
   apt update && apt upgrade -y
   apt install python3 python3-pip python3-venv -y

   # Install Playwright dependencies
   apt install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
     libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
     libxfixes3 libxrandr2 libgbm1 libasound2 -y
   ```

4. Clone your repo:
   ```bash
   git clone https://github.com/yourusername/pilot-jobs-platform.git
   cd pilot-jobs-platform/scraper
   ```

5. Set up Python environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

6. Create environment file:
   ```bash
   nano .env
   # Add your Supabase credentials
   ```

7. Set up systemd service for auto-restart:
   ```bash
   sudo nano /etc/systemd/system/pilot-scraper.service
   ```

   Paste:
   ```ini
   [Unit]
   Description=Pilot Jobs Scraper
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/pilot-jobs-platform/scraper
   Environment=PATH=/root/pilot-jobs-platform/scraper/venv/bin
   ExecStart=/root/pilot-jobs-platform/scraper/venv/bin/python scheduler.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

8. Start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pilot-scraper
   sudo systemctl start pilot-scraper

   # Check status
   sudo systemctl status pilot-scraper

   # View logs
   journalctl -u pilot-scraper -f
   ```

**Cost**: $6/month

### Option C: AWS EC2 / Google Cloud

Similar to DigitalOcean, but with more complex setup. Use a t3.micro (AWS) or e2-micro (GCP) instance.

**Cost**: ~$10-15/month

## Step 3: Deploy Frontend to Vercel

1. Push your code to GitHub
2. Go to https://vercel.com
3. Import your GitHub repo
4. Add environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. Deploy!

Vercel will automatically:
- Deploy on every push to `main`
- Provide SSL certificate
- Handle scaling

**Cost**: Free for most use cases

## Step 4: Update Frontend to Use Supabase

Your frontend API route (`src/app/api/jobs/route.ts`) is already set up to read from the JSON file. To switch to Supabase:

1. Update the API route to query Supabase directly
2. The scraper will populate the database
3. Frontend reads from Supabase = instant updates

## Monitoring & Maintenance

### Check Scraper Status

SSH into your server and run:
```bash
# View live logs
journalctl -u pilot-scraper -f

# Check if running
systemctl status pilot-scraper

# Restart if needed
systemctl restart pilot-scraper
```

### View in Supabase

1. Go to your Supabase dashboard
2. Click **Table Editor**
3. Select `pilot_jobs` table
4. See all scraped jobs with filters!

### Common Issues

**Problem**: Scraper finds 0 jobs
**Solution**: Airlines change their website structure. Check the logs and update the scraper selectors.

**Problem**: Blocked by website
**Solution**:
- Add residential proxies (Bright Data, Smartproxy ~$10/month)
- Rotate user agents
- Add more delay between requests

**Problem**: Database full
**Solution**: Supabase free tier = 500MB. Delete old/inactive jobs with:
```sql
DELETE FROM pilot_jobs WHERE date_scraped < NOW() - INTERVAL '30 days' AND is_active = false;
```

## Cost Summary

| Service | Cost/Month | Purpose |
|---------|------------|---------|
| Supabase | Free - $25 | Database |
| Railway/DigitalOcean | $5-6 | Scraper server |
| Vercel | Free | Frontend hosting |
| Proxies (optional) | $10-20 | Avoid blocking |
| **Total** | **$5-50** | Full platform |

## Scaling Up

When you get more users:

1. **Add more airlines**: The scraper infrastructure supports 100+ airlines
2. **Increase frequency**: Change `SCRAPE_INTERVAL_HOURS` to 2 or 1
3. **Add priority scraping**: Check top airlines every 30 minutes
4. **Use residential proxies**: Essential for scale
5. **Upgrade Supabase**: Pro plan for more storage and features

## Next Steps

1. [ ] Set up Supabase and run the schema
2. [ ] Deploy scraper to Railway or DigitalOcean
3. [ ] Deploy frontend to Vercel
4. [ ] Monitor first 24 hours of scraping
5. [ ] Add more airline scrapers as needed
6. [ ] Set up email alerts for new jobs (Supabase Edge Functions)

---

**Your scraper is now ready to run 24/7 and make your site THE destination for pilot jobs!**

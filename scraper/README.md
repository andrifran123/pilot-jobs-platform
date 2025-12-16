# Universal Airline Scraper System

A production-grade, scalable scraper system that can handle 200+ airlines without writing individual scripts for each one.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIVERSAL SCRAPER SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   │   HUNTER    │    │   ENGINE    │    │    QUEUE    │    │
│   │ (Discovery) │    │ (Scraping)  │    │ (Scheduler) │    │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│          │                  │                  │            │
│          └──────────────────┼──────────────────┘            │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │   ATS ROUTER    │                      │
│                    │ (Auto-Detect)   │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│   ┌─────────┬───────────────┼───────────────┬─────────┐    │
│   │         │               │               │         │    │
│   ▼         ▼               ▼               ▼         ▼    │
│ TALEO   WORKDAY    SUCCESSFACTORS    BRASSRING   CUSTOM   │
│ Scraper  Scraper      Scraper         Scraper   AI Scraper │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   SUPABASE     │
                    │   Database     │
                    └────────────────┘
```

## Key Components

### 1. Universal Engine (`universal_engine.py`)
The brain of the system. It:
- Auto-detects the ATS (Applicant Tracking System) each airline uses
- Routes to the correct "Master Scraper" for that ATS
- Normalizes job data to a standard format
- Saves jobs to Supabase

### 2. Smart Queue (`smart_queue.py`)
The scheduler that runs continuously:
- Picks airlines that are "due" for scraping based on tier
- Processes them in round-robin fashion
- Never crashes the server by limiting concurrent requests
- Self-heals from errors

### 3. Airline Hunter (`airline_hunter.py`)
Discovers new airlines automatically:
- Scrapes Wikipedia for airline names
- Uses Google to find career page URLs
- Auto-detects the ATS type
- Adds new airlines to the database

## Tier System

Airlines are organized into tiers based on importance:

| Tier | Airlines | Check Frequency | Examples |
|------|----------|-----------------|----------|
| 1 | Major | Every 2-3 hours | Emirates, Delta, Singapore |
| 2 | Medium | Every 12 hours | Wizz Air, flydubai, JetBlue |
| 3 | Regional | Every 24 hours | Ethiopian, Copa, Cebu Pacific |

## Quick Start

### 1. Initial Setup
```bash
cd scraper
pip install -r requirements.txt
python main.py setup
```

### 2. Run Database Migrations
Copy the contents of `supabase-schema.sql` to your Supabase SQL Editor and run it.

### 3. Test the Scraper
```bash
# Dry run (no database writes)
python main.py scrape --test

# Scrape a single airline
python main.py scrape --airline "Emirates"
```

### 4. Start the Queue (Production)
```bash
# Run continuously
python main.py queue

# Run one batch and exit
python main.py queue --once

# Only process Tier 1 airlines
python main.py queue --tier 1
```

### 5. Discover New Airlines
```bash
# Find a specific airline
python main.py hunt --search "Delta Air Lines"

# Full discovery from Wikipedia
python main.py hunt --limit 50
```

## Commands Reference

```bash
# Main commands
python main.py scrape              # Run universal scraper
python main.py queue               # Start continuous queue
python main.py hunt                # Discover new airlines
python main.py stats               # Show statistics
python main.py setup               # Initial setup
python main.py validate            # Validate job URLs

# Options
--test                             # Dry run, no DB writes
--airline <name>                   # Scrape single airline
--tier <1|2|3>                     # Filter by tier
--batch-size <n>                   # Airlines per batch
--limit <n>                        # Limit results
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# Optional: Search APIs for airline discovery
SERP_API_KEY=your-serper-dev-key      # serper.dev
SERPAPI_KEY=your-serpapi-key           # serpapi.com
```

## Database Schema

### airlines_to_scrape
The source of truth for all airlines to scrape.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR | Airline name (unique) |
| career_page_url | TEXT | Career page URL |
| ats_type | VARCHAR | TALEO, WORKDAY, CUSTOM_AI, etc. |
| tier | INTEGER | 1, 2, or 3 |
| scrape_frequency_hours | INTEGER | How often to check |
| last_checked | TIMESTAMP | Last scrape time |
| status | VARCHAR | active, inactive, error |
| region | VARCHAR | europe, asia, middle_east, etc. |

### scrape_logs
Analytics and debugging logs.

| Column | Type | Description |
|--------|------|-------------|
| airline_id | UUID | Reference to airline |
| ats_type_detected | VARCHAR | Detected ATS type |
| status | VARCHAR | success, failed, timeout |
| jobs_found | INTEGER | Number of jobs scraped |
| duration_seconds | DECIMAL | Time taken |
| error_message | TEXT | Error details if failed |

## Adding New Airlines

**You don't need to write code.** Just add a row to the `airlines_to_scrape` table:

```sql
INSERT INTO airlines_to_scrape (name, career_page_url, ats_type, tier, region)
VALUES ('New Airline', 'https://careers.newairline.com', 'CUSTOM_AI', 2, 'europe');
```

Or use the hunter:
```bash
python main.py hunt --search "New Airline"
```

## ATS Types Supported

| ATS | Airlines Using It | Detection Pattern |
|-----|-------------------|-------------------|
| TALEO | Emirates, Etihad, BA, Air France | `taleo.net`, `oraclecloud` |
| WORKDAY | Singapore, Qantas, JetBlue, SWISS | `myworkdayjobs.com` |
| SUCCESSFACTORS | Various European | `successfactors.com` |
| BRASSRING | Legacy systems | `brassring` |
| ICIMS | Growing ATS | `icims.com` |
| GREENHOUSE | Tech companies | `greenhouse.io` |
| CUSTOM_AI | Everything else | Fallback |

## Error Handling

The system is designed to never crash:

1. **Airline Errors**: If an airline fails 5 times, it's marked as `error` status
2. **Browser Crashes**: Playwright auto-recovers
3. **Rate Limiting**: Built-in delays between requests
4. **Network Issues**: Retries with exponential backoff

To retry failed airlines:
```bash
python main.py queue --retry-errors
```

## Monitoring

View system status:
```bash
python main.py stats
```

Output:
```
PILOT JOBS PLATFORM - SCRAPER STATISTICS
==========================================
  Total Airlines in Database: 56
  Airlines Due for Scraping: 12

  By Tier:
    Tier 1 (Major):    12
    Tier 2 (Medium):   19
    Tier 3 (Regional): 25

  By Status:
    active: 54
    error: 2
```

## Production Deployment

### Option 1: Run as a Service (Recommended)
Use systemd, PM2, or supervisor to keep the queue running:

```bash
# Using PM2
pm2 start "python main.py queue" --name pilot-scraper

# Using systemd
sudo systemctl enable pilot-scraper
sudo systemctl start pilot-scraper
```

### Option 2: Scheduled Cron Jobs
```bash
# Run scraper every hour
0 * * * * cd /path/to/scraper && python main.py scrape

# Run hunter monthly
0 0 1 * * cd /path/to/scraper && python main.py hunt --limit 100
```

### Option 3: Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY scraper/ .
RUN pip install -r requirements.txt
RUN playwright install chromium

CMD ["python", "main.py", "queue"]
```

## Scaling Considerations

- **Proxies**: For high-volume scraping, consider rotating proxies
- **Multiple Workers**: Run multiple queue instances with different tiers
- **Rate Limits**: Adjust `SLEEP_BETWEEN_AIRLINES` in `smart_queue.py`
- **Database**: Supabase handles concurrent writes well

## Troubleshooting

### "No airlines found to scrape"
- Run the SQL schema in Supabase to create tables
- Check if airlines_to_scrape has data

### "Supabase connection failed"
- Verify `SUPABASE_SERVICE_KEY` (not the anon key)
- Check network connectivity

### "Playwright error"
```bash
python -m playwright install chromium
```

### Browser crashes frequently
- Reduce batch size: `python main.py queue --batch-size 3`
- Increase memory on your server

## Files Overview

```
scraper/
├── main.py              # CLI entry point
├── universal_engine.py  # Core scraping engine
├── smart_queue.py       # Round-robin scheduler
├── airline_hunter.py    # Airline discovery
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── logs/                # Log files
│   ├── universal_engine.log
│   ├── smart_queue.log
│   └── airline_hunter.log
└── output/              # Scraped data (JSON backup)
    ├── universal_jobs.json
    └── discovered_airlines.json
```

"""
Universal Engine - AI Nuclear Option
=====================================
Brute force crawler that feeds EVERYTHING to Claude.
It doesn't guess. It grabs every link and lets AI decide.
"""

import time
import os
import random
from playwright.sync_api import sync_playwright
from supabase import create_client
from dotenv import load_dotenv
from ai_parser import parse_job_with_ai

load_dotenv()
supabase = create_client(os.getenv("NEXT_PUBLIC_SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


# --- BRUTE FORCE LINK FINDER ---
def get_potential_links(page, base_url):
    """
    Finds ALL links that might be jobs.
    Filters out ONLY technical garbage (login, privacy, etc).
    """
    print("      [*] Scanning page for potential job links...")

    # Wait for dynamic content
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except:
        pass

    all_links = page.locator("a[href]").all()
    unique_urls = set()

    # 1. THE BLOCKLIST (Skip technical pages to save money)
    BLOCKLIST = [
        "login", "signin", "register", "password", "privacy", "terms",
        "policy", "javascript:", "mailto:", "tel:", "facebook", "twitter",
        "linkedin", "instagram", "youtube", "faq", "help", "contact",
        "forgot", "reset", "accessibility", "sitemap", "language"
    ]

    # 2. THE GREENLIST (If URL/Text contains this, we MUST check it)
    GREENLIST = [
        "captain", "officer", "pilot", "instructor", "cadet", "flight-crew",
        "vacancy", "opening", "job", "career", "join", "apply", "detail"
    ]

    for link in all_links:
        try:
            href = link.get_attribute("href")
            text = link.inner_text().lower().strip()

            if not href or len(href) < 2:
                continue

            # Normalize URL
            if href.startswith("/"):
                # Handle base URL robustly
                domain = "/".join(base_url.split("/")[:3])
                href = domain + href

            href_lower = href.lower()

            # Skip Blocklisted
            if any(bad in href_lower for bad in BLOCKLIST):
                continue
            if any(bad in text for bad in BLOCKLIST):
                continue

            # Keep Greenlisted OR anything that looks like a deep link
            # We are aggressive here: If it's not blocked, we check it.
            unique_urls.add(href)

        except:
            continue

    # Limit to 40 links per airline to prevent infinite scraping on massive sites
    return list(unique_urls)[:40]


# --- THE ENGINE ---
def scrape_airline(airline):
    print(f"\n[+] Processing: {airline['name']}")

    with sync_playwright() as p:
        # Launch Headless Chrome
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 1. GO TO CAREER PAGE
            url = airline.get('career_page_url') or airline.get('url', '')
            print(f"   Navigating to: {url}...")
            page.goto(url, timeout=60000)
            time.sleep(4)  # Allow JS to load

            # 2. FIND ALL LINKS
            potential_jobs = get_potential_links(page, url)
            print(f"   Found {len(potential_jobs)} potential pages. Analyzing with AI...")

            # 3. VISIT & ANALYZE EACH LINK
            valid_jobs_count = 0

            for i, job_url in enumerate(potential_jobs):
                try:
                    # Brief pause to be polite
                    if i > 0 and i % 10 == 0:
                        time.sleep(2)

                    # Go to the specific job page
                    page.goto(job_url, timeout=30000)
                    try:
                        page.wait_for_selector("body", timeout=5000)
                    except:
                        pass

                    # Grab text
                    raw_text = page.locator("body").inner_text()

                    # AI DECISION TIME
                    ai_data = parse_job_with_ai(raw_text, job_url, airline['name'])

                    # If AI says "Not a job", skip it.
                    if not ai_data.get("is_valid_job", False):
                        continue

                    # If verified, save it!
                    print(f"      [OK] JOB CONFIRMED: {ai_data.get('job_title')} ({ai_data.get('min_hours')}h)")

                    # Save to Database
                    job_record = {
                        "company": airline['name'],
                        "title": ai_data.get('job_title', 'Pilot Position'),
                        "application_url": job_url,
                        "min_total_hours": ai_data.get('min_hours', 0),
                        "aircraft_type": ", ".join(ai_data.get('aircraft', [])) if ai_data.get('aircraft') else None,
                        "visa_sponsorship": ai_data.get('visa_sponsored', False),
                        "is_entry_level": ai_data.get('is_low_hour', False),
                        "type_rating_required": ai_data.get('type_rating_required', False),
                        "is_active": True,
                        "source": f"Direct - {airline['name']}",
                        "region": airline.get('region', 'global'),
                    }

                    # Upsert (Save)
                    supabase.table("pilot_jobs").upsert(job_record, on_conflict="application_url").execute()
                    valid_jobs_count += 1

                except Exception as e:
                    # Ignore link errors and keep moving
                    continue

            print(f"   [DONE] Finished {airline['name']}: {valid_jobs_count} valid jobs saved.")

            # Update airline last_checked
            if airline.get('id'):
                supabase.table("airlines_to_scrape").update({
                    "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "jobs_found_last_scrape": valid_jobs_count
                }).eq("id", airline['id']).execute()

        except Exception as e:
            print(f"   [X] Failed to scrape airline: {e}")
        finally:
            browser.close()


def run_engine(single_airline=None):
    """Run the scraper for all airlines or a single airline"""
    if single_airline:
        # Fetch single airline
        response = supabase.table("airlines_to_scrape").select("*").ilike("name", single_airline).limit(1).execute()
        if response.data:
            scrape_airline(response.data[0])
        else:
            print(f"Airline '{single_airline}' not found in database.")
        return

    # Fetch active airlines from DB
    rows = supabase.table("airlines_to_scrape").select("*").eq("status", "active").execute()
    if not rows.data:
        print("No airlines found in DB. Run the Hunter script first.")
        return

    print(f"Found {len(rows.data)} airlines to scrape.")

    for airline in rows.data:
        scrape_airline(airline)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Universal Airline Job Scraper - AI Nuclear Option")
    parser.add_argument("--airline", type=str, help="Scrape a single airline by name")
    args = parser.parse_args()

    run_engine(single_airline=args.airline)

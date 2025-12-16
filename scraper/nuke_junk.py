#!/usr/bin/env python3
"""
☢️ NUKE JUNK SCRIPT
====================
Deletes obvious garbage from the pilot_jobs database.
Run this to clean up mobile games, FAQs, and other non-job entries.

Usage:
    python scraper/nuke_junk.py
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("NEXT_PUBLIC_SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def nuke_junk():
    print("☢️ STARTING DATABASE CLEANUP...")

    # 1. Delete obvious junk by keywords
    junk_keywords = [
        "faq",
        "f.a.q",
        "mobile game",
        "privacy policy",
        "cookie",
        "login",
        "register",
        "talent community",
        "join our team",
        "life at",
        "why work",
        "our culture",
        "benefits",
        "contact us"
    ]

    count = 0
    for word in junk_keywords:
        response = supabase.table("pilot_jobs").delete().ilike("title", f"%{word}%").execute()
        if response.data:
            count += len(response.data)
            print(f"   Deleted {len(response.data)} jobs containing '{word}'")

    # 2. Delete jobs with no hours and no aircraft (often generic pages)
    # Be careful with this one, maybe just mark them inactive first
    # response = supabase.table("pilot_jobs").delete().eq("min_total_hours", 0).is_("aircraft_type", "null").execute()

    print(f"✅ CLEANUP COMPLETE. Removed {count} junk entries.")

if __name__ == "__main__":
    nuke_junk()

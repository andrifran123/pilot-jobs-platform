#!/usr/bin/env python3
"""
Nuke Junk Script - Clean up garbage from the database
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("NEXT_PUBLIC_SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def clean_database():
    print("[*] Cleaning database...")

    # 1. Delete anything with 'FAQ' or 'Game' in the title
    response = supabase.table("pilot_jobs").delete().or_("title.ilike.%FAQ%,title.ilike.%Game%,title.ilike.%Login%").execute()
    print(f"Deleted {len(response.data)} junk rows.")

    # 2. Delete jobs with 0 hours AND no aircraft type (usually generic pages)
    # response = supabase.table("pilot_jobs").delete().eq("min_total_hours", 0).is_("aircraft", "null").execute()

    print("[+] Database clean.")

if __name__ == "__main__":
    clean_database()

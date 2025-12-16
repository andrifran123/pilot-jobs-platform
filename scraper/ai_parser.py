import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize the client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def parse_job_with_ai(raw_text, url, company_name=""):
    """
    Sends raw job text to Claude 3 Haiku to extract structured data.
    NOW INCLUDES VALIDATION: Returns is_valid_job=False for junk.
    """

    system_prompt = """
    You are an expert aviation recruiter API.
    Analyze the text from a webpage to determine if it is a SPECIFIC JOB OPENING for a Pilot.

    RETURN JSON ONLY.

    Validation Rules:
    - is_valid_job: boolean. Set to FALSE if this page is:
        - A list of jobs (not a specific job)
        - A generic "Careers" landing page
        - A "FAQ" or "Contact Us" page
        - A login/register page
        - A blog post or news article
        - A "Join our Talent Community" page
        - A mobile game or app advertisement

    Extraction Rules (Only if is_valid_job is true):
    - min_hours: The absolute minimum Total Flight Time required (integer). Return 0 if not found.
    - aircraft: List of specific aircraft type ratings required (e.g. ["A320", "B737"]).
    - visa_sponsored: boolean.
    - job_title: The specific role (e.g. "Captain", "First Officer").
    - is_low_hour: boolean (true if min_hours < 500).
    """

    user_message = f"""
    Analyze this page content for {company_name} ({url}):

    {raw_text[:4000]}
    """

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        json_str = response.content[0].text.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1].replace("json", "").strip()

        data = json.loads(json_str)
        return data

    except Exception as e:
        print(f"[X] AI Parsing Failed for {url}: {e}")
        return {"is_valid_job": False}

import json
import os
import re
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize Claude
try:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
except:
    client = None

def parse_job_with_ai(raw_text, url, company_name):
    """
    The 'Nuclear' Parser.
    It reads the page text and decides if it is a VALID PILOT JOB.
    """
    if not client:
        return {"is_valid_job": False}

    system_prompt = """
    You are an expert aviation recruiter.
    Analyze the webpage text provided.

    YOUR GOAL:
    1. Decide if this is a SPECIFIC JOB OPENING for a Pilot (Captain, FO, Instructor, Cadet).
    2. If yes, extract the details into JSON.

    RULES FOR 'is_valid_job':
    - TRUE if: It is a job description for a specific pilot role (e.g. "B737 Captain", "Flight Instructor").
    - FALSE if: It is a list of jobs, a search page, a login page, a "Register Interest" page, a blog post, a news article, or a "Life at Emirates" marketing page.

    EXTRACTION FIELDS (If valid):
    - job_title: The exact role title.
    - min_hours: The absolute minimum total flight time required (Integer). Return 0 if not specified.
    - aircraft: List of aircraft type ratings REQUIRED (e.g. ["A320", "B737"]).
    - type_rating_required: Boolean (True if they require you to already have the rating).
    - visa_sponsored: Boolean (True if the text explicitly says they provide/sponsor visas).
    - is_low_hour: Boolean (True if min_hours < 500 or text says "Cadet"/"Entry Level").
    """

    user_message = f"""
    Company: {company_name}
    URL: {url}

    PAGE TEXT:
    {raw_text[:6000]}
    """

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        # Clean response
        json_str = response.content[0].text.strip()
        if "```" in json_str:
            json_str = json_str.split("```json")[-1].split("```")[0].strip()

        return json.loads(json_str)

    except Exception as e:
        print(f"      [X] AI Analysis Failed: {e}")
        return {"is_valid_job": False}

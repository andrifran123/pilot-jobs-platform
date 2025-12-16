#!/usr/bin/env python3
"""
AI-Powered Job Parser using Claude 3 Haiku
==========================================
Sends raw job text to Claude and gets back clean structured JSON.
This replaces all regex and hardcoded parsing logic.
"""

import json
import os
import logging
from typing import Dict, Any, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment from project root - use override to ensure our .env takes precedence
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    # Fallback: try current directory
    load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Initialize the Anthropic client
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
logger.info(f"Anthropic API Key: {'Loaded' if ANTHROPIC_API_KEY else 'Not found'}")

if ANTHROPIC_API_KEY:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None
    logger.warning("ANTHROPIC_API_KEY not set - AI parsing disabled, falling back to regex")


# System prompt for the AI - very specific instructions
SYSTEM_PROMPT = """
You are an expert aviation recruiter API.
Your job is to extract specific pilot job requirements from unstructured text.
Return ONLY valid JSON. No markdown, no conversational text, no explanations.

Extraction Rules:
- min_hours: The absolute minimum Total Flight Time required as an integer. (Return null if not specified).
- min_pic_hours: Minimum Pilot-in-Command hours if mentioned, as integer. (Return null if not specified).
- aircraft: List of aircraft types mentioned (e.g. ["A320", "B737", "B777"]). Normalize to standard codes.
- type_rating_required: Boolean - does the job require you to already have the type rating?
- type_rating_provided: Boolean - does the company provide type rating training?
- visa_sponsored: Boolean - does the ad explicitly say they provide a visa/work permit?
- job_title: The specific role title (e.g. "A320 Captain", "B737 First Officer", "Cadet Pilot").
- position_type: One of: "captain", "first_officer", "cadet", "instructor", "other"
- location: Where is the job based? (City, Country format)
- contract_type: One of: "permanent", "contract", "freelance", "seasonal"
- is_entry_level: Boolean - true if min_hours < 500 OR text mentions "entry level", "cadet", "ab initio", "low hour"
- description_summary: A 1-2 sentence summary of the key requirements.

CRITICAL PARSING RULES:
1. Watch for "Visual Stacking" - numbers and words on separate lines (e.g. "2000" on line 1, "Hours" on line 2)
2. Ignore "Preferred" or "Desired" hours - only extract "Required" or "Minimum" hours
3. Handle formats like "2000+", "1,500", "1500h", "1500 TT", "1500 total time"
4. If range given (e.g. "1500-3000 hours"), use the MINIMUM
5. Convert PIC to min_pic_hours, Total Time/TT to min_hours

Return JSON in exactly this format:
{
  "job_title": "string",
  "position_type": "string",
  "location": "string or null",
  "min_hours": number or null,
  "min_pic_hours": number or null,
  "aircraft": ["array", "of", "strings"],
  "type_rating_required": boolean,
  "type_rating_provided": boolean,
  "visa_sponsored": boolean,
  "contract_type": "string",
  "is_entry_level": boolean,
  "description_summary": "string"
}
"""


def parse_job_with_ai(raw_text: str, url: str, airline_name: str = "") -> Dict[str, Any]:
    """
    Sends raw job text to Claude 3 Haiku to extract structured data.

    Args:
        raw_text: The full text of the job posting page
        url: The URL of the job posting (for context)
        airline_name: The airline name (for context)

    Returns:
        Dict with extracted job data
    """

    # Default fallback response
    default_response = {
        "job_title": "Pilot Position",
        "position_type": "other",
        "location": None,
        "min_hours": None,
        "min_pic_hours": None,
        "aircraft": [],
        "type_rating_required": False,
        "type_rating_provided": False,
        "visa_sponsored": False,
        "contract_type": "permanent",
        "is_entry_level": False,
        "description_summary": "Unable to parse job details"
    }

    # If no API key, return default
    if not client:
        logger.debug("AI parsing disabled - no API key")
        return default_response

    # Truncate text to save costs (Haiku is cheap but let's be efficient)
    truncated_text = raw_text[:4000] if len(raw_text) > 4000 else raw_text

    user_message = f"""
Analyze this pilot job posting from {airline_name} ({url}):

---
{truncated_text}
---

Extract the structured job requirements as JSON.
"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Fast, cheap ($0.25/MTok input, $1.25/MTok output)
            max_tokens=1024,
            temperature=0,  # Deterministic output
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )

        # Get the response text
        json_str = response.content[0].text.strip()

        # Clean up common AI response artifacts
        # Sometimes AI adds ```json ... ``` wrappers
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            # Remove first and last lines (the ``` markers)
            json_str = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            json_str = json_str.replace("```", "").strip()

        # Parse JSON
        parsed = json.loads(json_str)

        # Validate and fill in missing fields
        result = {
            "job_title": parsed.get("job_title", "Pilot Position"),
            "position_type": parsed.get("position_type", "other"),
            "location": parsed.get("location"),
            "min_hours": parsed.get("min_hours"),
            "min_pic_hours": parsed.get("min_pic_hours"),
            "aircraft": parsed.get("aircraft", []),
            "type_rating_required": parsed.get("type_rating_required", False),
            "type_rating_provided": parsed.get("type_rating_provided", False),
            "visa_sponsored": parsed.get("visa_sponsored", False),
            "contract_type": parsed.get("contract_type", "permanent"),
            "is_entry_level": parsed.get("is_entry_level", False),
            "description_summary": parsed.get("description_summary", "")
        }

        logger.debug(f"AI parsed: {result['job_title']} - {result['min_hours']}hrs - {result['aircraft']}")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"AI returned invalid JSON for {url}: {e}")
        return default_response

    except Exception as e:
        logger.error(f"AI Parsing Failed for {url}: {e}")
        return default_response


def parse_jobs_batch(jobs_data: list) -> list:
    """
    Parse multiple jobs efficiently.

    Args:
        jobs_data: List of dicts with 'raw_text', 'url', 'airline_name'

    Returns:
        List of parsed job dicts
    """
    results = []

    for job in jobs_data:
        parsed = parse_job_with_ai(
            raw_text=job.get('raw_text', ''),
            url=job.get('url', ''),
            airline_name=job.get('airline_name', '')
        )
        parsed['original_url'] = job.get('url', '')
        results.append(parsed)

    return results


# Test function
if __name__ == "__main__":
    # Test with sample job text
    test_text = """
    A320 Captain - Dubai Base

    Emirates is seeking experienced A320 Captains to join our growing fleet.

    Requirements:
    - Valid ICAO ATPL
    - Minimum 5000 hours total time
    - Minimum 2500 hours PIC on A320
    - Current type rating on A320
    - Valid Class 1 Medical

    Benefits:
    - Tax-free salary
    - Accommodation provided
    - Visa sponsorship for successful candidates
    - Type rating conversion provided

    This is a permanent position based in Dubai, UAE.
    """

    if client:
        result = parse_job_with_ai(test_text, "https://example.com/job", "Emirates")
        print("AI Parser Test Result:")
        print(json.dumps(result, indent=2))
    else:
        print("ANTHROPIC_API_KEY not set - add it to .env file")

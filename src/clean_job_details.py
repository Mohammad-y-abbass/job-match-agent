import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import tempfile
from datetime import datetime

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_CHARS = 8000  # Soft truncation limit

# Compile regex patterns once for performance
KEEP_HEADERS = [
    r'requirements', r'qualifications', r'what you need', r'who you are',
    r'what we look for', r'responsibilities', r'what you will do', r'duties',
    r'skills', r'tech stack', r'technologies', r'minimum', r'preferred',
    r'about the role', r'the role', r'job summary', r'your profile', r'ideal candidate'
]
SKIP_HEADERS = [
    r'about us', r'about the company', r'benefits', r'perks', r'what we offer',
    r'compensation', r'salary', r'how to apply', r'interview process',
    r'culture', r'why join', r'legal', r'location', r'equal opportunity',
    r'who we are', r'what the company does', r'company description',
    r'about (?!the role|the job|this role|the position)',
    r'privacy', r'gdpr', r'data protection', r'background check', r'accessibility',
    r'diversity', r'inclusion', r'eeo'
]

KEEP_PATTERNS = [re.compile(p, re.I) for p in KEEP_HEADERS]
SKIP_PATTERNS = [re.compile(p, re.I) for p in SKIP_HEADERS]

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def clean_description(text: str) -> str:
    """Cleans a job description by keeping relevant sections and removing noise."""
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_blocks = []
    keep_current_block = True

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # Heuristic for headers
        is_header = len(stripped_line) < 80 and (stripped_line[0].isupper() or stripped_line.endswith(':'))

        if is_header:
            lower_line = stripped_line.lower()
            if any(p.search(lower_line) for p in SKIP_PATTERNS):
                keep_current_block = False
                continue
            if any(p.search(lower_line) for p in KEEP_PATTERNS):
                keep_current_block = True
                cleaned_blocks.append(stripped_line)
                continue

        if keep_current_block:
            # Normalize bullets
            normalized_line = re.sub(r'^\s*[\*•]\s+', '- ', stripped_line)
            cleaned_blocks.append(normalized_line)

    result_text = "\n".join(cleaned_blocks)

    # Truncate if too long
    if len(result_text) > MAX_CHARS:
        trunc_index = result_text.rfind("\n", 0, MAX_CHARS)
        if trunc_index != -1:
            result_text = result_text[:trunc_index] + "\n[...Truncated due to length...]"
        else:
            result_text = result_text[:MAX_CHARS] + "\n[...Truncated...]"

    return result_text

def process_job(url: str, details: dict) -> tuple:
    """Process a single job description and return cleaned result."""
    title = details.get("title", "")
    original_desc = details.get("description", "")
    cleaned_text = clean_description(original_desc)

    return url, {
        "title": title,
        "cleaned_text": f"{title}\n\n{cleaned_text}"
    }

def main():
    try:
        log("Starting clean_job_details.py")
        
        # Load job details
        try:
            with open(os.path.join(BASE_DIR, "static/job_details.json"), "r", encoding="utf-8") as f:
                jobs = json.load(f)
        except FileNotFoundError:
            log("Error: job_details.json not found.")
            return

        cleaned_jobs = {}

        # Use ThreadPoolExecutor for parallel processing if jobs are many
        with ThreadPoolExecutor(max_workers=8) as executor:
            for url, cleaned in executor.map(partial(process_job), jobs.keys(), jobs.values()):
                cleaned_jobs[url] = cleaned

        # Atomic write
        output_path = os.path.join(BASE_DIR, "static/jobs_for_embedding.json")
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
            json.dump(cleaned_jobs, tf, indent=2, ensure_ascii=False)
        os.replace(tf.name, output_path)

        log(f"Processed {len(cleaned_jobs)} jobs. Saved to jobs_for_embedding.json")

    except Exception as e:
        log(f"Critical error in clean_job_details: {e}")

if __name__ == "__main__":
    main()

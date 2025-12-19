import json
import re

def clean_description(text):
    """
    Cleans job description by keeping only relevant sections (requirements, responsibilities, etc.)
    and removing noise (about company, benefits, etc.).
    """
    if not text:
        return ""

    lines = text.split('\n')
    cleaned_blocks = []
    keep_current_block = True # Default to keeping the intro as it often contains role summary
    
    # Signal keywords (Keep these sections)
    keep_headers = [
        r'requirements', r'qualifications', r'what you need', r'who you are', 
        r'what we look for', r'responsibilities', r'what you will do', r'duties', 
        r'skills', r'tech stack', r'technologies', r'minimum', r'preferred', 
        r'about the role', r'the role', r'job summary', r'your profile', r'ideal candidate'
    ]
    
    # Noise keywords (Discard these sections)
    skip_headers = [
        r'about us', r'about the company', r'benefits', r'perks', r'what we offer', 
        r'compensation', r'salary', r'how to apply', r'interview process', 
        r'culture', r'why join', r'legal', r'location', r'equal opportunity',
        r'who we are', r'what the company does', r'company description',
        r'about (?!the role|the job|this role|the position)',
        r'privacy', r'gdpr', r'data protection', r'background check', r'accessibility',
        r'diversity', r'inclusion', r'eeo'
    ]

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
            
        # Check if line looks like a header (short, often no punctuation at end, capitalized)
        # Length check < 60 is a heuristic for headers
        is_header = len(stripped_line) < 60 and (stripped_line[0].isupper() or stripped_line.endswith(':'))
        
        if is_header:
            lower_line = stripped_line.lower()
            
            # Check if it triggers a skip
            if any(re.search(pattern, lower_line) for pattern in skip_headers):
                keep_current_block = False
                continue # Don't add the header itself if we are skipping
            
            # Check if it triggers a keep
            if any(re.search(pattern, lower_line) for pattern in keep_headers):
                keep_current_block = True
                cleaned_blocks.append(stripped_line)
                continue

        if keep_current_block:
            # Normalize bullets: * -> -
            normalized_line = re.sub(r'^\s*[\*•]\s+', '- ', stripped_line)
            cleaned_blocks.append(normalized_line)

    result_text = "\n".join(cleaned_blocks)
    
    # Chunking / Truncation (Soft limit)
    MAX_CHARS = 8000 # Approx 2000 tokens
    if len(result_text) > MAX_CHARS:
        # Truncate at the last newline before MAX_CHARS to avoid cutting text mid-sentence
        trunc_index = result_text.rfind('\n', 0, MAX_CHARS)
        if trunc_index != -1:
            result_text = result_text[:trunc_index] + "\n[...Truncated due to length...]"
        else:
            result_text = result_text[:MAX_CHARS] + "\n[...Truncated...]"

    return result_text

def main():
    try:
        with open('job_details.json', 'r', encoding='utf-8') as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("Error: job_details.json not found.")
        return

    cleaned_jobs = {}
    
    for url, details in jobs.items():
        original_desc = details.get('description', '')
        title = details.get('title', '')
        
        cleaned_text = clean_description(original_desc)
        
        if len(cleaned_text) < 50:
             print(f"Warning: Cleaned text for {title} is very short ({len(cleaned_text)} chars).")
        
        cleaned_jobs[url] = {
            "title": title,
            "cleaned_text": f"{title}\n\n{cleaned_text}" # Prepend title for embedding context
        }

    with open('jobs_for_embedding.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_jobs, f, indent=2, ensure_ascii=False)
        
    print(f"Processed {len(cleaned_jobs)} jobs. Saved to jobs_for_embedding.json")

if __name__ == "__main__":
    main()

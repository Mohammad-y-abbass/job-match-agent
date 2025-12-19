import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def load_resume():
    """Load resume text from resume.md"""
    try:
        with open('resume.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("Error: resume.md not found.")
        return None

def load_jobs():
    """Load jobs from jobs_for_embedding.json"""
    try:
        with open('jobs_for_embedding.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Error: jobs_for_embedding.json not found or invalid.")
        return {}

from datetime import datetime

def match_jobs(threshold=0.5, top_n=100):
    """
    Match resume against job descriptions using sentence embeddings.
    
    Args:
        threshold: Minimum similarity score (0-1) to be considered a match
        top_n: Maximum number of matches to return
    
    Returns:
        List of matching jobs with scores and history
    """
    print(f"Loading sentence-transformers model (Threshold: {threshold})...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    resume = load_resume()
    if not resume:
        return []
    
    jobs = load_jobs()
    if not jobs:
        return []
    
    # Load existing matches to preserve history
    existing_matches = {}
    try:
        with open('matching_jobs.json', 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            existing_matches = {m['url']: m for m in old_data}
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    print(f"Loaded {len(jobs)} jobs for matching.")
    
    # Create resume embedding
    print("Creating resume embedding...")
    resume_embedding = model.encode([resume])[0]
    
    # Create job embeddings and calculate similarity
    print("Calculating similarity scores...")
    matches = []
    
    all_urls = list(jobs.keys())
    job_urls = []
    job_texts = []
    job_titles = []

    # Filter out Senior roles
    print("Filtering out Senior roles...")
    for url in all_urls:
        title = jobs[url].get('title', 'Untitled')
        if 'senior' in title.lower():
            continue
        
        job_urls.append(url)
        job_texts.append(jobs[url].get('cleaned_text', ''))
        job_titles.append(title)
        
    print(f"Processing {len(job_urls)} jobs after filtering (from {len(all_urls)} total).")
    
    # Batch encode for efficiency
    job_embeddings = model.encode(job_texts, show_progress_bar=True)
    
    # Calculate cosine similarity
    similarities = cosine_similarity([resume_embedding], job_embeddings)[0]
    
    now = datetime.now().isoformat()
    
    # Create matches with scores
    for i, (url, title, score) in enumerate(zip(job_urls, job_titles, similarities)):
        if score >= threshold:
            # Check if it was already matched
            is_new = url not in existing_matches
            matched_at = existing_matches[url].get('matched_at', now) if not is_new else now
            status = existing_matches[url].get('status', 'matched') if not is_new else 'matched'
            
            matches.append({
                "url": url,
                "title": title,
                "score": float(score),
                "description": job_texts[i],
                "matched_at": matched_at,
                "is_new": is_new,
                "status": status
            })
    
    # Sort by score descending
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    # Limit to top_n
    matches = matches[:top_n]
    
    print(f"Found {len(matches)} matching jobs above threshold {threshold}")
    
    # Save to file
    with open('matching_jobs.json', 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    print(f"Saved matching jobs to matching_jobs.json")
    
    return matches

if __name__ == "__main__":
    matches = match_jobs()
    print(f"\nTop 10 Matches:")
    for i, match in enumerate(matches[:10], 1):
        print(f"{i}. [{match['score']:.3f}] {match['title']}")

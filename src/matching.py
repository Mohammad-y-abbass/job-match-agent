import json
import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global model cache
_model_cache = None

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def get_model():
    """Load the SentenceTransformer model once and cache it."""
    global _model_cache
    if _model_cache is None:
        log("Loading sentence-transformers model...")
        _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
    return _model_cache

def load_resume():
    """Load resume text from resume.md"""
    try:
        with open(os.path.join(BASE_DIR, 'static/resume.md'), 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        log("Error: resume.md not found.")
        return None

def load_jobs():
    """Load jobs from jobs_for_embedding.json"""
    try:
        with open(os.path.join(BASE_DIR, 'static/jobs_for_embedding.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log("Error: jobs_for_embedding.json not found or invalid.")
        return {}

def is_senior_role(title):
    """Check if a job title indicates a senior/lead role."""
    if not title:
        return False
    senior_keywords = [
        "senior", "lead", "principal", "head", "manager", "director",
        "vp", "vice president", "chief", "architect"
    ]
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in senior_keywords)

def match_jobs(threshold=0.5, top_n=100):
    try:
        log("Starting matching.py")
        model = get_model()
        
        resume = load_resume()
        if not resume:
            return []
        
        jobs = load_jobs()
        if not jobs:
            return []
        
        # Load existing matches to preserve history
        existing_matches = {}
        try:
            with open(os.path.join(BASE_DIR, 'static/matching_jobs.json'), 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                existing_matches = {m['url']: m for m in old_data}
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        log(f"Loaded {len(jobs)} jobs for matching.")
        
        # Create resume embedding
        log("Creating resume embedding...")
        resume_embedding = model.encode([resume])[0]
        
        # Prepare job data excluding senior roles
        job_urls, job_texts, job_titles = [], [], []
        for url, job in jobs.items():
            title = job.get('title', 'Untitled')
            # if is_senior_role(title):
            #     continue
            job_urls.append(url)
            job_texts.append(job.get('cleaned_text', ''))
            job_titles.append(title)
        
        log(f"Processing {len(job_urls)} jobs.")
        
        # Batch encode job descriptions
        job_embeddings = model.encode(job_texts, show_progress_bar=True)
        
        # Calculate cosine similarity
        similarities = cosine_similarity([resume_embedding], job_embeddings)[0]
        
        now = datetime.now().isoformat()
        matches = []

        # Create matches with scores
        for i, (url, title, score) in enumerate(zip(job_urls, job_titles, similarities)):
            if score >= threshold:
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
        
        log(f"Found {len(matches)} matching jobs above threshold {threshold}")
        
        # Save results
        with open(os.path.join(BASE_DIR, 'static/matching_jobs.json'), 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=2, ensure_ascii=False)
        
        log(f"Saved matching jobs to matching_jobs.json")
        return matches

    except Exception as e:
        log(f"Critical error in matching.py: {e}")
        return []

if __name__ == "__main__":
    matches = match_jobs()
    print("\nTop 10 Matches:")
    for i, match in enumerate(matches[:10], 1):
        print(f"{i}. [{match['score']:.3f}] {match['title']}")

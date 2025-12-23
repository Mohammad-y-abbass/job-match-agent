from flask import Flask, render_template, jsonify, request
import json
import subprocess
import threading
import os
import sys
from collections import deque

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Status tracking for scraping operations
scrape_status = {
    "running": False,
    "current_step": "",
    "message": "",
    "logs": deque(maxlen=1000)
}

def add_log(message):
    """Add a message to the logs"""
    print(message)
    scrape_status["logs"].append(message)

def load_jobs():
    """Load jobs from jobs.json"""
    try:
        with open(os.path.join(BASE_DIR, 'static/jobs.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_job_details():
    """Load job details from job_details.json"""
    try:
        with open(os.path.join(BASE_DIR, 'static/job_details.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_matching_jobs():
    """Load matching jobs from matching_jobs.json"""
    try:
        with open(os.path.join(BASE_DIR, 'static/matching_jobs.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_stats():
    """Get scraping statistics"""
    jobs = load_jobs()
    details = load_job_details()
    
    sites = {}
    for job in jobs:
        site = job.get('site', 'unknown')
        sites[site] = sites.get(site, 0) + 1
    
    seen_count = sum(1 for d in details.values() if d.get('seen', False))
    
    return {
        "total_urls": len(jobs),
        "total_details": len(details),
        "seen_count": seen_count,
        "sites": sites
    }

@app.route('/')
def index():
    """Serve the main UI page"""
    return render_template('index.html')

@app.route('/api/jobs')
def api_jobs():
    """Get all jobs with their details (paginated, new jobs first)"""
    jobs = load_jobs()
    details = load_job_details()
    
    # Pagination params
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').lower()
    site_filter = request.args.get('site', '')
    
    # Merge job URLs with their details
    result = []
    for job in jobs:
        url = job.get('url')
        job_data = {
            "site": job.get('site'),
            "url": url,
            "title": details.get(url, {}).get('title', 'Not scraped yet'),
            "description": details.get(url, {}).get('description', ''),
            "seen": details.get(url, {}).get('seen', False),
            "last_seen": details.get(url, {}).get('last_seen', None),
            "has_details": url in details
        }
        result.append(job_data)
    
    # Sort: new jobs first (not seen), then seen jobs
    # Within each group, maintain original order (most recent additions at end)
    result = sorted(result, key=lambda x: (x['seen'], 0), reverse=False)
    # Reverse to show newest first (latest added jobs appear at top)
    new_jobs = [j for j in result if not j['seen']]
    seen_jobs = [j for j in result if j['seen']]
    # Reverse to show most recently added first
    new_jobs.reverse()
    seen_jobs.reverse()
    result = new_jobs + seen_jobs
    
    # Filter by search term
    if search:
        result = [j for j in result if 
                  search in j['title'].lower() or 
                  search in j['site'].lower() or 
                  search in j['url'].lower()]
    
    # Filter by site
    if site_filter:
        result = [j for j in result if j['site'] == site_filter]
    
    # Pagination
    total = len(result)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated = result[start:end]
    
    return jsonify({
        "jobs": paginated,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }
    })

@app.route('/api/stats')
def api_stats():
    """Get scraping statistics"""
    return jsonify(get_stats())

def run_script(script_name, step_name):
    """Run a python script and capture its output to logs"""
    add_log(f"\n>>> Starting step: {step_name} ({script_name})")
    scrape_status["current_step"] = step_name
    
    # Force the subprocess to use the venv's site-packages
    env = os.environ.copy()
    venv_base = os.path.dirname(os.path.dirname(sys.executable))
    site_packages = os.path.join(venv_base, 'Lib', 'site-packages')
    
    if os.path.exists(site_packages):
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = site_packages + os.pathsep + env['PYTHONPATH']
        else:
            env['PYTHONPATH'] = site_packages

    process = subprocess.Popen(
        [sys.executable, '-u', script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )
    
    for line in process.stdout:
        add_log(line.strip())
    
    process.wait()
    if process.returncode == 0:
        add_log(f">>> {step_name} completed successfully.")
        return True
    else:
        add_log(f">>> {step_name} failed with return code {process.returncode}.")
        return False

@app.route('/api/scrape/full', methods=['POST'])
def api_scrape_full():
    """Trigger the full scraping and matching process"""
    if scrape_status["running"]:
        return jsonify({"success": False, "message": "Scrape already in progress"})
    
    def full_process():
        scrape_status["running"] = True
        scrape_status["logs"].clear()
        scrape_status["message"] = "Starting full process..."
        
        steps = [
            ('scrape_urls.py', 'Scraping URLs'),
            ('scrape_details.py', 'Scraping Details'),
            ('matching.py', 'Running Matching')
        ]
        
        success = True
        for script, step in steps:
            if not run_script(script, step):
                success = False
                scrape_status["message"] = f"Failed at: {step}"
                break
        
        if success:
            scrape_status["message"] = "Full process completed successfully!"
            scrape_status["current_step"] = "Completed"
        
        scrape_status["running"] = False

    thread = threading.Thread(target=full_process)
    thread.start()
    
    return jsonify({"success": True, "message": "Full scraping process started"})

@app.route('/api/scrape/status')
def api_scrape_status():
    """Get current scraping status and logs"""
    # Convert deque to list for JSON serialization
    status_copy = scrape_status.copy()
    status_copy["logs"] = list(scrape_status["logs"])
    return jsonify(status_copy)

@app.route('/api/matching/jobs')
def api_matching_jobs():
    """Get matching jobs list"""
    matches = load_matching_jobs()
    return jsonify(matches)

@app.route('/api/jobs/view', methods=['POST'])
def api_job_viewed():
    """Mark a job as viewed"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"success": False, "message": "No URL provided"}), 400
        
    try:
        matches = load_matching_jobs()
        updated = False
        
        for job in matches:
            if job['url'] == url:
                job['status'] = 'viewed'
                # Also mark as not new if viewed
                job['is_new'] = False 
                updated = True
                break
        
        if updated:
            with open(os.path.join(BASE_DIR, 'static/matching_jobs.json'), 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Job not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_details():
    # Load configuration
    try:
        with open('job-details-scraping-map.json', 'r') as f:
            scraping_map = json.load(f)
    except FileNotFoundError:
        print("Error: job-details-scraping-map.json not found.")
        return

    # Load jobs
    try:
        with open('jobs.json', 'r') as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("Error: jobs.json not found.")
        return

    # Load existing details to resume if stopped
    job_details = {}
    try:
        with open('job_details.json', 'r') as f:
            job_details = json.load(f)
            print(f"Loaded {len(job_details)} existing job details.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("No existing job matching file found. Starting fresh.")

    # Name mapping to handle discrepancies (e.g. "remote ok" vs "remoteOk")
    # Keys are names in jobs.json, Values are keys in job-details-scraping-map.json
    site_name_map = {
        "remote ok": "remoteOk",
        "workable": "workable",
        "meetfrank": "meetfrank",
        "remocate": "remocate",
        "naukrigulf": "naukrigulf",
        "bayt": "bayt",
        "hire lebanese": "hire lebanese",
        "dice": "dice",
        "WWR": "WWR"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.new_page()

        for i, job in enumerate(jobs):
            url = job.get('url')
            site_name = job.get('site')
            
            if not url or not site_name:
                continue
                
            # Check if already scraped
            if url in job_details:
                # Mark as seen without re-scraping
                job_details[url]["seen"] = True
                job_details[url]["last_seen"] = datetime.now().isoformat()
                # Save incrementally
                with open('job_details.json', 'w') as f:
                    json.dump(job_details, f, indent=2)
                print(f"Marked as seen: {url}")
                continue

            # Get config key
            config_key = site_name_map.get(site_name, site_name)
            if config_key not in scraping_map:
                print(f"Skipping {site_name}: No scraping config found.")
                continue
            
            selectors = scraping_map[config_key]
            
            print(f"Scraping details for {url} ({site_name})...")
            
            try:
                page.goto(url, timeout=60000)
                # Small wait to ensure basic render
                time.sleep(2)

                # Special handling for MeetFrank
                if config_key == 'meetfrank':
                    try:
                        # Try to click "Read more" if it exists to expand description
                        # Using a generic selector for "Read more" buttons often found on such sites
                        read_more_btn = page.locator('text="Read more"').first
                        if read_more_btn.is_visible(timeout=3000):
                            read_more_btn.click()
                            print("Clicked 'Read more'")
                            time.sleep(1)
                    except Exception as e:
                        print(f"MeetFrank 'Read more' action failed or not needed: {e}")

                # Extract Data
                title = ""
                description = ""

                try:
                    if page.locator(selectors['title']).count() > 0:
                        title = page.locator(selectors['title']).first.inner_text().strip()
                except Exception as e:
                    print(f"Error extracting title: {e}")

                try:
                    if page.locator(selectors['description']).count() > 0:
                        # Get inner HTML to preserve formatting, or text if preferred. 
                        # Use inner_text for clean text, inner_html for HTML.
                        # User asked for "descriotion" (description), usually implies text content but HTML is detailed.
                        # Let's use inner_text for now as it's cleaner for simple storage, 
                        # but often descriptions need HTML. I'll use inner_text to be safe on JSON size 
                        # and readability unless HTML is strictly required. 
                        # Actually for job descriptions HTML is better to keep structure.
                        # Let's grab inner_text for simplicity unless requested otherwise, 
                        # or inner_html if the user wants rich text. 
                        # Given the prompt simply said "descriotion", I will default to inner_text 
                        # but keep newlines.
                        description = page.locator(selectors['description']).first.inner_text().strip()
                except Exception as e:
                    print(f"Error extracting description: {e}")

                # Store result
                job_details[url] = {
                    "title": title,
                    "description": description
                }

                # Save incrementally
                with open('job_details.json', 'w') as f:
                    json.dump(job_details, f, indent=2)
                
                print(f"Saved details for {title}")

            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
                # Optional: Add a failed entry or just skip to retry later

        browser.close()
    
    print(f"Completed scraping details. Total: {len(job_details)}")

if __name__ == "__main__":
    scrape_details()

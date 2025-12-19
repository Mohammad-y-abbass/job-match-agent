import json
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urljoin

def scrape_sites():
    with open('sites.json', 'r') as f:
        sites = json.load(f)

    all_jobs = []
    seen_urls = set()
    try:
        with open('jobs.json', 'r') as f:
            all_jobs = json.load(f)
            seen_urls = {job['url'] for job in all_jobs}
            print(f"Loaded {len(all_jobs)} existing jobs.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("No existing jobs.json found or file is empty. Starting fresh.")

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


        for site in sites:
            print(f"Scraping {site['name']}...")
            try:
                page.goto(site['url'], timeout=180000)
                time.sleep(3)
                
                # Wait for at least one item to appear
                # Construct a combined selector to wait for items inside the container
                # This handles cases where the container exists but is empty initially
                item_selector = f"{site['list_selector']} {site['list_item_selector']}"
                print(f"Waiting for selector: {item_selector}")
                page.wait_for_selector(item_selector, timeout=30000)

                # Get list container first
                list_container = page.locator(site['list_selector'])
                # Get all list items within the container
                list_items = list_container.locator(site['list_item_selector']).all()
                print(f"Found {len(list_items)} items.")

                for i, item in enumerate(list_items):
                    try:
                        # Use a short timeout for item fields to avoid hanging
                        link_el = item.locator(site['item_url']).first
                        
                        if link_el.count() == 0:
                            # Skip items without links (could be empty or different structure)
                            print(f"Debug: No link found for item {i} in {site['name']}")

                            continue

                        url = link_el.get_attribute('href', timeout=1000)
                        # Handle relative URLs by joining with current page URL
                        # urljoin correctly handles base URLs with query parameters
                        if not url.startswith(('http:', 'https:')):
                            url = urljoin(page.url, url)

                        if url in seen_urls:
                            print(f"Duplicate found, skipping: {url}")
                            continue
                        
                        job_data = {
                            "site": site["name"],
                            "url": url
                        }
                        all_jobs.append(job_data)
                        seen_urls.add(url)
                        
                        # Save immediately to ensure data is persisted incrementally
                        # We rewrite the file to maintain valid JSON array structure
                        with open('jobs.json', 'w') as f:
                            json.dump(all_jobs, f, indent=2)
                        
                        print(f"New Job: {url}")
                    except Exception as e:
                        print(f"Error extracting item {i}: {e}")

            except Exception as e:
                print(f"Failed to scrape {site['name']}: {e}")
        
        browser.close()
    
    print(f"Total jobs in database: {len(all_jobs)}")

if __name__ == "__main__":
    scrape_sites()

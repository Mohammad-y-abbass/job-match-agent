import json
import os
import asyncio
from datetime import datetime
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

async def scrape_site_urls(context, site_config, existing_urls, lock, new_jobs_list):
    site_name = site_config.get("name")
    url = site_config.get("url")
    list_selector = site_config.get("list_selector")
    list_item_selector = site_config.get("list_item_selector")
    item_url_selector = site_config.get("item_url")

    log(f"Scraping {site_name}...")
    
    try:
        page = await context.new_page()
        await page.goto(url, timeout=60000)
        
        # Wait for the list container
        try:
            await page.wait_for_selector(list_selector, timeout=10000)
        except:
            log(f"Time out waiting for list selector on {site_name}")
            await page.close()
            return

        container = page.locator(list_selector).first
        
        items = container.locator(list_item_selector)
        count = await items.count()
        log(f"Found {count} potential jobs on {site_name}")

        local_new_count = 0
        
        for i in range(count):
            try:
                item = items.nth(i)
                link_element = item.locator(item_url_selector).first
                
                href = await link_element.get_attribute("href")
                if not href:
                    continue
                
                full_url = urljoin(url, href)
                
                async with lock:
                    if full_url not in existing_urls:
                        job_entry = {
                            "site": site_name,
                            "url": full_url,
                            "found_at": datetime.now().isoformat()
                        }
                        new_jobs_list.append(job_entry)
                        existing_urls.add(full_url)
                        local_new_count += 1
                        log(f"Found new job: {full_url}")
            except Exception as e:
                continue

        log(f"Finished {site_name}. New jobs: {local_new_count}")
        await page.close()

    except Exception as e:
        log(f"Failed to scrape {site_name}: {e}")


async def scrape_urls():
    try:
        log("Starting scrape_urls.py")
        
        # Load sites config
        try:
            with open(os.path.join(BASE_DIR, "static/sites.json"), "r") as f:
                sites_config = json.load(f)
        except FileNotFoundError:
            log("Error: sites.json not found.")
            return

        # Load existing jobs to avoid duplicates
        existing_urls = set()
        try:
            with open(os.path.join(BASE_DIR, "static/jobs.json"), "r") as f:
                existing_jobs = json.load(f)
                for job in existing_jobs:
                    if "url" in job:
                        existing_urls.add(job["url"])
            log(f"Loaded {len(existing_urls)} existing jobs.")
        except (FileNotFoundError, json.JSONDecodeError):
            existing_jobs = []
            log("No existing jobs found. Starting fresh.")

        new_jobs_list = []
        lock = asyncio.Lock()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                 ignore_https_errors=True
            )
            
            await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

            tasks = []
            for site in sites_config:
                tasks.append(scrape_site_urls(context, site, existing_urls, lock, new_jobs_list))
            
            await asyncio.gather(*tasks)
            
            await context.close()
            await browser.close()
            
        if new_jobs_list:
            log(f"Total new jobs found: {len(new_jobs_list)}")
            existing_jobs.extend(new_jobs_list)
            
            with open(os.path.join(BASE_DIR, "static/jobs.json"), "w") as f:
                json.dump(existing_jobs, f, indent=4)
            log("Updated jobs.json")
        else:
            log("No new jobs found.")
            
    except Exception as e:
        log(f"Critical error in scrape_urls: {e}")

if __name__ == "__main__":
    asyncio.run(scrape_urls())

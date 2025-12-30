import json
import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Name mapping
SITE_NAME_MAP = {
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

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

async def scrape_single_job(context, job, scraping_map, job_details, lock, sem):
    async with sem:
        url = job.get('url')
        site_name = job.get('site')
        
        if not url or not site_name:
            return

        config_key = SITE_NAME_MAP.get(site_name, site_name)
        if config_key not in scraping_map:
            # log(f"Skipping {site_name}: No scraping config found.")
            return

        selectors = scraping_map[config_key]
        
        # log(f"Scraping details for {url} ({site_name})...")
        
        page = None
        try:
            page = await context.new_page()
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(2000)

                # Special handling for MeetFrank
                if config_key == 'meetfrank':
                    try:
                        read_more_btn = page.locator('text="Read more"').first
                        if await read_more_btn.is_visible(timeout=3000):
                            await read_more_btn.click()
                            await page.wait_for_timeout(1000)
                    except Exception:
                        pass

                # Extract Data
                title = ""
                description = ""

                try:
                    if await page.locator(selectors['title']).count() > 0:
                        title = (await page.locator(selectors['title']).first.inner_text()).strip()
                except Exception:
                    pass

                try:
                    if await page.locator(selectors['description']).count() > 0:
                        description = (await page.locator(selectors['description']).first.inner_text()).strip()
                except Exception:
                    pass

                if title or description:
                    async with lock:
                        job_details[url] = {
                            "title": title,
                            "description": description,
                            "scraped_at": datetime.now().isoformat(),
                            "seen": True,
                            "last_seen": datetime.now().isoformat()
                        }
                    log(f"Scraped: {title[:50]}..." if title else f"Scraped: {url}")
                else:
                    log(f"Empty result for {url}")

            except Exception as e:
                log(f"Failed to scrape {url}: {e}")
            finally:
                if page:
                    await page.close()

        except Exception as e:
             log(f"Error creating page for {url}: {e}")

async def scrape_details():
    try:
        log("Starting scrape_details.py")
        
        # Load configuration
        try:
            with open(os.path.join(BASE_DIR, 'static/job-details-scraping-map.json'), 'r') as f:
                scraping_map = json.load(f)
        except FileNotFoundError:
            log("Error: job-details-scraping-map.json not found.")
            return

        # Load jobs
        try:
            with open(os.path.join(BASE_DIR, 'static/jobs.json'), 'r') as f:
                jobs = json.load(f)
        except FileNotFoundError:
            log("Error: jobs.json not found.")
            return

        # Load existing details
        job_details = {}
        try:
            with open(os.path.join(BASE_DIR, 'static/job_details.json'), 'r') as f:
                job_details = json.load(f)
                log(f"Loaded {len(job_details)} existing job details.")
        except (FileNotFoundError, json.JSONDecodeError):
            log("No existing job details found. Starting fresh.")

        # Identify tasks
        jobs_to_scrape = []
        for job in jobs:
            url = job.get('url')
            if url in job_details:
                 # Update last_seen in memory
                 job_details[url]["seen"] = True
                 job_details[url]["last_seen"] = datetime.now().isoformat()
            else:
                 jobs_to_scrape.append(job)

        log(f"Found {len(jobs_to_scrape)} jobs to scrape.")

        if jobs_to_scrape:
            lock = asyncio.Lock()
            sem = asyncio.Semaphore(10) # 10 concurrent tabs

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    ignore_https_errors=True
                )
                
                await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

                tasks = [scrape_single_job(context, job, scraping_map, job_details, lock, sem) for job in jobs_to_scrape]
                await asyncio.gather(*tasks)

                await context.close()
                await browser.close()
        
        # Save all results at the end
        log("Saving results...")
        with open(os.path.join(BASE_DIR, 'static/job_details.json'), 'w') as f:
            json.dump(job_details, f, indent=2)
        
        log(f"Completed scrape_details.py. Total details: {len(job_details)}")
        
    except Exception as e:
        log(f"Critical error in scrape_details: {e}")

if __name__ == "__main__":
    asyncio.run(scrape_details())

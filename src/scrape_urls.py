import json
import os
import asyncio
from datetime import datetime
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def scrape_job(context, job, scraping_map, site_name_map, job_details, lock):
    url = job.get("url")
    site_name = job.get("site")
    
    if not url or not site_name:
        return

    # Skip if already scraped
    async with lock:
        if url in job_details:
            job_details[url]["seen"] = True
            job_details[url]["last_seen"] = datetime.now().isoformat()
            return

    config_key = site_name_map.get(site_name, site_name)
    if config_key not in scraping_map:
        print(f"Skipping {site_name}: No scraping config found.")
        return

    selectors = scraping_map[config_key]

    try:
        page = await context.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")

        # Special handling for MeetFrank "Read more"
        if config_key == "meetfrank":
            try:
                read_more_btn = page.locator('text="Read more"').first
                if await read_more_btn.is_visible(timeout=3000):
                    await read_more_btn.click()
                    await page.wait_for_timeout(1000)
                    print("Clicked 'Read more'")
            except Exception:
                pass  # not present, skip

        # Extract title
        title = ""
        try:
            if await page.locator(selectors["title"]).count() > 0:
                title = (await page.locator(selectors["title"]).first.inner_text()).strip()
        except Exception as e:
            print(f"Error extracting title for {url}: {e}")

        # Extract description
        description = ""
        try:
            if await page.locator(selectors["description"]).count() > 0:
                description = (await page.locator(selectors["description"]).first.inner_text()).strip()
        except Exception as e:
            print(f"Error extracting description for {url}: {e}")

        async with lock:
            job_details[url] = {
                "title": title,
                "description": description,
                "site": site_name,
                "scraped_at": datetime.now().isoformat()
            }

        print(f"Saved details for {title} ({url})")
        await page.close()

    except Exception as e:
        print(f"Failed to scrape {url}: {e}")

async def scrape_details():
    # Load scraping map
    try:
        with open(os.path.join(BASE_DIR, "static/job-details-scraping-map.json"), "r") as f:
            scraping_map = json.load(f)
    except FileNotFoundError:
        print("Error: job-details-scraping-map.json not found.")
        return

    # Load jobs
    try:
        with open(os.path.join(BASE_DIR, "static/jobs.json"), "r") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("Error: jobs.json not found.")
        return

    # Load existing job details
    job_details = {}
    try:
        with open(os.path.join(BASE_DIR, "static/job_details.json"), "r") as f:
            job_details = json.load(f)
            print(f"Loaded {len(job_details)} existing job details.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("No existing job details found. Starting fresh.")

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

    lock = asyncio.Lock()
    sem = asyncio.Semaphore(10)  # Limit concurrency to 10

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ignore_https_errors=True
        )

        # Optional: block images/fonts to speed up page loads
        await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

        # Create tasks for all jobs
        async def bounded_scrape(job):
            async with sem:
                await scrape_job(context, job, scraping_map, site_name_map, job_details, lock)

        tasks = [bounded_scrape(job) for job in jobs]
        await asyncio.gather(*tasks)

        await context.close()
        await browser.close()

    # Save all results at the end
    with open(os.path.join(BASE_DIR, "static/job_details.json"), "w") as f:
        json.dump(job_details, f, indent=2)

    print(f"Completed scraping details. Total: {len(job_details)}")

if __name__ == "__main__":
    asyncio.run(scrape_details())

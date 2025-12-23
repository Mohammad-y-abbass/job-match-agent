import json
import asyncio
import os
from playwright.async_api import async_playwright
from urllib.parse import urljoin

# Base directory for resolving file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def scrape_site(browser, site, all_jobs, seen_urls, lock):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        ignore_https_errors=True
    )
    page = await context.new_page()

    try:
        print(f"Scraping {site['name']}...")
        await page.goto(site['url'], timeout=180000)
        await page.wait_for_load_state("domcontentloaded")

        item_selector = f"{site['list_selector']} {site['list_item_selector']}"
        await page.wait_for_selector(item_selector, timeout=30000)

        items = page.locator(item_selector)
        count = await items.count()

        print(f"Found {count} items on {site['name']}")

        for i in range(count):
            item = items.nth(i)
            link = item.locator(site['item_url']).first

            if await link.count() == 0:
                continue

            url = await link.get_attribute("href")
            if not url:
                continue

            if not url.startswith("http"):
                url = urljoin(page.url, url)

            async with lock:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_jobs.append({
                    "site": site["name"],
                    "url": url
                })

                print(f"New Job: {url}")

    except Exception as e:
        print(f"{site['name']} failed: {e}")
    finally:
        await context.close()

async def scrape_sites():
    with open(os.path.join(BASE_DIR, "static/sites.json")) as f:
        sites = json.load(f)

    all_jobs = []
    seen_urls = set()

    try:
        with open(os.path.join(BASE_DIR, "static/jobs.json")) as f:
            all_jobs = json.load(f)
            seen_urls = {job["url"] for job in all_jobs}
            print(f"Loaded {len(all_jobs)} existing jobs.")
    except:
        print("Starting fresh.")

    lock = asyncio.Lock()
    sem = asyncio.Semaphore(10)  # LIMIT concurrency (important)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        async def bounded_scrape(site):
            async with sem:
                await scrape_site(browser, site, all_jobs, seen_urls, lock)

        tasks = [bounded_scrape(site) for site in sites]
        await asyncio.gather(*tasks)

        await browser.close()
        with open(os.path.join(BASE_DIR, "static/jobs.json"), "w") as f:
            json.dump(all_jobs, f, indent=2)

    print(f"Total jobs in database: {len(all_jobs)}")

if __name__ == "__main__":
    asyncio.run(scrape_sites())


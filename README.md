# Job Agent Scraper & Matcher

A comprehensive tool to scrape job listings, extract details, clean descriptions, and match them against your resume using AI (Semantic Search).

## Features

-   **Multi-Site Scraping**: Configurable scraping for various job boards using Playwright.
-   **Intelligent Matching**: Uses `sentence-transformers` and Cosine Similarity to semantic match your resume with job descriptions.
-   **Smart Cleaning**: Automatically parses and cleans job descriptions to remove noise before matching.
-   **Web Dashboard**: A Flask-based UI to view, filter, and manage matched jobs.
-   **Status Tracking**: Track which jobs are new, matched, or already viewed.

## Prerequisites

-   Python 3.8 or higher
-   Node.js (optional, for some Playwright dependencies)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Mohammad-y-abbass/job-match-agent.git
    cd job-match-agent
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    python -m playwright install chromium
    ```

## Configuration

### 1. Resume
Create or update `resume.md` in the root directory. Paste your full resume text there. This is used as the anchor for finding matching jobs.

### 2. Job Sites & Custom Selectors
Configure existing sites or add new ones by updating `sites.json` and `job-details-scraping-map.json`.

**Step A: Define the site in `sites.json`**
```json
 {
   "name": "my-custom-site",
   "url": "https://example.com/jobs",
   "list_selector": ".job-list",
   "list_item_selector": ".job-card",
   "item_url": "a.title-link"
 }
```

**Step B: Add detail selectors in `job-details-scraping-map.json`**
Ensure the key matches the `name` used in `sites.json`.
```json
"my-custom-site": {
  "title": "h1.role-title",
  "description": "div.job-body"
}
```

## Running the Application

### Web Dashboard (Recommended)
The easiest way to use the tool is via the web interface.

1.  Start the server:
    ```bash
    python app.py
    ```
2.  Open [http://localhost:5001](http://localhost:5001) in your browser.
3.  Click **"Scrape & Match"** to fetch new jobs and update matches.
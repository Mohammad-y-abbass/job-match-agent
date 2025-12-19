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

### For Users (Usage Only)
If you simply want to use the application without modifying the core code or contributing back:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Mohammad-y-abbass/job-match-agent.git
    cd job-match-agent
    ```
    *This creates a local copy on your machine that you can run immediately.*

### For Contributors (Development)
If you want to modify the code, add features, and submit changes (Pull Requests):

1.  **Fork the repository**:
    *   Click the **Fork** button in the top-right corner of this GitHub page.
    *   This creates a copy of the repository under your own GitHub account.

2.  **Clone your Fork**:
    ```bash
    git clone https://github.com/YOUR-USERNAME/job-match-agent.git
    cd job-match-agent
    ```

### Setup Steps (For both Users and Contributors)

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
    ```

4.  **Install Playwright browsers**:
    ```bash
    python -m playwright install chromium
    ```

## Configuration

### 1. Resume
Create or update `resume.md` in the root directory. Paste your full resume text there. This is used as the anchor for finding matching jobs.

### 2. Job Sites
Update `sites.json` to configure which job boards to scrape.
```json
[
  {
    "name": "remote ok",
    "url": "https://remoteok.com/remote-jobs",
    "list_selector": "table#jobsboard",
    "list_item_selector": "tr.job",
    "item_url": "a.preventLink"
  }
]
```

### 3. Detail Scraping Map
Update `job-details-scraping-map.json` to define CSS selectors for extracting titles and descriptions from individual job pages for each site.

### 4. Adding Custom Sites
You can add your own job boards to the scraper!

1.  **Add the site to `sites.json`**:
    Define the URL and the CSS selectors to find the list of jobs and the link to each job.
    ```json
    {
      "name": "my-custom-site",
      "url": "https://example.com/jobs",
      "list_selector": ".job-list",
      "list_item_selector": ".job-card",
      "item_url": "a.title-link"
    }
    ```

2.  **Add detail selectors to `job-details-scraping-map.json`**:
    **Crucial Step:** You MUST add valid selectors for the Job Title and Description so the detailed scraper knows what to grab. The key must match the `name` you used in `sites.json`.
    ```json
    "my-custom-site": {
      "title": "h1.role-title",
      "description": "div.job-body"
    }
    ```

## Quick Start

1.  **Install dependencies**: `pip install -r requirements.txt`
2.  **Install browsers**: `python -m playwright install chromium`
3.  **Run the App**: `python app.py`
4.  **Open Browser**: Go to [http://localhost:5001](http://localhost:5001)

## Running the Application

### Web Dashboard
The easiest way to use the tool is via the web interface.

1.  Start the server:
    ```bash
    python app.py
    ```
2.  Open `http://localhost:5001` in your browser.
3.  Click **"Scrape & Match"** to fetch new jobs and update matches.
4.  **View Matches**: Click "View" on any job to see details. This marks the job as "Viewed" so you can track your progress.

### Manual Data Pipeline
For advanced usage or debugging, you can run each step of the pipeline manually:

1.  **Scrape Job URLs**:
    ```bash
    python main.py
    ```
2.  **Scrape Job Details**:
    ```bash
    python scrape_details.py
    ```
3.  **Clean Descriptions**:
    ```bash
    python clean_job_details.py
    ```
4.  **Match Jobs**:
    ```bash
    python matching.py
    ```

## Project Structure

-   `app.py`: Flask web application backend.
-   `main.py`: Main scraper for fetching job URLs from lists.
-   `scrape_details.py`: Fetcher for individual job page content.
-   `clean_job_details.py`: Pre-processor to clean text for embedding.
-   `matching.py`: AI matching logic using Sentence Transformers.
-   `resume.md`: Your input resume.
-   `static/` & `templates/`: Frontend files for the web dashboard.
-   `*.json`: Data files for storage and configuration.


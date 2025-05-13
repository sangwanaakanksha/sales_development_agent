from dotenv import load_dotenv
load_dotenv()

# utils/search.py

import os
import time
import re

# First-party SERP client
try:
    from serpapi import GoogleSearch
except ImportError:
    from google_search_results import GoogleSearch

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from utils.database import save_stage

# Your SerpAPI key
SERP_KEY = os.getenv("SERPAPI_API_KEY")

# Map event keywords → exhibitor-gallery URLs
EVENT_LINKS = {
    "ISA2025": (
        "https://isasignexpo2025.mapyourshow.com/8_0/explore/"
        "exhibitor-gallery.cfm?featured=false&categories=1%7C47"
    ),
    # add more events here as needed
}

def crawl_event_exhibitors(event_url: str, max_exhibitors: int = 50):
    """
    Headless Chrome + Selenium to scrape exhibitor names + URLs
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(event_url)
    time.sleep(3)  # wait for JS to render

    # Grab all links that lead to exhibitor-details pages
    elems = driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'exhibitor-details.cfm?exhid=')]"
    )

    seen = set()
    exhibitors = []
    for el in elems:
        url = el.get_attribute("href")
        name = el.text.strip()
        if not url or not name:
            continue
        if url in seen:
            continue
        seen.add(url)
        exhibitors.append({"name": name, "url": url})
        if len(exhibitors) >= max_exhibitors:
            break

    driver.quit()
    return exhibitors

def enrich_basic_info(leads: list):
    """
    For each lead, add company_website and a LinkedIn search for decision-makers
    """
    enriched = []
    for lead in leads:
        q = re.sub(r"\s+", "+", lead["name"])
        # 1) find official website
        params = {"engine":"google", "q":f"{q}+official+site", "api_key":SERP_KEY}
        site_results = GoogleSearch(params).get_dict().get("organic_results", [])
        lead["company_website"] = next(
            (r["link"] for r in site_results if "linkedin.com" not in r.get("link","")), ""
        )

        # 2) find a decision-maker
        params = {"engine":"google", "q":f"{q}+VP+site:linkedin.com/in", "api_key":SERP_KEY}
        people = GoogleSearch(params).get_dict().get("organic_results", [])
        lead["decision_makers"] = [
            {"name": p.get("title",""), "profile": p.get("link","")}
            for p in people[:3]
        ]

        enriched.append(lead)
        time.sleep(1)  # gentle rate-limit

    return enriched

def search_leads(keyword: str):
    """
    1) If keyword matches an EVENT_LINKS entry, crawl its exhibitor page.
    2) Otherwise throw an error (or you could fallback to a generic SERP search).
    3) In both cases, enrich with basic company_website + decision_makers.
    4) Snapshot to db/search.csv and return the list of dicts.
    """
    key = keyword.upper()
    if key in EVENT_LINKS:
        url = EVENT_LINKS[key]
        print(f"→ Crawling exhibitors for event '{keyword}'")
        leads = crawl_event_exhibitors(url)
    else:
        raise ValueError(f"No event link configured for '{keyword}'")

    # Enrich each exhibitor with website & decision makers
    leads = enrich_basic_info(leads)

    # Save to CSV
    save_stage(leads, "search")
    return leads

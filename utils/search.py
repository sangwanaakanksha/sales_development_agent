# utils/search.py

import os
import time
import requests
from bs4 import BeautifulSoup
import re # Make sure re is imported

# Try SerpAPI clients
try:
    from serpapi import GoogleSearch
except ImportError:
    from serpapi import GoogleSearch

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from utils.database import save_stage

SERP_KEY = os.getenv("SERPAPI_API_KEY")

EVENT_LINKS = {
    "ISA2025": (
        "https://isasignexpo2025.mapyourshow.com/8_0/explore/"
        "exhibitor-gallery.cfm?featured=false&categories=1%7C47"
    ),
}

def extract_text_from_soup_element(element, default=""):
    """Safely extracts text from a BeautifulSoup element."""
    return element.get_text(strip=True) if element else default

def crawl_event_exhibitors(event_gallery_url: str, max_exhibitors: int):
    """
    Uses Selenium to get exhibitor detail page URLs from the main gallery,
    then fetches each detail page to extract more comprehensive information.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")


    print(f"Initializing WebDriver to scrape: {event_gallery_url}")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(event_gallery_url)
        # Wait for exhibitor links to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href,'exhibitor-details.cfm?exhid=')]"))
        )
        print("Exhibitor list page loaded.")

        # Find detail links via XPath
        gallery_links_elements = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'exhibitor-details.cfm?exhid=')]"
        )

        exhibitor_detail_page_infos = []
        seen_urls = set()

        for el in gallery_links_elements:
            if len(exhibitor_detail_page_infos) >= max_exhibitors:
                break
            
            detail_url = el.get_attribute("href")
            company_name_from_gallery = el.text.strip()

            if not detail_url or not company_name_from_gallery:
                continue
            
            # Ensure the URL is absolute
            if not detail_url.startswith("http"):
                # Attempt to construct absolute URL based on common patterns for mapyourshow
                base_url_match = re.match(r"(https?://[^/]+)", event_gallery_url)
                if base_url_match:
                    detail_url = base_url_match.group(1) + detail_url if detail_url.startswith('/') else base_url_match.group(1) + '/' + detail_url
                else: # Fallback if base URL can't be easily determined (less likely for mapyourshow)
                    print(f"Warning: Could not form absolute URL for {detail_url}. Skipping.")
                    continue
            
            if detail_url in seen_urls:
                continue
            
            seen_urls.add(detail_url)
            exhibitor_detail_page_infos.append({
                "mapyourshow_detail_url": detail_url,
                "company_name_gallery": company_name_from_gallery
            })
        
        print(f"Found {len(exhibitor_detail_page_infos)} unique exhibitor detail links to scrape (up to max {max_exhibitors}).")

    except Exception as e:
        print(f"Error during Selenium part for gallery page {event_gallery_url}: {e}")
        if driver:
            driver.quit()
        return [] # Return empty if gallery scraping fails
    finally:
        if driver:
            driver.quit() # Ensure driver quits even if loop breaks early or error in loop

    # Now, scrape each detail page
    all_exhibitors_data = []
    for entry_info in exhibitor_detail_page_infos:
        detail_url = entry_info["mapyourshow_detail_url"]
        company_name = entry_info["company_name_gallery"] # Use name from gallery as fallback
        print(f"  -> Scraping details for: {company_name} from {detail_url}")

        data = {
            "name": company_name,
            "mapyourshow_detail_url": detail_url,
            "company_website": "",
            "description": "",
            "location": "",
            "phone": "",
            "email": "",
            "linkedin_company_page": "",
            "raw_contacts_text": "", # For any text blobs that might contain contact names/titles
            "booth_number": ""
        }

        try:
            # Using requests for individual detail pages for speed.
            # If JS rendering is critical for the content on detail pages,
            # you'd need to use driver.get(detail_url) here instead.
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
            response = requests.get(detail_url, headers=headers, timeout=20)
            response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Extracting data from detail page ---

            # Company Name (sometimes more complete on detail page)
            # This is a GUESS - inspect the page for the actual company name element
            name_tag_h1 = soup.find('h1') # Often the main heading
            if name_tag_h1:
                data["name"] = name_tag_h1.get_text(strip=True)
            # Fallback to title tag if h1 is not good
            elif soup.title:
                title_text = soup.title.string
                # Clean up title like "Exhibitor Details - Company Name | Event Name"
                parts = title_text.split('|')[0].replace("Exhibitor Details - ", "").strip()
                if parts: data["name"] = parts


            # Meta Description
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            data["description"] = extract_text_from_soup_element(meta_desc_tag, default="").strip() if meta_desc_tag and meta_desc_tag.get('content') else ''
            if not data["description"]: # Fallback to other description sources if meta is empty
                # Example: Find a div with a class like 'company-description' or 'profile-summary'
                desc_div = soup.find('div', class_=re.compile(r"description|profile|overview", re.I))
                if desc_div: data["description"] = desc_div.get_text(separator="\n", strip=True)


            # Booth Number
            # Example: Look for text "Booth:", or an element with id/class "boothNumber"
            booth_element = soup.find(string=re.compile(r"Booth\s*#?:", re.I))
            if booth_element:
                # Try to get the next sibling's text or parent's text part
                booth_text_candidate = booth_element.find_next_sibling(string=True)
                if booth_text_candidate:
                    data["booth_number"] = booth_text_candidate.strip()
                else: # More complex logic might be needed if it's nested differently
                    parent_text = booth_element.parent.get_text(strip=True)
                    match = re.search(r"Booth\s*#?:\s*([A-Za-z0-9\-]+)", parent_text, re.I)
                    if match: data["booth_number"] = match.group(1)
            if not data["booth_number"]: # Try common class/id patterns
                booth_tag = soup.find(id=re.compile(r"booth", re.I)) or soup.find(class_=re.compile(r"booth", re.I))
                if booth_tag: data["booth_number"] = booth_tag.get_text(strip=True)


            # Location
            # Try to find a specific section or element for location
            # This is very site-specific
            location_section = soup.find(['div', 'p', 'span'], text=re.compile(r"Location:|Address:", re.I))
            if location_section:
                # Attempt to get text from sibling or parent container that seems to hold the address
                parent_container = location_section.parent
                data["location"] = parent_container.get_text(separator=", ", strip=True).replace("Location:", "").replace("Address:","").strip()
            if not data["location"]: # Fallback to broad text search if specific elements fail
                for txt_el in soup.find_all(text=re.compile(r'(city,\s*[A-Z]{2}\s*\d{5}|[A-Z]{2}\s+\d{5}|state\s+zip)', re.I)):
                    # This is a very rough heuristic for US addresses
                    data["location"] = txt_el.strip() # This might grab too much or too little
                    break


            # Company Website
            # Look for <a> tags with href, excluding mailto, tel, and often internal site links
            # This requires careful crafting of regex or conditions
            website_tags = soup.find_all('a', href=True)
            for tag in website_tags:
                href = tag['href']
                text = tag.get_text(strip=True).lower()
                # Prioritize links with text like "website", "visit site", or company name
                # Exclude mapyourshow, mailto, tel, javascript
                if not re.search(r"mapyourshow\.com|mailto:|tel:|javascript:void", href, re.I):
                    if "website" in text or "site" in text or data["name"].lower().split(' ')[0] in text or "www." in href or "http" in href:
                        data["company_website"] = href
                        break # Take the first likely candidate
            if not data["company_website"] and website_tags: # Broader fallback if specific not found
                 for tag in website_tags:
                    href = tag['href']
                    if href.startswith("http") and not re.search(r"mapyourshow\.com|linkedin\.com|facebook\.com|twitter\.com|instagram\.com", href, re.I):
                        data["company_website"] = href
                        break


            # Phone Number
            phone_tag = soup.find('a', href=re.compile(r"tel:"))
            if phone_tag:
                data["phone"] = phone_tag['href'].replace("tel:", "").strip()
            if not data["phone"]:
                phone_match = soup.find(text=re.compile(r"(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4})"))
                if phone_match: data["phone"] = phone_match.strip()


            # Email Address
            email_tag = soup.find('a', href=re.compile(r"mailto:"))
            if email_tag:
                data["email"] = email_tag['href'].replace("mailto:", "").strip().split('?')[0] # Remove subject etc.
            if not data["email"]:
                email_match = soup.find(text=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"))
                if email_match: data["email"] = email_match.strip()


            # LinkedIn Company Page
            linkedin_tags = soup.find_all('a', href=re.compile(r"linkedin\.com/(company/|school/|in/)", re.I))
            for tag in linkedin_tags:
                href = tag['href']
                if "company/" in href or "school/" in href : # Prioritize company/school pages
                    data["linkedin_company_page"] = href
                    break
            # If no company page, take first LinkedIn link found (could be a person)
            if not data["linkedin_company_page"] and linkedin_tags:
                 data["linkedin_company_page"] = linkedin_tags[0]['href']


            # Raw Contacts Text (for later processing, e.g., by an LLM)
            # Look for sections titled "Contact Us", "Staff", "Personnel", etc.
            # This is very heuristic.
            contact_headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'],
                                           text=re.compile(r"Contact(s)?|Staff|Personnel|Team|Representatives|Key Personnel", re.I))
            contact_info_parts = []
            for header in contact_headers:
                # Try to find the parent container that holds the contact details
                parent_container = header.find_parent(['div', 'section', 'article', 'p', 'ul', 'table']) # Adjust tags as needed
                if parent_container:
                    contact_info_parts.append(parent_container.get_text(separator='\n', strip=True))
            if contact_info_parts:
                data["raw_contacts_text"] = "\n---\n".join(list(set(contact_info_parts))) # Join unique sections

            # Fallback if no headers found, look for divs with contact-related classes/ids
            if not data["raw_contacts_text"]:
                contact_divs = soup.find_all('div', class_=re.compile(r"contact|staff|personnel|team", re.I))
                for div in contact_divs:
                     data["raw_contacts_text"] += div.get_text(separator='\n', strip=True) + "\n---\n"
                data["raw_contacts_text"] = data["raw_contacts_text"].strip("-\n ")


            all_exhibitors_data.append(data)
            time.sleep(0.5) # Be polite to the server

        except requests.exceptions.RequestException as req_err:
            print(f"      !! Request error for {detail_url}: {req_err}")
            all_exhibitors_data.append(data) # Append with whatever was found
        except Exception as e_detail:
            print(f"      !! Error processing detail page {detail_url} for {company_name}: {e_detail}")
            all_exhibitors_data.append(data) # Append with whatever was found, even if partial

    return all_exhibitors_data


def search_leads(keyword: str, num_leads: int = 10):
    """
    1) If keyword matches EVENT_LINKS, crawl that page.
    2) Otherwise fallback to SerpAPI lookup.
    3) Save to db/search.csv
    """
    key = (keyword or "").upper()
    leads = []

    if key in EVENT_LINKS:
        event_gallery_url = EVENT_LINKS[key]
        print(f"→ Crawling up to {num_leads} exhibitors for event '{keyword}' from {event_gallery_url}")
        leads = crawl_event_exhibitors(event_gallery_url, num_leads)
    else:
        print(f"→ Performing SerpAPI search for '{keyword}' (up to {num_leads} results)")
        if not SERP_KEY:
            raise RuntimeError("SERPAPI_API_KEY not set for general search.")
        params = {"engine": "google", "q": keyword, "api_key": SERP_KEY, "num": num_leads}
        try:
            search_results = GoogleSearch(params).get_dict()
            organic_results = search_results.get("organic_results", [])
            
            for r in organic_results:
                leads.append({
                    "name": r.get("title", ""),
                    "mapyourshow_detail_url": "", # Not applicable for SerpAPI
                    "company_website": r.get("link", ""), # Google link is usually the company website
                    "description": r.get("snippet", ""),
                    "location": r.get("address",""), # SerpAPI sometimes provides address
                    "phone": "", # Typically not directly in SERP results
                    "email": "", # Typically not directly in SERP results
                    "linkedin_company_page": "", # Need further processing for this
                    "raw_contacts_text": "",
                    "booth_number": ""
                })
        except Exception as e_serp:
            print(f"Error during SerpAPI search: {e_serp}")

    # Ensure all defined keys exist for all leads for consistent CSV structure
    default_lead_keys = [
        "name", "mapyourshow_detail_url", "company_website", "description", 
        "location", "phone", "email", "linkedin_company_page", 
        "raw_contacts_text", "booth_number"
    ]
    processed_leads = []
    for lead_data in leads:
        processed_lead = {key: lead_data.get(key, "") for key in default_lead_keys}
        processed_leads.append(processed_lead)

    if processed_leads:
        save_stage(processed_leads, "search") # Assuming save_stage handles list of dicts
        print(f"-> Saved {len(processed_leads)} leads to db/search.csv")
    else:
        print("-> No leads found or processed.")
        
    return processed_leads

if __name__ == '__main__':
    # Basic test for crawl_event_exhibitors
    print("Testing ISA2025 exhibitor crawl (max 3)...")
    isa_leads = search_leads("ISA2025", 3)
    if isa_leads:
        print("\nSample leads from ISA2025 crawl:")
        for i, lead in enumerate(isa_leads[:2]):
            print(f"\n--- Lead {i+1} ---")
            for k, v in lead.items():
                print(f"  {k}: {v}")
    else:
        print("No leads returned from ISA2025 test crawl.")

    # Basic test for SerpAPI fallback (if you have a key and want to test)
    # print("\nTesting SerpAPI fallback for 'digital signage companies' (max 2)...")
    # general_leads = search_leads("digital signage companies", 2)
    # if general_leads:
    #     print("\nSample leads from SerpAPI crawl:")
    #     for i, lead in enumerate(general_leads[:2]):
    #         print(f"\n--- Lead {i+1} ---")
    #         for k, v in lead.items():
    #             print(f"  {k}: {v}")
    # else:
    #     print("No leads returned from SerpAPI test crawl (check API key and query).")
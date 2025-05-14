# utils/search.py

import os
import time
import requests
from bs4 import BeautifulSoup, Comment
import re
from urllib.parse import urljoin # For constructing absolute URLs

# Try SerpAPI clients
try:
    from serpapi import GoogleSearch
except ImportError:
    from google_search_results import GoogleSearch # type: ignore

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.database import save_stage # Assuming you have this utility

SERP_KEY = os.getenv("SERPAPI_API_KEY")

EVENT_LINKS = {
    "ISA2025": (
        "https://isasignexpo2025.mapyourshow.com/8_0/explore/"
        "exhibitor-gallery.cfm?featured=false&categories=1%7C47"
    ),
}

def clean_text(text: str, is_description: bool = False) -> str:
    """Cleans text by removing excessive whitespace and common unwanted phrases."""
    if not isinstance(text, str):
        return ""
    
    text = re.sub(r'<[^>]+>', ' ', text) # Remove any lingering HTML tags
    
    # Remove common event portal boilerplate first
    boilerplate_patterns = [
        r"My Planner", r"My Profile", r"Recommendations", r"Sign Out",
        r"function\s+parse_query_string\s*\(.*?\)\s*\{[\s\S]*?\}",
        r"var\s+\w+\s*=\s*.*;", r"document\.getElementById\s*\(.*?\)",
        r"sessionStorage\.getItem\s*\(.*?\)", r"sessionStorage\.setItem\s*\(.*?\)",
        r"Vue\.component\s*\(.*?\)\s*\{[\s\S]*?\}\);",
        r"ShowID", r"exhid", r"contactid", r"chatid",
        r"Copyright\s*©.*All rights reserved", r"Privacy Policy", r"Terms of Use",
        r"Skip to main content", r"Toggle navigation",
        r"There are no available appointments for this exhibitor\." # Specific boilerplate
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    text = re.sub(r'\s+', ' ', text).strip() # Normalize whitespace
    
    if is_description: # More aggressive cleaning for descriptions
        text = re.sub(r"^[^a-zA-Z0-9(\"\']+", "", text) # Remove leading non-alphanumeric (allow quotes, parens)
        text = re.sub(r"[^a-zA-Z0-9\s\.\,\!\?\-\–\'\"\(\)]+$", "", text) # Remove trailing non-alphanumeric
        if len(text) < 20 and not re.search(r"[a-zA-Z]{5,}", text): # If very short and no real words
            return ""
    return text.strip()


def extract_from_detail_page(soup: BeautifulSoup, company_name_from_gallery: str, detail_page_url: str) -> dict:
    """Extracts detailed information from a single exhibitor's BeautifulSoup object."""
    
    data = {
        "name": company_name_from_gallery, # Start with gallery name as fallback
        "mapyourshow_detail_url": detail_page_url,
        "company_website": "", "description": "", "location": "", "phone": "",
        "email": "", "linkedin_company_page": "", "raw_contacts_text": "",
        "booth_number": "", "size": "", "revenue": "", "industry": ""
    }

    # 1. Company Name (prioritize specific elements on detail page)
    # Common selectors for company name on exhibitor portals
    name_selectors = ['h1.companyName', 'h1.ExhibitorName', 'div.profile-title h1', 'div.exhibitor-name h1', 'h1']
    for selector in name_selectors:
        name_tag = soup.select_one(selector)
        if name_tag:
            name_text = clean_text(name_tag.get_text(strip=True))
            if name_text and len(name_text) > 2 and name_text.lower() != "exhibitor details": # Ensure it's not generic
                data["name"] = name_text
                break
    if not data["name"] or data["name"] == company_name_from_gallery: # If h1 failed or was same as gallery
        if soup.title:
            title_text = clean_text(soup.title.string)
            # Try to extract from title like "Exhibitor Details - COMPANY NAME | Event"
            match = re.search(r"Exhibitor Details\s*-\s*(.+?)\s*\|", title_text, re.I)
            if match and match.group(1).strip():
                data["name"] = match.group(1).strip()


    # 2. Description
    # Try meta description first
    meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_desc_tag and meta_desc_tag.get('content'):
        desc = clean_text(meta_desc_tag.get('content'), is_description=True)
        if len(desc) > 30: # Check if it's substantial
            data["description"] = desc
    
    if not data["description"]:
        # Look for specific description divs/sections
        desc_container_selectors = [
            'div.company-description', 'div.exhibitor-description', 
            'div[itemprop="description"]', 'section#about-us p',
            'div.profile-text', 'div.overview-text'
        ]
        for selector in desc_container_selectors:
            desc_element = soup.select_one(selector)
            if desc_element:
                desc_text = clean_text(desc_element.get_text(separator=' ', strip=True), is_description=True)
                if len(desc_text) > 50: # Require a decent length
                    data["description"] = desc_text[:700] # Limit length
                    break
    data["description"] = data["description"].replace(company_name_from_gallery, "").strip() # Remove company name if it's just that


    # 3. Booth Number - Needs to be very specific
    # Look for elements explicitly labeling a booth number
    booth_text_patterns = [
        r"Booth\s*#?:\s*([A-Za-z0-9\-]+(?:\s?[A-Za-z0-9\-]+)*)",
        r"Stand\s*#?:\s*([A-Za-z0-9\-]+(?:\s?[A-Za-z0-9\-]+)*)"
    ]
    booth_label_elements = soup.find_all(string=re.compile(r"Booth|Stand", re.I))
    for label_el in booth_label_elements:
        # Check parent or nearby elements for the actual number
        parent = label_el.parent
        if parent:
            parent_text = clean_text(parent.get_text(strip=True))
            for pattern in booth_text_patterns:
                match = re.search(pattern, parent_text, re.I)
                if match and match.group(1) and not any(name_part.lower() in match.group(1).lower() for name_part in data["name"].split() if len(name_part)>2): # Avoid company name
                    data["booth_number"] = match.group(1).strip()
                    break
            if data["booth_number"]: break
    
    if not data["booth_number"]: # Try class-based selectors as fallback
        booth_css_selectors = ['.boothNumber', '.booth-id', '[class*="booth-num"]']
        for selector in booth_css_selectors:
            booth_tag = soup.select_one(selector)
            if booth_tag:
                booth_val = clean_text(booth_tag.get_text(strip=True))
                if booth_val and len(booth_val) < 15 and not any(name_part.lower() in booth_val.lower() for name_part in data["name"].split() if len(name_part)>2):
                    data["booth_number"] = booth_val
                    break

    # 4. Company Website
    website_tags = soup.select('a[href]')
    for tag in website_tags:
        href = tag.get('href', '').strip()
        text = tag.get_text(strip=True).lower()
        # Prioritize links with text like "website", "visit site", or if href looks like a main domain
        if href.startswith("http") and not any(domain in href for domain in ["mapyourshow.com", "linkedin.com", "facebook.com", "twitter.com", "instagram.com", "javascript:void", "mailto:", "tel:"]):
            if "website" in text or "site" in text or "home" == text:
                data["company_website"] = href
                break
            # Check if the link is a root domain or common company URL pattern
            if re.match(r"https?://(www\.)?[^/]+\.[^/.]+(?!.*/.+)", href) and data["name"].split(' ')[0].lower() in href.lower(): # Basic check
                 data["company_website"] = href
                 break
    if not data["company_website"] and website_tags: # Broader fallback
         for tag in website_tags:
            href = tag['href']
            if href.startswith("http") and not any(domain in href for domain in ["mapyourshow.com", "linkedin.com", "facebook.com", "twitter.com", "instagram.com", "javascript:void(0)", "mailto:", "tel:"]):
                data["company_website"] = href
                break

    # 5. Phone Number
    phone_tag = soup.select_one('a[href^="tel:"]')
    if phone_tag:
        data["phone"] = phone_tag['href'].replace("tel:", "").strip()
    if not data["phone"]:
        phone_regex_strict = r"\b(?:\+?\d{1,3}[-\.\s()]*)?\(?\d{3}\)?[-\.\s()]?\d{3}[-\.\s]?\d{4}\b"
        body_text = soup.get_text(separator=' ', strip=True)
        phone_matches = re.findall(phone_regex_strict, body_text)
        if phone_matches:
            data["phone"] = clean_text(phone_matches[0])

    # 6. Email Address
    email_tag = soup.select_one('a[href^="mailto:"]')
    if email_tag:
        data["email"] = email_tag['href'].replace("mailto:", "").split('?')[0].strip()
    if not data["email"]:
        email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        body_text = soup.get_text(separator=' ', strip=True)
        email_match = re.search(email_regex, body_text)
        if email_match:
            data["email"] = clean_text(email_match.group(0))

    # 7. LinkedIn Company Page
    linkedin_tags = soup.select('a[href*="linkedin.com/company/"]')
    if linkedin_tags:
        data["linkedin_company_page"] = linkedin_tags[0]['href'].strip()
    else:
        linkedin_tags_other = soup.select('a[href*="linkedin.com/"]') # More general
        for tag in linkedin_tags_other:
            href = tag['href']
            if "/in/" not in href and "/pub/" not in href: # Avoid personal profiles for now
                data["linkedin_company_page"] = href
                break
    
    # 8. Raw Contacts Text (very heuristic)
    contact_keywords = ['Contact Us', 'Our Team', 'Sales Contacts', 'Representatives', 'Staff', 'Personnel', 'Key Contacts', 'Meet the Team']
    raw_text_parts = []
    for keyword in contact_keywords:
        header = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','p','strong','b'] and keyword.lower() in tag.get_text(strip=True).lower())
        if header:
            # Look for nearby text content, trying a few parent levels or siblings
            parent_search_levels = 3
            current_el = header
            for _ in range(parent_search_levels):
                if current_el.parent:
                    parent_text = clean_text(current_el.parent.get_text(separator='\n', strip=True))
                    if len(parent_text) > 30 and len(parent_text) < 1000: # Some substance, not too huge
                        raw_text_parts.append(parent_text)
                        break 
                    current_el = current_el.parent
                else:
                    break
    if raw_text_parts:
        data["raw_contacts_text"] = "\n---\n".join(list(set(raw_text_parts)))[:700]
    
    # Final cleanup on all string fields
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = clean_text(value, is_description=(key == "description"))
            if key == "description" and (not data[key] or len(data[key])<20): # If description is poor after cleaning
                data[key] = "No detailed description available on event page."


    return data


def crawl_event_exhibitors(event_gallery_url: str, max_exhibitors: int):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

    print(f"Initializing WebDriver to scrape: {event_gallery_url}")
    driver = None
    exhibitor_detail_page_infos = []

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(event_gallery_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href,'exhibitor-details.cfm?exhid=')]"))
        )
        print("Exhibitor list page loaded.")
        
        # This XPath should target the link that contains the company name
        gallery_links_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'companyName')]/a | //a[.//div[contains(@class, 'companyName')]] | //a[contains(@class, 'exhibitorName')]") # More specific
        if not gallery_links_elements: # Fallback
             gallery_links_elements = driver.find_elements(By.XPATH, "//a[contains(@href,'exhibitor-details.cfm?exhid=')]")


        seen_urls = set()
        for el in gallery_links_elements:
            if len(exhibitor_detail_page_infos) >= max_exhibitors:
                break
            
            detail_url = el.get_attribute("href")
            company_name_from_gallery = el.text.strip() # This should be the company name

            if not detail_url or not company_name_from_gallery:
                # Try to find name from a child div if el.text is empty
                name_div = el.find_elements(By.XPATH, ".//div[contains(@class, 'companyName')] | .//div[contains(@class, 'exhibitorName')]")
                if name_div:
                    company_name_from_gallery = name_div[0].text.strip()

            if not detail_url or not company_name_from_gallery:
                print(f"Warning: Could not extract URL or name from gallery element: {el.get_attribute('outerHTML')[:100]}")
                continue
            
            detail_url = urljoin(event_gallery_url, detail_url) # Ensure absolute URL
            
            if detail_url in seen_urls:
                continue
            
            seen_urls.add(detail_url)
            exhibitor_detail_page_infos.append({
                "mapyourshow_detail_url": detail_url,
                "company_name_gallery": company_name_from_gallery # Store the name from the gallery
            })
        
        print(f"Found {len(exhibitor_detail_page_infos)} unique exhibitor detail links (max {max_exhibitors}).")

    except Exception as e:
        print(f"Error during Selenium part for gallery page {event_gallery_url}: {e}")
        return []
    finally:
        if driver: driver.quit()

    all_exhibitors_data = []
    for entry_info in exhibitor_detail_page_infos:
        detail_url = entry_info["mapyourshow_detail_url"]
        company_name_from_gallery = entry_info["company_name_gallery"]
        
        print(f"  -> Scraping details for: {company_name_from_gallery} from {detail_url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
            response = requests.get(detail_url, headers=headers, timeout=20)
            response.raise_for_status()
            
            # Clean HTML before parsing specific elements
            soup_cleaned = BeautifulSoup(response.text, 'html.parser')
            for unwanted_tag in soup_cleaned(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
                unwanted_tag.decompose()
            for comment in soup_cleaned.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Extract data using the helper function
            data = extract_from_detail_page(soup_cleaned, company_name_from_gallery, detail_url)
            all_exhibitors_data.append(data)
            time.sleep(0.2) # Be polite

        except requests.exceptions.RequestException as req_err:
            print(f"      !! Request error for {detail_url}: {req_err}")
            # Append a minimal record so we know it was attempted
            all_exhibitors_data.append({"name": company_name_from_gallery, "mapyourshow_detail_url": detail_url, "description": "Request Error", "error_message": str(req_err)})
        except Exception as e_detail:
            print(f"      !! Error processing detail page {detail_url} for {company_name_from_gallery}: {e_detail}")
            all_exhibitors_data.append({"name": company_name_from_gallery, "mapyourshow_detail_url": detail_url, "description": "Processing Error", "error_message": str(e_detail)})

    print(f"Finished scraping {len(all_exhibitors_data)} exhibitor detail pages.")
    return all_exhibitors_data


def search_leads(keyword: str, num_leads: int = 10):
    key = (keyword or "").upper()
    leads_data = []

    if key in EVENT_LINKS:
        event_gallery_url = EVENT_LINKS[key]
        print(f"→ Crawling up to {num_leads} exhibitors for event '{keyword}' from {event_gallery_url}")
        leads_data = crawl_event_exhibitors(event_gallery_url, num_leads)
    else:
        print(f"→ Performing SerpAPI search for '{keyword}' (up to {num_leads} results)")
        if not SERP_KEY or not GoogleSearch: # Check if GoogleSearch itself is None
            print("Warning: SerpAPI client or API key not available. SerpAPI search will be skipped.")
            leads_data = [{"name": keyword, "description": "SerpAPI key not configured or client not installed."}]
        else:
            params = {"engine": "google", "q": f"{keyword} company", "api_key": SERP_KEY, "num": num_leads}
            try:
                search_results_json = GoogleSearch(params).get_json()
                organic_results = search_results_json.get("organic_results", [])
                for r in organic_results:
                    leads_data.append({
                        "name": r.get("title", ""), "mapyourshow_detail_url": "",
                        "company_website": r.get("link", ""), "description": r.get("snippet", ""),
                        "location": r.get("address","") if "address" in r else "", "phone": "", "email": "",
                        "linkedin_company_page": "", "raw_contacts_text": "", "booth_number": "",
                        "size": "", "revenue": "", "industry": ""
                    })
            except Exception as e_serp:
                print(f"Error during SerpAPI search: {e_serp}")
                leads_data.append({"name": keyword, "description": f"SerpAPI search failed: {e_serp}"})

    default_lead_keys = [
        "name", "mapyourshow_detail_url", "company_website", "description", "location", "phone", 
        "email", "linkedin_company_page", "raw_contacts_text", "booth_number", 
        "size", "revenue", "industry"
    ]
    
    processed_leads = []
    if isinstance(leads_data, list):
        for lead_item in leads_data:
            if isinstance(lead_item, dict):
                # Ensure all keys are present, defaulting to empty string
                processed_lead = {key: clean_text(str(lead_item.get(key, ""))) for key in default_lead_keys}
                
                # Specific final cleanup for description and booth_number
                processed_lead["description"] = clean_text(processed_lead["description"], is_description=True)
                if not processed_lead["description"]: # If still empty after cleaning
                    processed_lead["description"] = "No detailed description available."

                # Validate booth number: should be short and not contain the company name
                if len(processed_lead["booth_number"]) > 15 or \
                   (processed_lead["name"] and processed_lead["name"].lower() in processed_lead["booth_number"].lower()):
                    processed_lead["booth_number"] = ""
                
                processed_leads.append(processed_lead)
            else:
                print(f"Warning: Found non-dictionary item in leads_data during final processing: {lead_item}")
    else:
        print(f"Warning: leads_data is not a list after search/crawl: {leads_data}")

    if processed_leads:
        save_stage(processed_leads, "search")
        print(f"-> Saved {len(processed_leads)} leads to db/search.csv")
    else:
        print("-> No leads found or processed by search_leads.")
    return processed_leads

if __name__ == '__main__':
    print("Testing ISA2025 exhibitor crawl (max 2)...")
    isa_leads = search_leads("ISA2025", 2) # Test with a small number
    if isa_leads:
        print(f"\n--- Found {len(isa_leads)} leads from ISA2025 crawl ---")
        for i, lead in enumerate(isa_leads):
            print(f"\n--- Lead {i+1} ---")
            for k, v in lead.items():
                print(f"  {k}: {v}")
    else:
        print("No leads returned from ISA2025 test crawl.")

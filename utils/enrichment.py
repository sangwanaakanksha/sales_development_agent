# utils/enrichment.py

import os
import logging
from utils.outreach import generate_outreach # This function expects leads_list, user_signature, user_name_for_signature
from dotenv import load_dotenv
# import json # Not used
from langchain_openai import OpenAI as LangchainOpenAI # Use a distinct alias
from utils.database import save_stage

# Try SerpAPI clients
try:
    from serpapi import GoogleSearch
except ImportError:
    try:
        from serpapi  import GoogleSearch
    except ImportError:
        GoogleSearch = None
        print("Warning: SerpAPI client (serpapi or google-search-results) not found. LinkedIn search will be skipped.")

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Ensure this is loaded

ICP_DESCRIPTION = """
Specializes in large-format signage, vehicle wraps, and architectural graphics;
Global $8B+ revenue, thousands of employees;
Exhibits at ISA Sign Expo, active in industry associations;
Decision-makers: VPs of Product Development, Directors of Innovation, R&D leaders.
"""

def get_company_linkedin_url_via_serpapi(company_name: str) -> str:
    if not GoogleSearch or not SERPAPI_API_KEY:
        # logger.warning("SerpApi client or API key not available for LinkedIn search.") # Already logged in search_leads
        return ""
    if not company_name:
        return ""
    try:
        params = {
            "engine": "google",
            "q": f"{company_name} LinkedIn company profile site:linkedin.com/company",
            "api_key": SERPAPI_API_KEY,
            "num": 1
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])
        if organic_results:
            first_result_link = organic_results[0].get("link", "")
            if "linkedin.com/company/" in first_result_link:
                return first_result_link
    except Exception as e:
        logger.error(f"SerpApi LinkedIn search failed for {company_name}: {e}")
    return ""

def external_profile_lookup(company_name: str) -> dict:
    logger.debug(f"Lookup external profile for {company_name}")
    return {"size": None, "revenue": None, "industry": None}

# Corrected function signature to accept all necessary arguments
def enrich_leads(leads: list, user_signature: str, user_name_for_signature: str, event_name: str = "ISA Sign Expo 2025") -> list:
    if not leads:
        logger.info("No leads provided to enrich.")
        return []

    llm = None
    try:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        llm = LangchainOpenAI(temperature=0, model_name="gpt-3.5-turbo-instruct", openai_api_key=OPENAI_API_KEY)
        logger.info("OpenAI LLM initialized for enrichment.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM: {e}.")
        return [dict(lead, qualified="Error", actionable="Error", qualification_rationale=f"LLM Init Failed: {e}", outreach_message="") for lead in leads]

    enriched_leads_list = []
    for lead_data in leads:
        if not isinstance(lead_data, dict):
            logger.warning(f"Skipping non-dictionary item in leads list: {lead_data}")
            continue
        
        current_lead = lead_data.copy()
        company_name = current_lead.get('name', '')
        company_description = current_lead.get('description', 'No description available')

        try:
            profile = external_profile_lookup(company_name)
            current_lead.update(profile)

            if company_name and not current_lead.get("linkedin_company_page") and not current_lead.get("linkedin_company_page_serpapi"):
                logger.info(f"Searching LinkedIn page for {company_name} via SerpApi...")
                linkedin_url = get_company_linkedin_url_via_serpapi(company_name)
                current_lead["linkedin_company_page_serpapi"] = linkedin_url or ""
            
            prompt = (
                f"Evaluate if the following company matches this Ideal Customer Profile (ICP):\n"
                f"ICP: {ICP_DESCRIPTION}\n\n"
                f"Company Name: {company_name}\n"
                f"Company Description: {company_description}\n\n"
                f"Respond in two parts separated by '###RATIONALE###'.\n"
                f"Part 1: 'Yes' or 'No' indicating if the company matches the ICP.\n"
                f"Part 2: A brief (1-2 sentence) rationale for your decision based on the ICP and company details."
            )
            
            llm_response_text = llm.invoke(prompt)
            
            qualification_rationale = "Rationale not extracted by LLM."
            qualified = "No" # Default to No
            if "###RATIONALE###" in llm_response_text:
                parts = llm_response_text.split("###RATIONALE###", 1)
                qualification_decision_text = parts[0].strip().lower()
                qualified = "Yes" if "yes" in qualification_decision_text else "No"
                qualification_rationale = parts[1].strip()
            else:
                logger.warning(f"LLM response for {company_name} did not follow rationale format: {llm_response_text}")
                qualified = "Yes" if "yes" in llm_response_text.lower() else "No" # Basic fallback

            actionable = "Yes" if qualified == "Yes" else "No"

            current_lead.update({
                "qualified": qualified,
                "qualification_rationale": qualification_rationale,
                "actionable": actionable
            })
            enriched_leads_list.append(current_lead)

        except Exception as e_inner:
            logger.exception(f"Error enriching lead {company_name}: {e_inner}")
            current_lead.update({
                "qualified": "Error", 
                "qualification_rationale": f"Enrichment error: {e_inner}",
                "actionable": "No",
                "outreach_message": "" # Ensure outreach_message key exists even on error
            })
            enriched_leads_list.append(current_lead)
    
    leads_with_outreach = []
    if enriched_leads_list:
        logger.info(f"Generating outreach messages for {len(enriched_leads_list)} enriched leads...")
        # Correctly pass all required arguments to generate_outreach
        leads_with_outreach = generate_outreach(
            enriched_leads_list, 
            user_signature, 
            user_name_for_signature, # This was the missing argument being passed correctly
            event_name # Pass event_name if you want it dynamic, or rely on default in outreach.py
        )
    else:
        logger.info("No successfully enriched leads to generate outreach messages for.")

    if not leads_with_outreach and enriched_leads_list: # If outreach failed but enrichment happened
        logger.warning("Outreach generation step returned no leads, saving enriched leads without outreach messages.")
        save_stage(enriched_leads_list, "enriched") # Save at least the enriched data
        return enriched_leads_list

    save_stage(leads_with_outreach, "enriched")
    logger.info(f"Saved {len(leads_with_outreach)} enriched leads (with outreach) to db/enriched.csv")
    return leads_with_outreach


if __name__ == "__main__":
    import pandas as pd
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. LLM calls in smoke test will fail.")
    if not SERPAPI_API_KEY:
        print("WARNING: SERPAPI_API_KEY not set. SerpApi calls in smoke test will be skipped.")

    search_csv_path = 'db/search.csv'
    # ... (rest of your smoke test, ensure it passes all required args to enrich_leads)
    if not os.path.exists(search_csv_path):
        logger.info(f"Creating dummy {search_csv_path} for smoke test.")
        dummy_search_data = [
            {"name": "TestCo 1 from Search", "description": "Innovators in testing.", "raw_contacts_text": "Alice Manager", "company_website": "http://testco1.com"},
            {"name": "DevInc from Search", "description": "Developers of fine software.", "raw_contacts_text": "Bob Director", "company_website": "http://devinc.com"}
        ]
        if not os.path.exists('db'):
            os.makedirs('db')
        pd.DataFrame(dummy_search_data).to_csv(search_csv_path, index=False)

    leads_from_search = pd.read_csv(search_csv_path).to_dict(orient='records')
    
    if leads_from_search:
        dummy_signature_str = "\n\nBest,\nTest User\nTest Corp"
        dummy_user_name_str = "Test User"
        
        final_enriched_leads = enrich_leads(leads_from_search, dummy_signature_str, dummy_user_name_str, event_name="Test Event")
        
        print("\n--- Sample of Final Enriched Leads (from enrich_leads function output) ---")
        if final_enriched_leads:
            df_sample = pd.DataFrame(final_enriched_leads)
            with pd.option_context('display.width', 1000, 'display.max_colwidth', 70):
                print(df_sample.head(3))
        else:
            print("enrich_leads returned no data.")
    else:
        logger.info(f"No leads loaded from {search_csv_path} for smoke test.")

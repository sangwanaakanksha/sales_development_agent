# utils/enrichment.py

import os
import logging
from utils.outreach import generate_outreach # Assuming this is correctly defined in outreach.py
from dotenv import load_dotenv
load_dotenv()

import json # Not currently used, can be removed if not needed later
from langchain_community.llms import OpenAI
from utils.database import save_stage

# configure logger
logging.basicConfig(level=logging.INFO) # Consider format for logger: logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Your ICP description
ICP_DESCRIPTION = """
Specializes in large-format signage, vehicle wraps, and architectural graphics;
Global $8B+ revenue, thousands of employees;
Exhibits at ISA Sign Expo, active in industry associations;
Decision-makers: VPs of Product Development, Directors of Innovation, R&D leaders.
"""

# Placeholder for external enrichment API (e.g., Clearbit)
def external_profile_lookup(company_name: str) -> dict:
    """
    Stub for real API. Logs lookup attempts.
    """
    logger.debug(f"Lookup external profile for {company_name}")
    # TODO: integrate real enrichment API here
    # Ensure keys returned here are handled consistently if they are sparse
    return {"size": None, "revenue": None, "industry": None}


def enrich_leads(leads: list, user_signature: str) -> list: # Added return type hint
    """
    • Classify each lead vs. ICP with an LLM
    • Mark actionable if qualified
    • Generates outreach messages
    • Snapshot to db/enriched.csv
    """
    if not leads:
        logger.info("No leads provided to enrich.")
        return []

    # It's good practice to initialize the LLM once if possible,
    # but for this structure, initializing per call is also fine.
    # Consider cost/performance if calling enrich_leads frequently with many leads.
    try:
        llm = OpenAI(temperature=0) # Add API key if not globally configured: openai_api_key=os.getenv("OPENAI_API_KEY")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM: {e}. Make sure OPENAI_API_KEY is set.")
        # Depending on desired behavior, you might return leads as is, or an empty list, or raise e
        return leads # Return leads unprocessed if LLM fails

    enriched_leads_list = [] # Use a different name to avoid confusion with the input 'leads'

    for lead_data in leads: # Use a more descriptive variable name for each item
        if not isinstance(lead_data, dict):
            logger.warning(f"Skipping non-dictionary item in leads list: {lead_data}")
            continue
        try:
            # It's safer to work on a copy if you're modifying and then potentially conditionally adding
            current_lead = lead_data.copy()

            # merge external profile placeholders
            profile = external_profile_lookup(current_lead.get('name', ''))
            current_lead.update(profile)

            # Build qualification prompt
            prompt = (
                f"Ideal Customer Profile:\n{ICP_DESCRIPTION}\n\n"
                f"Company:\n  Name: {current_lead.get('name','')}\n"
                f"  Description: {current_lead.get('description','No description available')}\n\n"
                "Respond with only 'Yes' or 'No' if this company matches the ICP."
            )
            resp = llm.invoke(prompt) # Updated to use .invoke() as per LangChain deprecation
            qualified = "Yes" if "yes" in resp.lower() else "No"
            
            # Actionable logic: 'decision_makers' key is not reliably populated by search.py
            # The 'raw_contacts_text' is what search.py provides.
            # For a simple 'actionable' flag now, let's base it on qualification.
            # True 'actionable' would need parsing of 'raw_contacts_text' or other contact finding.
            actionable = "Yes" if qualified == "Yes" else "No" # Simplified actionable

            current_lead.update({"qualified": qualified, "actionable": actionable})
            enriched_leads_list.append(current_lead)
        except Exception as e_inner:
            logger.exception(f"Error enriching lead {lead_data.get('name', 'Unknown Lead')}: {e_inner}")
            # Optionally append the original lead_data if enrichment fails partway
            # enriched_leads_list.append(lead_data)

    # Now add outreach messages
    leads_with_outreach = [] # Initialize
    if enriched_leads_list:
        logger.info(f"Generating outreach messages for {len(enriched_leads_list)} enriched leads...")
        leads_with_outreach = generate_outreach(enriched_leads_list, user_signature) # generate_outreach should return a new list
    else:
        logger.info("No successfully enriched leads to generate outreach messages for.")
        # If enriched_leads_list is empty, leads_with_outreach will also be empty.

    if not leads_with_outreach:
        logger.warning("No leads available after outreach generation step. Saving an empty file or skipping.")
        # Depending on desired behavior, save_stage might create an empty file or you might skip saving.
        # save_stage([], "enriched") # Creates an empty CSV with headers if save_stage is designed so
        # return []

    save_stage(leads_with_outreach, "enriched") # Save the version with outreach messages
    logger.info(f"Saved {len(leads_with_outreach)} enriched leads (with outreach) to db/enriched.csv")
    return leads_with_outreach # Return the version with outreach

# Removed the dead code block that was here

if __name__ == "__main__":
    # smoke test
    import pandas as pd
    # Ensure OPENAI_API_KEY is set in your .env for this test to work fully
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. LLM calls in smoke test will fail.")

    search_csv_path = 'db/search.csv'
    if not os.path.exists(search_csv_path):
        logger.error(f"{search_csv_path} not found; run search stage first or create a dummy file.")
        # Create a dummy db/search.csv for testing if it doesn't exist
        dummy_search_data = [
            {"name": "TestCo 1 from Search", "description": "Innovators in testing.", "raw_contacts_text": "Alice Manager"},
            {"name": "DevInc from Search", "description": "Developers of fine software.", "raw_contacts_text": "Bob Director"}
        ]
        if not os.path.exists('db'):
            os.makedirs('db')
        pd.DataFrame(dummy_search_data).to_csv(search_csv_path, index=False)
        logger.info(f"Created dummy {search_csv_path} for smoke test.")

    leads_from_search = pd.read_csv(search_csv_path).to_dict(orient='records')
    
    if leads_from_search:
        final_enriched_leads = enrich_leads(leads_from_search)
        print("\n--- Sample of Final Enriched Leads (from enrich_leads function output) ---")
        if final_enriched_leads:
            df_sample = pd.DataFrame(final_enriched_leads)
            # Configure pandas display for better terminal output during smoke test
            with pd.option_context('display.width', 1000, 'display.max_colwidth', 70):
                print(df_sample.head(3))
        else:
            print("enrich_leads returned no data.")
    else:
        logger.info(f"No leads loaded from {search_csv_path} for smoke test.")
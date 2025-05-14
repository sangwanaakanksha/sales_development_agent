# run.py

import os
import pandas as pd
import logging

# Import utility functions from the utils package
from utils.search import search_leads
from utils.enrichment import enrich_leads # This function now expects 'leads', 'user_signature', 'user_name_for_signature'
from utils.finalize import finalize
# utils.outreach and utils.guardrail are used within enrichment.py

# Configure basic logging for the run.py script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main function to orchestrate the lead generation and enrichment pipeline.
    """
    logger.info("🚀 Starting AI Sales Development Agent Pipeline...")

    # --- 1. Get User Inputs ---
    event_name = input("🔍 Enter the event/industry to search for (e.g., ISA2025, digital signage companies): ").strip()
    while not event_name:
        print("Event/industry cannot be empty.")
        event_name = input("🔍 Enter the event/industry to search for: ").strip()

    num_leads_str = input("🎯 How many leads do you want to search for? (Default: 10): ").strip()
    try:
        num_leads = int(num_leads_str)
        if num_leads <= 0:
            logger.warning("Number of leads must be a positive integer. Defaulting to 5.")
            num_leads = 5
    except ValueError:
        logger.warning(f"Invalid input '{num_leads_str}' for number of leads. Defaulting to 5.")
        num_leads = 5

    user_name_for_signature_input = input("👤 Enter your name for the email signature (e.g., John Doe): ").strip()
    user_company_for_signature_input = input("🏢 Enter your company name for the signature (e.g., YourCompany Inc.): ").strip()
    
    # Provide defaults if user leaves signature fields empty
    user_name = user_name_for_signature_input if user_name_for_signature_input else "Your Name"
    user_company = user_company_for_signature_input if user_company_for_signature_input else "Your Company"
    
    if not user_name_for_signature_input: logger.info("Defaulting signature name to 'Your Name'.")
    if not user_company_for_signature_input: logger.info("Defaulting signature company to 'Your Company'.")

    # This is the full signature string
    user_full_signature = f"\n\nBest regards,\n{user_name}\n{user_company}"
    # This is just the user's name, for potential use in the LLM prompt context
    user_name_context = user_name 
    
    logger.info(f"Using signature: {user_full_signature.replace(chr(10), ' ')}")

    # --- 2. Search for Leads ---
    logger.info(f"Starting search for {num_leads} leads for '{event_name}'...")
    found_leads = search_leads(event_name, num_leads) 

    if not found_leads:
        logger.warning("No leads were found in the search phase. Exiting pipeline.")
        return

    logger.info(f"Search phase completed. Found {len(found_leads)} potential leads.")

    # --- 3. Enrich Leads and Generate Outreach ---
    enriched_leads_data_with_outreach = None
    if found_leads: 
        logger.info(f"Proceeding to enrich {len(found_leads)} found leads and generate outreach messages...")
        # Corrected call to enrich_leads:
        enriched_leads_data_with_outreach = enrich_leads(
            leads=found_leads, 
            user_signature=user_full_signature, # Pass the full signature string
            user_name_for_signature=user_name_context # Pass just the user's name
        )
        if not enriched_leads_data_with_outreach:
            logger.warning("Enrichment and outreach generation resulted in no leads.")
    else:
        logger.info("No leads were found in the search phase to enrich.")


    # --- 4. Display Sample of Enriched Data in Terminal ---
    if enriched_leads_data_with_outreach:
        logger.info("\n--- Sample of Enriched Leads (includes outreach message if generated) ---")
        df_for_terminal = pd.DataFrame(enriched_leads_data_with_outreach)
        
        original_display_width = pd.get_option('display.width')
        original_display_max_colwidth = pd.get_option('display.max_colwidth')
        original_display_max_rows = pd.get_option('display.max_rows')
        original_display_expand_frame_repr = pd.get_option('display.expand_frame_repr')

        pd.set_option('display.max_rows', 10)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 200) 
        pd.set_option('display.max_colwidth', 70)

        try:
            print(df_for_terminal.head(3).to_string(index=False))
        except Exception as e:
            logger.error(f"Error printing DataFrame head: {e}. Printing basic head.")
            print(df_for_terminal.head(3))

        pd.set_option('display.width', original_display_width)
        pd.set_option('display.max_colwidth', original_display_max_colwidth)
        pd.set_option('display.max_rows', original_display_max_rows)
        pd.set_option('display.expand_frame_repr', original_display_expand_frame_repr)
        
        logger.info("---------------------------------------------------------------------\n")
    else:
        logger.info("No enriched leads to display in terminal.")

    # --- 5. Finalize Leads ---
    if enriched_leads_data_with_outreach: 
        logger.info(f"Finalizing data...")
        finalize() 
    else:
        logger.info("No data to finalize as enrichment step yielded no results.")

    logger.info("🎉 Pipeline execution finished!")
    logger.info("Run `streamlit run app.py` to view the dashboard.")

if __name__ == "__main__":
    if not os.path.exists("db"):
        os.makedirs("db")
        logger.info("Created 'db' directory.")
    main()

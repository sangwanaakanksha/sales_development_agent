# run.py

import os
import pandas as pd
from utils.search import search_leads
from utils.enrichment import enrich_leads # This function now expects 'user_signature'
from utils.finalize import finalize

def main():
    event_name = input("🔍 Enter the event/industry to search for (e.g. ISA2025): ")
    num_leads_str = input("How many leads do you want to search? ")

    # ---- ADD THIS SECTION TO GET USER SIGNATURE ----
    user_name_for_signature = input("👤 Enter your name for the email signature (e.g., John Doe): ").strip()
    user_company_for_signature = input("🏢 Enter your company name for the signature (e.g., YourCompany Inc.): ").strip()
    
    # Ensure there's a default if user enters nothing
    if not user_name_for_signature:
        user_name_for_signature = "Your Name" # Default name
    if not user_company_for_signature:
        user_company_for_signature = "Your Company" # Default company

    user_signature = f"\n\nBest regards,\n{user_name_for_signature}\n{user_company_for_signature}"
    # ---- END OF NEW SECTION ----

    try:
        num_leads = int(num_leads_str)
        if num_leads <= 0:
            print("Number of leads must be a positive integer. Defaulting to 10.")
            num_leads = 10
    except ValueError:
        print("Invalid input for number of leads. Defaulting to 10.")
        num_leads = 10
    
    print(f"Starting search for {num_leads} leads for event '{event_name}'...")
    found_leads = search_leads(event_name, num_leads)

    enriched_leads_data_with_outreach = None
    if found_leads:
        print(f"Proceeding to enrich {len(found_leads)} found leads and generate outreach...")
        
        # Pass 'user_signature' as the second argument
        enriched_leads_data_with_outreach = enrich_leads(found_leads, user_signature) 
       
    else:
        print("No leads found to enrich.")

    if enriched_leads_data_with_outreach:
        print("\n--- Sample of Enriched Leads (with Outreach) ---")
        df_for_terminal = pd.DataFrame(enriched_leads_data_with_outreach)

        # Store original pandas display options
        original_display_width = pd.get_option('display.width')
        original_display_max_colwidth = pd.get_option('display.max_colwidth')
        original_display_max_rows = pd.get_option('display.max_rows')
        original_display_expand_frame_repr = pd.get_option('display.expand_frame_repr')

        pd.set_option('display.width', 200)  # Adjust as needed for your terminal width
        pd.set_option('display.max_colwidth', 70) # Max characters per column before trying to wrap/truncate
        pd.set_option('display.max_rows', 10)     # Show more rows if desired
        pd.set_option('display.expand_frame_repr', True) # Allow display to expand horizontally

        print(df_for_terminal.head(3).to_string(index=False)) # Use to_string for better control

        # Reset display options
        pd.set_option('display.width', original_display_width)
        pd.set_option('display.max_colwidth', original_display_max_colwidth)
        pd.set_option('display.max_rows', original_display_max_rows)
        pd.set_option('display.expand_frame_repr', original_display_expand_frame_repr)

        print("------------------------------------------------------------\n")
        
    if enriched_leads_data_with_outreach:
        print(f"Finalizing data...")
        # finalize() should read from 'db/enriched.csv', which was saved by enrich_leads
        finalize() 
    else:
        print("No data to finalize.")

    print("🎉 Done! Run `streamlit run app.py` to view the dashboard.")

if __name__ == "__main__":
    main()
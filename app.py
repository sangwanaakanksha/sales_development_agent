# app.py

import streamlit as st
import pandas as pd
import os

# --- Page Configuration (Set this first) ---
st.set_page_config(
    page_title="AI Sales Development Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Function for Styling (Optional) ---
def local_css(file_name):
    """Loads a local CSS file."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file '{file_name}' not found. Using default styles.")

# Apply custom CSS if you have a styles.css file
# local_css("styles.css") # Create a 'styles.css' file in the same directory for custom styles

# --- Main Application ---
def run_dashboard():
    """
    Main function to run the Streamlit dashboard.
    """
    st.title("📊 AI Sales Development Dashboard")
    st.markdown("Review, filter, and manage your AI-generated sales leads and outreach suggestions.")

    # --- Load Data ---
    file_path = "db/master_outreach.csv" # This file is the output of finalize.py

    if not os.path.exists(file_path):
        st.error(f"🚨 Data file not found at `{file_path}`. Please run the main pipeline (`python run.py`) first to generate the data.")
        st.image("https://placehold.co/600x300/FFF/CCC?text=No+Data+Found!\\nPlease+run+pipeline.", caption="Data file missing")
        st.stop()

    try:
        df_original = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        st.error(f"The data file at `{file_path}` is empty. No leads to display.")
        st.image("https://placehold.co/600x300/FFF/CCC?text=Data+File+is+Empty", caption="Empty data file")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred while loading the data file: {e}")
        st.stop()

    if df_original.empty:
        st.info("The sales data file is empty. No leads to display.")
        st.stop()

    df = df_original.copy() # Work with a copy

    # --- Column Renaming and Preparation ---
    # Keys: Exact column names from your master_outreach.csv
    # Values: User-friendly names for the dashboard
    columns_to_rename = {
        "name": "Company Name",
        "company_website": "Website",
        "mapyourshow_detail_url": "Event Profile",
        "description": "Company Description",
        "location": "Location",
        "phone": "Phone",
        "email": "Email",
        "linkedin_company_page": "LinkedIn (Scraped)", # From initial website scrape
        "linkedin_company_page_serpapi": "LinkedIn (SerpApi)", # From SerpApi enrichment
        "booth_number": "Booth #",
        "raw_contacts_text": "Raw Contacts Info",
        "size": "Company Size",
        "revenue": "Est. Revenue",
        "industry": "Industry",
        "qualified": "ICP Qualified?",
        "qualification_rationale": "Qualification Rationale",
        "actionable": "Actionable?",
        "outreach_message": "Suggested Outreach",
        "Status": "Lead Status" # Column name from finalize.py
    }

    # Rename only columns that actually exist in the DataFrame
    actual_csv_columns = df.columns.tolist()
    rename_map = {}
    for original_name, display_name in columns_to_rename.items():
        if original_name in actual_csv_columns:
            rename_map[original_name] = display_name
        # else:
            # st.sidebar.warning(f"Column '{original_name}' not found in CSV, cannot rename to '{display_name}'.") # Optional warning

    df.rename(columns=rename_map, inplace=True)

    # --- Define Column Order and Selection for Display ---
    # These should be the RENAMED column names (the values from columns_to_rename)
    priority_display_columns = [
        "Company Name", "Lead Status", "ICP Qualified?", "Actionable?", "Suggested Outreach", "Qualification Rationale"
    ]
    contact_info_columns = [
        "Website", "LinkedIn (SerpApi)", "LinkedIn (Scraped)", "Event Profile", "Phone", "Email"
    ]
    additional_info_columns = [
        "Company Description", "Location", "Booth #", "Raw Contacts Info",
        "Company Size", "Est. Revenue", "Industry"
    ]
    
    # Combine and ensure no duplicates, maintaining order
    ordered_columns = priority_display_columns + \
                      [col for col in contact_info_columns if col not in priority_display_columns] + \
                      [col for col in additional_info_columns if col not in priority_display_columns and col not in contact_info_columns]
    
    # Filter this list to only include columns that actually exist in the DataFrame AFTER renaming
    final_display_columns = [col for col in ordered_columns if col in df.columns]


    # --- Sidebar for Filters and Actions ---
    st.sidebar.header("🔎 Filters & Actions")

    df_filtered = df.copy() # Start filtering from the (renamed) DataFrame

    # Filter by Status
    if "Lead Status" in df_filtered.columns:
        unique_statuses = sorted(df_filtered["Lead Status"].dropna().unique().tolist())
        if not unique_statuses:
            st.sidebar.info("No statuses available for filtering.")
        else:
            # Default to 'actionable' and 'qualified' if they exist
            default_selection = [s for s in ["actionable", "qualified"] if s in unique_statuses]
            if not default_selection and unique_statuses: # If preferred defaults not found, select first available
                 default_selection = [unique_statuses[0]] if unique_statuses else []


            selected_statuses = st.sidebar.multiselect(
                "Filter by Lead Status:",
                options=unique_statuses,
                default=default_selection
            )
            if selected_statuses: # Only filter if statuses are actually selected by the user
                df_filtered = df_filtered[df_filtered["Lead Status"].isin(selected_statuses)]
    else:
        st.sidebar.warning("'Lead Status' column not found. Cannot filter by status.")

    # --- Main Dashboard Display ---
    st.subheader("🚀 Lead Intelligence Dashboard")

    if not df_filtered.empty:
        # Column configurations for st.dataframe for better display
        column_config = {}

        # Configure text columns for wrapping (width can be 'small', 'medium', 'large')
        text_wrap_config = {
            "Suggested Outreach": "large",
            "Company Description": "medium",
            "Qualification Rationale": "medium",
            "Raw Contacts Info": "medium",
            "Location": "small"
        }
        for col_name, width_setting in text_wrap_config.items():
            if col_name in df_filtered.columns:
                column_config[col_name] = st.column_config.TextColumn(
                    label=col_name,
                    width=width_setting,
                    help=f"Details for {col_name.lower()}"
                )
        
        # Configure link columns
        link_columns_map = {
            "Website": "Visit 🔗",
            "Event Profile": "Event Page 🔗",
            "LinkedIn (Scraped)": "LI Scraped 🔗",
            "LinkedIn (SerpApi)": "LI SerpApi 🔗"
        }
        for col_name, display_text in link_columns_map.items():
            if col_name in df_filtered.columns:
                column_config[col_name] = st.column_config.LinkColumn(
                    label=col_name,
                    display_text=display_text,
                    help=f"Click to open {col_name}"
                )
        
        st.dataframe(
            df_filtered[final_display_columns], # Use the filtered list of columns that actually exist
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            height=(len(df_filtered) + 1) * 35 + 3 # Dynamically adjust height, or set fixed e.g. 600
        )
    else:
        st.info("No leads match the current filter criteria or no data available in the file.")

    # --- Sidebar: Download and Stats ---
    st.sidebar.markdown("---") # Divider

    if not df_filtered.empty:
        csv_export = df_filtered.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="📥 Download Filtered Leads (CSV)",
            data=csv_export,
            file_name="filtered_sales_leads.csv",
            mime="text/csv",
            key="download_csv_button"
        )
    else:
        st.sidebar.info("No data to download based on current filters.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Summary Statistics")
    
    st.sidebar.metric("Total Leads in File", len(df)) # Total from original loaded df
    
    if "Lead Status" in df_filtered.columns: # Check if 'Lead Status' column exists
        st.sidebar.metric("Leads Displayed (Filtered)", len(df_filtered))
        if not df_filtered.empty:
            st.sidebar.write("Filtered Leads by Status:")
            status_counts_filtered = df_filtered["Lead Status"].value_counts()
            st.sidebar.dataframe(status_counts_filtered, use_container_width=True) # Display as a small table
    else: # If 'Lead Status' column doesn't exist
         st.sidebar.metric("Leads Displayed", len(df_filtered)) # Show total displayed if status not available for breakdown


if __name__ == "__main__":
    run_dashboard()

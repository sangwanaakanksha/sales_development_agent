# app.py

import streamlit as st
import pandas as pd
import os

# Page Configuration (set this first)
st.set_page_config(page_title="AI SDR Dashboard", layout="wide")

st.title("📊 AI Sales Development Dashboard")

# Load the final outreach file
FILE_PATH = "db/master_outreach.csv"
if not os.path.exists(FILE_PATH):
    st.warning(f"Sales data file not found at {FILE_PATH}. Please run the main pipeline first: `python run.py`")
    st.stop() # Stop execution if file doesn't exist

try:
    df = pd.read_csv(FILE_PATH)
except pd.errors.EmptyDataError:
    st.error(f"The file {FILE_PATH} is empty. No leads to display.")
    st.stop()
except Exception as e:
    st.error(f"Error loading {FILE_PATH}: {e}")
    st.stop()

if df.empty:
    st.info("The sales data file is empty. No leads to display.")
    st.stop()

# --- Column Renaming ---
# Keys are original names from CSV, values are display names
columns_rename = {
    "name": "Company",
    "company_website": "Website URL", # Assuming this is the actual col name in CSV for website
    "mapyourshow_detail_url": "Event Profile URL", # If you want to show this
    "description": "Company Description",
    "location": "Location",
    "size": "Company Size",
    "revenue": "Est. Revenue",
    "industry": "Industry",
    "qualified": "ICP Qualified",
    "actionable": "Actionable Lead",
    "outreach_message": "Suggested Outreach", # Renaming for display
    "Status": "Status", # If 'Status' is already the name, this won't change it but ensures consistency
    "phone": "Phone",
    "email": "Email",
    "linkedin_company_page": "LinkedIn Page",
    "booth_number": "Booth #"
}
# Only rename columns that actually exist in the DataFrame to avoid errors
existing_columns_to_rename = {k: v for k, v in columns_rename.items() if k in df.columns}
df.rename(columns=existing_columns_to_rename, inplace=True)

# --- Define columns for display and their order ---
# Prioritize based on importance and data availability
# Check your CSV for the exact column names after the renaming step above
base_display_columns = [
    "Company", "Status", "ICP Qualified", "Actionable Lead", "Suggested Outreach"
]
detailed_info_columns = [
    "Company Description", "Location", "Website URL", "Event Profile URL",
    "LinkedIn Page", "Phone", "Email", "Booth #",
    "Company Size", "Est. Revenue", "Industry" # These might be sparse
]

# Filter out columns that don't exist in the df from desired lists
final_display_columns = [col for col in base_display_columns if col in df.columns]
final_display_columns.extend([col for col in detailed_info_columns if col in df.columns and col not in final_display_columns])

# --- Sidebar for Filters ---
st.sidebar.header("Lead Filters")

# Filter by status
if "Status" in df.columns:
    statuses_in_data = sorted(df["Status"].dropna().unique().tolist())
    if not statuses_in_data:
        st.sidebar.warning("No statuses available for filtering.")
        selected_statuses = []
    else:
        default_statuses = [s for s in ["actionable", "qualified"] if s in statuses_in_data]
        selected_statuses = st.sidebar.multiselect(
            "Filter by Lead Status:",
            options=statuses_in_data,
            default=default_statuses
        )
    if selected_statuses:
        df_filtered = df[df["Status"].isin(selected_statuses)]
    else:
        df_filtered = df # Show all if no status selected or status column is problematic
else:
    st.sidebar.warning("'Status' column not found. Displaying all leads.")
    df_filtered = df

# --- Main Dashboard Display ---
st.subheader("Sales Outreach Intelligence")

if not df_filtered.empty:
    # To make text in cells wrap and control column width/font, we can use st.data_editor
    # or inject some CSS. For simplicity, st.dataframe has limited direct styling.
    # For medium font and better visibility, Streamlit's default theme is usually quite good.
    # We can ensure text wrapping for outreach messages by setting column widths.
    
    # Create a column configuration dictionary for st.data_editor or st.dataframe
    column_config = {}
    if "Suggested Outreach" in final_display_columns:
        column_config["Suggested Outreach"] = st.column_config.TextColumn(
            "Suggested Outreach",
            help="AI-generated outreach message suggestion.",
            # width="large" # You can try 'small', 'medium', 'large' or specific pixel width
        )
    if "Company Description" in final_display_columns:
         column_config["Company Description"] = st.column_config.TextColumn(
            "Company Description",
            # width="medium"
        )
    if "Website URL" in final_display_columns:
        column_config["Website URL"] = st.column_config.LinkColumn(
            "Website URL",
            display_text="Visit 🔗" # Or use a regex to display the domain
        )
    if "Event Profile URL" in final_display_columns:
        column_config["Event Profile URL"] = st.column_config.LinkColumn(
            "Event Profile URL",
            display_text="Event Page 🔗"
        )
    if "LinkedIn Page" in final_display_columns:
        column_config["LinkedIn Page"] = st.column_config.LinkColumn(
            "LinkedIn Page",
            display_text="LinkedIn 🔗"
        )


    st.dataframe(
        df_filtered[final_display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
else:
    st.info("No leads match the current filter criteria.")

# --- Sidebar for Download and Stats ---
st.sidebar.markdown("---") # Divider

if not df_filtered.empty:
    st.sidebar.download_button(
        label="Download Filtered Leads (CSV)",
        data=df_filtered.to_csv(index=False).encode('utf-8'),
        file_name="filtered_leads.csv",
        mime="text/csv"
    )
else:
    st.sidebar.info("No data to download based on current filters.")

st.sidebar.markdown("---")
st.sidebar.subheader("Summary Statistics")
if not df.empty: # Use original df for total stats before filtering for some context
    st.sidebar.metric("Total Leads in File", len(df))
if not df_filtered.empty:
    st.sidebar.metric("Leads Displayed (Filtered)", len(df_filtered))
    if "Status" in df_filtered.columns:
        st.sidebar.write("Leads by Status (Filtered):")
        status_counts = df_filtered["Status"].value_counts()
        st.sidebar.dataframe(status_counts) # Display as a small table
else:
     st.sidebar.metric("Leads Displayed (Filtered)", 0)
# streamlit_app.py
import app_3 as st
import pandas as pd
import config # To get file paths
import utils # For load_from_csv

st.set_page_config(layout="wide", page_title="DuPont Lead Gen Dashboard")

st.title("DuPont Tedlar - Graphics & Signage Lead Dashboard")

# --- Load Data ---
@st.cache_data(ttl=60) # Cache for 1 minute
def load_data():
    qualified_df = utils.load_from_csv(config.DATABASE_FILE_QUALIFIED)
    actionable_df = utils.load_from_csv(config.DATABASE_FILE_ACTIONABLE)
    initial_df = utils.load_from_csv(config.DATABASE_FILE_INITIAL) # For stats
    enriched_df = utils.load_from_csv(config.DATABASE_FILE_ENRICHED) # For stats
    return initial_df, enriched_df, qualified_df, actionable_df

initial_df, enriched_df, qualified_df, actionable_df = load_data()

# --- Display Stats ---
st.header("Process Summary")
if initial_df is not None and not initial_df.empty:
    st.metric("Initial Leads Scraped", len(initial_df))
else:
    st.metric("Initial Leads Scraped", 0)

if enriched_df is not None and not enriched_df.empty:
     st.metric("Leads Enriched", len(enriched_df))
else:
    st.metric("Leads Enriched", 0)

if qualified_df is not None and not qualified_df.empty:
    st.metric("Total Leads Processed for Qualification", len(qualified_df))
    status_counts = qualified_df['status'].value_counts().to_dict()
    cols_metrics = st.columns(len(status_counts))
    i = 0
    for status, count in status_counts.items():
        with cols_metrics[i]:
            st.metric(f"{status.replace('_', ' ').title()} Leads", count)
        i += 1
else:
    st.metric("Total Leads Processed for Qualification", 0)


st.divider()

# --- Display Actionable Leads ---
st.header("🚀 Actionable Leads with Outreach Messages")
if actionable_df is not None and not actionable_df.empty:
    st.info(f"Found {len(actionable_df)} actionable leads.")
    # Select columns to display
    display_cols_actionable = ['company_name', 'company_website', 'official_website_serp', 'description', 'hq_location', 'outreach_message']
    actionable_display = actionable_df[[col for col in display_cols_actionable if col in actionable_df.columns]]
    st.dataframe(actionable_display, height=400, use_container_width=True)

    st.subheader("Download Actionable Leads")
    csv_actionable = actionable_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Actionable Leads as CSV",
        data=csv_actionable,
        file_name='actionable_leads_dupont.csv',
        mime='text/csv',
    )
else:
    st.warning("No actionable leads found or data file is empty.")

st.divider()

# --- Display All Qualified & Other Leads ---
st.header("📋 All Processed Leads (by status)")
if qualified_df is not None and not qualified_df.empty:
    # Filter by status
    status_options = ["all"] + sorted(list(qualified_df['status'].unique()))
    selected_status = st.selectbox("Filter by Status:", options=status_options, index=0)

    if selected_status == "all":
        filtered_df = qualified_df
    else:
        filtered_df = qualified_df[qualified_df['status'] == selected_status]

    st.info(f"Displaying {len(filtered_df)} leads for status: '{selected_status}'")
    display_cols_qualified = ['company_name', 'status', 'company_website', 'official_website_serp', 'description', 'revenue', 'employees', 'hq_location', 'source_url']
    qualified_display = filtered_df[[col for col in display_cols_qualified if col in filtered_df.columns]]
    st.dataframe(qualified_display, height=400, use_container_width=True)

    st.subheader("Download All Processed Leads")
    csv_qualified = qualified_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download All Processed Leads as CSV",
        data=csv_qualified,
        file_name='all_processed_leads_dupont.csv',
        mime='text/csv',
    )
else:
    st.warning("No qualified leads data found or file is empty.")

st.sidebar.button("Refresh Data")
st.sidebar.markdown("---")
st.sidebar.markdown("Built with AutoGen, Playwright, SerpAPI, OpenAI & Streamlit.")

logger_s = utils.logging.getLogger("StreamlitApp") # For messages specific to streamlit
logger_s.info("Streamlit dashboard loaded/reloaded.")
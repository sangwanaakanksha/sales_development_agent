import streamlit as st
import pandas as pd
import os

from utils.outreach import generate_outreach
from utils.judge import judge_message

# Page config
st.set_page_config(layout="wide", page_title="Sales Outreach UI")

# Custom CSS for tags and fonts
st.markdown(
    """
    <style>
    .title {font-size:32px; font-weight:bold; margin-bottom:20px;}
    .subheader {font-size:20px; font-weight:500; margin-top:10px; margin-bottom:10px;}
    .tag {display:inline-block; background-color:#E0F7FA; color:#00796B; padding:4px 8px; border-radius:4px; font-size:12px; margin-right:4px;}
    .send-btn {background-color:#00796B; color:white; font-weight:bold; width:100%; padding:8px;}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="title">Sales Outreach Assistant</div>', unsafe_allow_html=True)

@st.cache_data
def load_data():
    enriched_path = os.path.join("db", "enriched.csv")
    df_e = pd.read_csv(enriched_path) if os.path.exists(enriched_path) else pd.DataFrame()
    return df_e

df_enriched = load_data()

# Create placeholders for message data
if 'message_data' not in st.session_state:
    st.session_state['message_data'] = None

col1, col2, col3 = st.columns([1, 2, 2])

# ---- LEFT PANEL ----
with col1:
    st.markdown('<div class="subheader">Filters & Input</div>', unsafe_allow_html=True)
    # Filter sliders
    if not df_enriched.empty:
        # Revenue filter
        if 'revenue' in df_enriched:
            min_r, max_r = int(df_enriched['revenue'].min()), int(df_enriched['revenue'].max())
            rmin, rmax = st.slider("Revenue range", min_r, max_r, (min_r, max_r))
        else:
            rmin = rmax = None
        # Employee size filter
        if 'size' in df_enriched:
            min_s, max_s = int(df_enriched['size'].min()), int(df_enriched['size'].max())
            smin, smax = st.slider("Employee size", min_s, max_s, (min_s, max_s))
        else:
            smin = smax = None
        # Apply filters
        df_filtered = df_enriched.copy()
        if rmin is not None:
            df_filtered = df_filtered[(df_filtered['revenue']>=rmin)&(df_filtered['revenue']<=rmax)]
        if smin is not None:
            df_filtered = df_filtered[(df_filtered['size']>=smin)&(df_filtered['size']<=smax)]
    else:
        df_filtered = pd.DataFrame()

    st.markdown("<br><div style='text-align:center;'>— OR —</div><br>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload PDF for extraction", type=["pdf"])
    if uploaded_file:
        st.info("Upload detected. Run backend to process and refresh leads.")

    st.markdown("<br>", unsafe_allow_html=True)
    # User details
    user_name = st.text_input("Your Name", value="Sales Rep")
    org_name = st.text_input("Your Organization", value="DuPont Tedlar")

# ---- CENTER PANEL ----
with col2:
    st.markdown('<div class="subheader">Actionable Leads</div>', unsafe_allow_html=True)
    # Only actionable leads
    if not df_filtered.empty:
        df_action = df_filtered[df_filtered['actionable']=='Yes']
    else:
        df_action = pd.DataFrame()

    if not df_action.empty:
        options = []
        for idx, row in df_action.iterrows():
            tags = []
            if row['qualified']=='Yes': tags.append('Qualified')
            if row['actionable']=='Yes': tags.append('Actionable')
            display = "".join([f"<span class='tag'>{t}</span>" for t in tags]) + f" {row['name']}"
            options.append((display, idx))
        # Single-select dropdown
        sel_display, sel_idx = st.selectbox("Select a lead:", options, format_func=lambda x: x[0])
        selected_lead = df_action.loc[sel_idx]
    else:
        st.write("No actionable leads. Adjust filters or upload data.")
        selected_lead = None

# ---- RIGHT PANEL ----
with col3:
    st.markdown('<div class="subheader">Outreach Message Composer</div>', unsafe_allow_html=True)
    sender_email = st.text_input("Your Email Address", value="user@company.com")

    if selected_lead is not None:
        # Generate button
        if st.button("Generate Outreach", key='gen'):
            msg_data = generate_outreach(selected_lead.to_dict())
            # Validate
            issues = judge_message(msg_data['revised'])
            st.session_state['message_data'] = msg_data
            st.session_state['issues'] = issues
        # Display message if available
        if st.session_state['message_data']:
            data = st.session_state['message_data']['revised']
            st.markdown(f"**Medium:** {data.get('medium','')}" )
            subj = st.text_input("Subject", data.get('subject',''))
            body = st.text_area("Body", data.get('body',''), height=300)
            st.markdown(f"**Review:** {st.session_state.get('issues','OK')}")
            # Send button
            if st.button("Send Outreach", key='send'):
                st.success(f"Outreach sent to {selected_lead['name']} via {data.get('medium')} from {sender_email}")
    else:
        st.write("Select one actionable lead to begin.")

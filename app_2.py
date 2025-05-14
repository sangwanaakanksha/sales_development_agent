import app_3 as st
import pandas as pd
import os
import plotly.express as px

from utils.event_research import discover_events

# Page config
st.set_page_config(layout="wide", page_title="Leads Dashboard")

@st.cache_data
def load_all():
    d = {}
    for name in ['input', 'search', 'enriched', 'final_outreach']:
        path = os.path.join('db', f'{name}.csv')
        d[name] = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    return d

data = load_all()

# --- Dashboard Header ---
st.title("📊 Lead Generation Dashboard")

# --- Metrics Row ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Raw Leads", len(data['input']))
col2.metric("Searched", len(data['search']))
col3.metric("Qualified", len(data['enriched'][data['enriched']['qualified']=='Yes']))
col4.metric("Outreach Sent", len(data['final_outreach']))

st.markdown("---")

# --- Funnel Chart ---
funnel_df = pd.DataFrame({
    'Stage': ['Input','Search','Qualified','Outreach'],
    'Count': [len(data['input']), len(data['search']),
              len(data['enriched'][data['enriched']['qualified']=='Yes']),
              len(data['final_outreach'])]
})
fig = px.funnel(funnel_df, x='Count', y='Stage')
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- Qualified Leads Filter & List ---
st.subheader("Filter & Select Actionable Leads")
if not data['enriched'].empty:
    # Filter only actionable leads
    df_action = data['enriched'][data['enriched']['actionable']=='Yes'].copy()
    st.write(f"Total actionable leads: {len(df_action)}")
    # Add summary columns
    df_display = df_action.assign(
        Company=df_action['name'],
        Industry=df_action.get('industry', ''),
        Size=df_action.get('size', ''),
        Revenue=df_action.get('revenue', ''),
        Source=df_action.get('source', ''),
        Website=df_action.get('company_website', ''),
        Contact=df_action['decision_makers'].apply(lambda d: d[0].get('name', '') if isinstance(d, list) and d else '')
    )
    # Show table
    st.dataframe(
        df_display[['Company','Industry','Size','Revenue','Source','Website','Contact']],
        height=200
    )
    # Selection dropdown
    lead_names = df_action['name'].tolist()
    selected_lead = st.selectbox("Select a lead for outreach:", lead_names)
else:
    st.write("No actionable leads available.")

# st.markdown("---")("---")("---")

# --- Outreach Message Preview ---
st.subheader("Outreach Message Preview")
if 'final_outreach' in data and not data['final_outreach'].empty and 'selected_lead' in locals() and selected_lead:
    df_final = data['final_outreach']
    df_msg = df_final[df_final['lead_name']==selected_lead]
    if not df_msg.empty:
        msg = df_msg.iloc[-1]
        st.markdown(f"**Medium:** {msg.get('medium','')}")
        st.markdown("**Message:**")
        st.text_area("", msg.get('message',''), height=200)
    else:
        st.write("No outreach message found for this lead. Generate outreach via main app.")
else:
    st.write("Select an actionable lead to preview its outreach message.")

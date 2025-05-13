# main_backend.py

import os
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import argparse
from datetime import datetime

from utils.input_processing import process_input_file
from utils.search import search_leads
from utils.enrichment import enrich_leads
from utils.outreach import generate_outreach
from utils.judge import judge_message
from langchain.agents import initialize_agent, Tool
from langchain_community.llms import OpenAI
from langchain.memory import ConversationBufferMemory

# Interactive LangChain agent (if needed)
llm_agent = OpenAI(temperature=0.2)
memory_agent = ConversationBufferMemory(memory_key="chat_history")

tools = [
    Tool(name="Input Processor", func=process_input_file, description="Extract leads from PDF"),
    Tool(name="Search Agent",   func=search_leads,       description="Search leads by keyword/event"),
    Tool(name="Enrichment",     func=enrich_leads,       description="Enrich and qualify leads"),
    Tool(name="Outreach",       func=generate_outreach,  description="Draft and revise outreach messages"),
    Tool(name="Judge",          func=judge_message,      description="Validate outreach content"),
]

agent = initialize_agent(
    tools, llm_agent,
    agent="zero-shot-react-description",
    memory=memory_agent,
    verbose=True
)

def run_agent_chain(user_input: str):
    """Run the LangChain agent on a user input string."""
    return agent.run(user_input)


def pipeline(file: str = None,
             keyword: str = None,
             user_name: str = None,
             org_name: str = None):
    """
    End-to-end pipeline:
      1) Input → raw company names
      2) Search → detailed leads
      3) Enrich → qualified & actionable
      4) Outreach + Judge → messaging
      5) Save final and master DB with comprehensive lead info
    """
    if not user_name or not org_name:
        raise ValueError("Both --user_name and --org_name must be provided.")

    # Step 1 & 2: Gather leads with source tags
    all_leads = []
    if file:
        mapping = process_input_file(file)  # {event_name: [company names]}
        for source, names in mapping.items():
            for name in names:
                leads = search_leads(name)
                for lead in leads:
                    lead["source"] = source
                    all_leads.append(lead)
    elif keyword:
        leads = search_leads(keyword)
        for lead in leads:
            lead["source"] = keyword
        all_leads = leads
    else:
        raise ValueError("Either --file or --keyword must be provided.")

    # Step 3: Enrichment
    enriched = enrich_leads(all_leads)

    # Filter actionable leads
    actionable = [lead for lead in enriched if lead.get("actionable") == "Yes"]

    # Prepare master DB
    db_dir = "db"
    os.makedirs(db_dir, exist_ok=True)
    master_path = os.path.join(db_dir, "master_outreach.csv")
    master_cols = [
        "timestamp", "lead_name", "company_description", "company_website", "source",
        "contact1_name", "contact1_profile", "contact1_medium",
        "contact2_name", "contact2_profile", "contact2_medium",
        "company_email", "medium", "message", "user_name", "org_name"
    ]
    if os.path.exists(master_path):
        master_df = pd.read_csv(master_path)
    else:
        master_df = pd.DataFrame(columns=master_cols)

    final_records = []

    # Step 4: Outreach & Judge
    for lead in actionable:
        outcome = generate_outreach(lead, user_name, org_name)
        revised = outcome.get("revised", {})
        medium = revised.get("medium", "email")
        message = revised.get("body", "")

        # Extract contacts if available
        contacts = lead.get("decision_makers", [])
        c1 = contacts[0] if len(contacts) > 0 else {}
        c2 = contacts[1] if len(contacts) > 1 else {}

        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "lead_name": lead.get("name"),
            "company_description": lead.get("description", ""),
            "company_website": lead.get("company_website", ""),
            "source": lead.get("source", ""),
            "contact1_name": c1.get("name", ""),
            "contact1_profile": c1.get("profile", ""),
            "contact1_medium": "linkedin" if c1.get("profile","").startswith("http") else "",  # assume
            "contact2_name": c2.get("name", ""),
            "contact2_profile": c2.get("profile", ""),
            "contact2_medium": "linkedin" if c2.get("profile","").startswith("http") else "",
            "company_email": lead.get("company_email", ""),
            "medium": medium,
            "message": message,
            "user_name": user_name,
            "org_name": org_name
        }
        final_records.append(row)

        # Append and dedupe
        master_df = pd.concat([master_df, pd.DataFrame([row])], ignore_index=True)

    # Save Master DB and final outreach
    master_df.drop_duplicates(subset=["lead_name", "message"], inplace=True)
    master_df.to_csv(master_path, index=False)

    final_df = pd.DataFrame(final_records)
    final_path = os.path.join(db_dir, "final_outreach.csv")
    final_df.to_csv(final_path, index=False)

    print(f"Pipeline done: {len(final_records)} messages saved.")
    print(f"Final outreach: {final_path}")
    print(f"Master DB: {master_path}")
    return final_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sales lead agent pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Input PDF for extraction")
    group.add_argument("--keyword", help="Event keyword for search")
    parser.add_argument("--user_name", required=True, help="Your name for personalization")
    parser.add_argument("--org_name", required=True, help="Your organization name")
    args = parser.parse_args()
    pipeline(
        file=args.file,
        keyword=args.keyword,
        user_name=args.user_name,
        org_name=args.org_name
    )

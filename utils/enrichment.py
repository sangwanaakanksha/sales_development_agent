# utils/enrichment.py

from dotenv import load_dotenv
load_dotenv()

import json
from langchain_community.llms import OpenAI
from utils.database import save_stage

# Your ICP description
ICP_DESCRIPTION = """
Specializes in large-format signage, vehicle wraps, and architectural graphics;
Global $8B+ revenue, thousands of employees;
Exhibits at ISA Sign Expo, active in industry associations;
Decision-makers: VPs of Product Development, Directors of Innovation, R&D leaders.
"""

def enrich_leads(leads: list):
    """
    • Classify each lead vs. ICP with an LLM
    • Mark actionable if qualified + has decision-makers
    • Snapshot to db/enriched.csv
    """
    llm = OpenAI(temperature=0)
    enriched = []

    for lead in leads:
        name = lead.get("name", "")
        desc = lead.get("description", "No description available")
        # Build prompt
        prompt = (
            f"Ideal Customer Profile:\n{ICP_DESCRIPTION}\n\n"
            f"Company:\n  Name: {name}\n"
            f"  Description: {desc}\n\n"
            "Respond with only 'Yes' or 'No' if this company matches the ICP."
        )
        resp = llm(prompt)
        qualified = "Yes" if "yes" in resp.lower() else "No"

        actionable = "Yes" if qualified == "Yes" and lead.get("decision_makers") else "No"

        # Update and collect
        lead.update({
            "qualified": qualified,
            "actionable": actionable,
            "description": desc  # ensure description field is present
        })
        enriched.append(lead)

    save_stage(enriched, "enriched")
    return enriched

if __name__ == "__main__":
    # Quick smoke test: load existing search dataset, fill missing descriptions, enrich
    import pandas as pd
    import os

    csv_path = os.path.join("db", "search.csv")
    if not os.path.exists(csv_path):
        print(f"No search.csv found at {csv_path}. Run search stage first.")
    else:
        leads = pd.read_csv(csv_path).to_dict(orient="records")
        # Fill missing descriptions
        for lead in leads:
            if not lead.get("description") or lead["description"] == "nan":
                lead["description"] = "No description available"
        enriched = enrich_leads(leads)
        print(json.dumps(enriched[:5], indent=2))

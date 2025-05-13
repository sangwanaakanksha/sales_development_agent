# utils/outreach.py

from dotenv import load_dotenv
load_dotenv()

import json
from langchain_community.llms import OpenAI
from utils.database import save_stage
from utils.judge import judge_message


def generate_outreach(lead: dict):
    """
    1. Generate an initial outreach message (email or LinkedIn DM).
    2. Use the Judge agent to validate for hallucinations, toxicity, or trailing issues.
    3. If issues are found, prompt the LLM to revise the message to correct them.
    4. Return a dict with 'original', 'revised', and 'issues'.
    5. Snapshot the revised message to db/outreach.csv.
    """
    llm = OpenAI(temperature=0.7)
    dms = lead.get("decision_makers", []) or []

    # Determine contact and medium
    if dms and isinstance(dms[0], dict) and dms[0].get("profile", "").startswith("https://linkedin.com"):
        medium = "linkedin_dm"
        contact = dms[0]["profile"]
        prompt = (
            f"Write a 300-character LinkedIn DM to {contact} at {lead['name']}. "
            "Keep it brief, friendly, and include a call to action for a quick call."
        )
    else:
        medium = "email"
        contact_info = dms[0]['profile'] if dms and isinstance(dms[0], dict) else ""
        prompt = (
            f"Draft a concise outreach email to {lead['name']} (contact: {contact_info}). "
            f"Company description: {lead.get('description', '')}. "
            "Return JSON with keys 'subject' and 'body'."
        )

    # 1) Generate original message
    resp = llm(prompt)
    try:
        original = json.loads(resp)
    except Exception:
        original = {
            "medium": medium,
            "subject": f"Collaboration with {lead['name']}",
            "body": resp
        }
    # Ensure medium in original
    original["medium"] = medium

    # 2) Validate via Judge
    issues = judge_message(original)

    # 3) Revise if issues found
    revised = original
    if issues.strip().upper() != 'OK':
        rev_prompt = (
            "The following outreach message has issues: " + issues +
            " Please revise it to correct any hallucinations, improve closure, "
            "and ensure it ends with a clear call to action. "
            "Respond in JSON with 'subject' and 'body'." +
            "\nOriginal Message:\n" + json.dumps(original)
        )
        rev_resp = llm(rev_prompt)
        try:
            new_msg = json.loads(rev_resp)
            revised = new_msg
        except Exception:
            revised = {"medium": medium, "subject": original.get("subject", ""), "body": rev_resp}
        revised["medium"] = medium

    # 4) Snapshot revised message
    save_stage([revised], "outreach")

    # 5) Return both versions and the judge report
    return {"original": original, "revised": revised, "issues": issues}


if __name__ == "__main__":
    # Quick smoke test for outreach + judge + revision
    import pandas as pd
    import os

    path = os.path.join("db", "enriched.csv")
    if not os.path.exists(path):
        print("Run enrichment stage first. db/enriched.csv not found.")
    else:
        leads = pd.read_csv(path).to_dict(orient="records")
        # Filter actionable only
        actionable = [l for l in leads if l.get("actionable") == "Yes"]
        if not actionable:
            print("No actionable leads to test.")
        else:
            test_lead = actionable[0]
            result = generate_outreach(test_lead)
            print(json.dumps(result, indent=2))

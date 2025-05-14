import pandas as pd
import os

def determine_status(row):
    # Basic qualification logic
    if pd.isna(row.get("Name")) or pd.isna(row.get("Title")):
        return "incomplete"
    elif isinstance(row.get("Outreach Message", ""), str) and len(row["Outreach Message"]) > 30:
        return "actionable"
    elif row.get("Qualified") == True:
        return "qualified"
    else:
        return "skipped"

def finalize():
    enriched_path = "db/enriched.csv"
    output_path = "db/master_outreach.csv"

    if not os.path.exists(enriched_path):
        print("❌ Enriched data not found.")
        return

    df = pd.read_csv(enriched_path)

    # Add 'Status'
    df["Status"] = df.apply(determine_status, axis=1)

    df.to_csv(output_path, index=False)
    print(f"✅ Finalized {len(df)} leads with status. Saved to {output_path}")

if __name__ == "__main__":
    finalize()

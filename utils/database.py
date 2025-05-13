import pandas as pd
import os

def save_stage(data, stage):
    """
    Save a list of dicts to db/<stage>.csv
    """
    os.makedirs("db", exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(f"db/{stage}.csv", index=False)
    print(f"-> Saved {len(df)} rows to db/{stage}.csv")

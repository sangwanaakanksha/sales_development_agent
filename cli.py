import argparse
import os
from main_backend import pipeline
import generate_dashboard

# Fallback sample PDF
SAMPLE_PDF = 'sample_input.pdf'

def main():
    parser = argparse.ArgumentParser(description="AI Sales Development Agent CLI")
    parser.add_argument(
        "--mode", choices=["full_pipeline","scrape_only","enrich_only","dashboard"],
        required=True,
        help="Operation mode: full_pipeline, scrape_only, enrich_only, dashboard"
    )
    parser.add_argument("--input_file", type=str, default=None, help="Path to input PDF")
    parser.add_argument("--keyword", type=str, default="ISA2025", help="Keyword/event for search")
    parser.add_argument("--user_name", type=str, default="Sales Rep", help="Your name for personalization")
    parser.add_argument("--org_name", type=str, default="DuPont Tedlar", help="Your organization name")
    args = parser.parse_args()

    # Determine input file
    input_file = args.input_file or (SAMPLE_PDF if os.path.exists(SAMPLE_PDF) else None)

    if args.mode == "full_pipeline":
        pipeline(
            file=input_file,
            keyword=args.keyword,
            user_name=args.user_name,
            org_name=args.org_name
        )
        print("✅ Full pipeline completed.")

    elif args.mode == "scrape_only":
        from utils.input_processing import process_input_file
        from utils.search import search_leads
        leads = []
        if input_file:
            mapping = process_input_file(input_file)
            for names in mapping.values():
                for name in names:
                    leads.extend(search_leads(name))
        else:
            leads = search_leads(args.keyword)
        print(f"✅ Scrape-only completed: {len(leads)} leads found.")

    elif args.mode == "enrich_only":
        import pandas as pd
        from utils.enrichment import enrich_leads
        path = 'db/search.csv'
        leads = pd.read_csv(path).to_dict(orient='records') if os.path.exists(path) else []
        enriched = enrich_leads(leads)
        print(f"✅ Enrich-only completed: {len(enriched)} leads enriched.")

    elif args.mode == "dashboard":
        generate_dashboard.main()
        print("✅ Dashboard generated: dashboard.html")

if __name__ == '__main__':
    main()

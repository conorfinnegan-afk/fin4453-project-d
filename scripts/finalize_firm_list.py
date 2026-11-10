import os
import requests
import pandas as pd

HEADERS = {"User-Agent": "UF FIN4453 Capstone Team c.finnegan@ufl.edu"}
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def main():
    cand_path = os.path.join(DATA_DIR, "sp500_industrials_candidates.csv")
    if not os.path.exists(cand_path):
        print(f"Error: {cand_path} not found.")
        return

    cands = pd.read_csv(cand_path)
    kept = []
    prefilter_excluded = []

    for _, row in cands.iterrows():
        ticker = row["ticker"]
        cik = str(row["cik"]).zfill(10)
        name = row["name"]
        
        try:
            sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            r = requests.get(sub_url, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            forms = data.get("filings", {}).get("recent", {}).get("form", [])
            dates = data.get("filings", {}).get("recent", {}).get("filingDate", [])
            
            ten_k_dates = [dates[i] for i, f in enumerate(forms) if f == "10-K"]
            oldest_year = int(min(ten_k_dates)[:4]) if ten_k_dates else 2026
            
            if len(ten_k_dates) >= 4 and oldest_year <= 2021:
                print(f"  kept: {ticker} (10-K history back to {oldest_year})")
                kept.append({
                    "ticker": ticker,
                    "cik": cik,
                    "name": name,
                    "fiscal_year_end": row.get("fiscal_year_end", "12-31"),
                    "sample_year": 2025
                })
            else:
                prefilter_excluded.append({
                    "ticker": ticker,
                    "cik": cik,
                    "name": name,
                    "reason": f"Insufficient 10-K history (<4 years or oldest year {oldest_year})"
                })
        except Exception as e:
            prefilter_excluded.append({
                "ticker": ticker,
                "cik": cik,
                "name": name,
                "reason": f"API error checking history: {str(e)}"
            })

    pd.DataFrame(kept).to_csv(os.path.join(DATA_DIR, "firm_list.csv"), index=False)
    pd.DataFrame(prefilter_excluded).to_csv(os.path.join(DATA_DIR, "excluded_firms_prefilter.csv"), index=False)
    print(f"\n{len(kept)} candidates passed mechanical filters, {len(prefilter_excluded)} excluded.")

if __name__ == "__main__":
    main()

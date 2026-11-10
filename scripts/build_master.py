import os
import pandas as pd

DATA_DIR = "data"
FILINGS_DIR = os.path.join(DATA_DIR, "filings")
FIN_DIR = os.path.join(DATA_DIR, "financials")

def main():
    firm_list_path = os.path.join(DATA_DIR, "firm_list.csv")
    if not os.path.exists(firm_list_path):
        print(f"Error: {firm_list_path} not found.")
        return

    firms = pd.read_csv(firm_list_path)
    extraction_log_path = os.path.join(DATA_DIR, "extraction_log.csv")
    extraction_log = pd.read_csv(extraction_log_path).set_index("ticker") if os.path.exists(extraction_log_path) else pd.DataFrame()
    
    master_rows = []
    excluded_rows = []

    # Target forecast year is FY2025; baseline years are FY2022, FY2023, FY2024
    SAMPLE_YEAR = 2025
    required_years = [2022, 2023, 2024, 2025]

    for _, row in firms.iterrows():
        ticker = row["ticker"]
        cik_str = str(row["cik"]).zfill(10)
        name = row["name"]
        
        fin_path = os.path.join(FIN_DIR, f"{ticker}_financials.csv")
        i1_path = os.path.join(FILINGS_DIR, f"{ticker}_item1.txt")
        i7_path = os.path.join(FILINGS_DIR, f"{ticker}_item7.txt")

        # 1. Check filing text validity
        if extraction_log.empty or ticker not in extraction_log.index or extraction_log.loc[ticker, "status"] != "success":
            excluded_rows.append({"ticker": ticker, "name": name, "reason": "Filing extraction failed or 10-K missing"})
            continue
            
        i1_len = extraction_log.loc[ticker, "item1_len"]
        i7_len = extraction_log.loc[ticker, "item7_len"]
        if i1_len < 1000 or i7_len < 1000:
            excluded_rows.append({"ticker": ticker, "name": name, "reason": f"Insufficient section length (Item1: {i1_len}, Item7: {i7_len})"})
            continue

        # 2. Check financial facts completeness
        if not os.path.exists(fin_path):
            excluded_rows.append({"ticker": ticker, "name": name, "reason": "Missing XBRL financials file"})
            continue

        fdf = pd.read_csv(fin_path).set_index("fiscal_year")
        if not all(y in fdf.index for y in required_years):
            excluded_rows.append({"ticker": ticker, "name": name, "reason": "Missing required fiscal years (2022-2025)"})
            continue

        revs = {y: fdf.loc[y, "revenue"] for y in required_years}
        margins = {y: fdf.loc[y, "operating_margin"] for y in required_years}

        if any(pd.isna(revs[y]) or pd.isna(margins[y]) for y in required_years):
            excluded_rows.append({"ticker": ticker, "name": name, "reason": "NaN values present in revenue or margin for 2022-2025"})
            continue

        if revs[2024] == 0:
            excluded_rows.append({"ticker": ticker, "name": name, "reason": "Zero revenue in FY2024 divisor"})
            continue

        # Ground truth FY2025 realized growth and margin
        actual_rev_growth = (revs[2025] - revs[2024]) / revs[2024]
        actual_margin = margins[2025]
        backlog_flag = bool(extraction_log.loc[ticker, "backlog"])

        master_rows.append({
            "ticker": ticker,
            "cik": cik_str,
            "name": name,
            "sample_year": SAMPLE_YEAR,
            "item1_path": i1_path,
            "item7_path": i7_path,
            "revenue_fy_minus_3": revs[2022],
            "revenue_fy_minus_2": revs[2023],
            "revenue_fy_minus_1": revs[2024],
            "margin_fy_minus_3": margins[2022],
            "margin_fy_minus_2": margins[2023],
            "margin_fy_minus_1": margins[2024],
            "actual_revenue_growth": actual_rev_growth,
            "actual_margin": actual_margin,
            "backlog_mentioned": backlog_flag
        })

    df_master = pd.DataFrame(master_rows)
    df_excluded = pd.DataFrame(excluded_rows)

    df_master.to_csv(os.path.join(DATA_DIR, "master.csv"), index=False)
    df_excluded.to_csv(os.path.join(DATA_DIR, "excluded_firms.csv"), index=False)

    print(f"master.csv: {len(df_master)} firms")
    print(f"excluded_firms.csv: {len(df_excluded)} firms -- see file for reasons")

if __name__ == "__main__":
    main()

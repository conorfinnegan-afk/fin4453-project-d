import os
import time
import requests
import pandas as pd
from datetime import datetime

HEADERS = {"User-Agent": "UF FIN4453 Capstone Team c.finnegan@ufl.edu"}
DATA_DIR = "data"
FIN_DIR = os.path.join(DATA_DIR, "financials")
os.makedirs(FIN_DIR, exist_ok=True)

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax"
]

OPERATING_INCOME_TAGS = [
    "OperatingIncomeLoss",
    "OperatingProfit",
    "OperatingResults",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "GrossProfit"
]

# Forecast target is FY2025; baseline history is FY2022, FY2023, FY2024
TARGET_YEARS = [2022, 2023, 2024, 2025]

def is_matching_annual_fact(entry, target_fy):
    """
    Validates that a fact corresponds to the full-year target fiscal year by period end date,
    avoiding comparative period offsets in 10-K tables.
    """
    if entry.get("form") not in ["10-K", "10-K/A"]:
        return False
    if entry.get("fp") != "FY":
        return False
        
    end_str = entry.get("end")
    if not end_str:
        return False
        
    try:
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    except Exception:
        return False

    # Alignment: fiscal years ending June-Dec align to end_dt.year; Jan/Feb align to end_dt.year
    period_fy = end_dt.year
    if period_fy != target_fy:
        return False

    # Confirm duration is approximately an annual period (300 to 400 days)
    start_str = entry.get("start")
    if start_str:
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
            days = (end_dt - start_dt).days
            if days < 300 or days > 400:
                return False
        except Exception:
            pass

    return True

def extract_fact_value(facts_gaap, tag_list, target_fy):
    for tag in tag_list:
        if tag in facts_gaap:
            units = facts_gaap[tag].get("units", {})
            entries = units.get("USD", [])
            matched = [e for e in entries if is_matching_annual_fact(e, target_fy)]
            if matched:
                # Prioritize most recently filed audit/10-K report
                matched.sort(key=lambda x: x.get("filed", ""), reverse=True)
                return float(matched[0]["val"]), tag
    return None, None

def process_company(ticker, cik, problems_log):
    cik_padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    
    time.sleep(0.12)
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    facts_gaap = r.json().get("facts", {}).get("us-gaap", {})

    records = []
    for fy in TARGET_YEARS:
        rev, r_tag = extract_fact_value(facts_gaap, REVENUE_TAGS, fy)
        op_inc, o_tag = extract_fact_value(facts_gaap, OPERATING_INCOME_TAGS, fy)
        
        if rev is None:
            problems_log.append({"ticker": ticker, "fiscal_year": fy, "issue": "No revenue under REVENUE_TAGS"})
        if op_inc is None:
            problems_log.append({"ticker": ticker, "fiscal_year": fy, "issue": "No operating income under OPERATING_INCOME_TAGS"})

        op_margin = (op_inc / rev) if (rev and op_inc is not None and rev != 0) else None
        
        records.append({
            "ticker": ticker,
            "fiscal_year": fy,
            "revenue": rev,
            "operating_income": op_inc,
            "operating_margin": op_margin,
            "revenue_tag": r_tag,
            "op_income_tag": o_tag
        })
    return records

def main():
    firm_list_path = os.path.join(DATA_DIR, "firm_list.csv")
    firms = pd.read_csv(firm_list_path)
    all_data = []
    problems_log = []

    for _, row in firms.iterrows():
        ticker = row["ticker"]
        cik = row["cik"]
        print(f"{ticker}: fetching companyfacts...")
        try:
            records = process_company(ticker, cik, problems_log)
            df_firm = pd.DataFrame(records)
            df_firm.to_csv(os.path.join(FIN_DIR, f"{ticker}_financials.csv"), index=False)
            all_data.extend(records)
        except Exception as e:
            print(f"  FAILED {ticker}: {str(e)}")
            problems_log.append({"ticker": ticker, "fiscal_year": "ALL", "issue": str(e)})

    pd.DataFrame(problems_log).to_csv(os.path.join(DATA_DIR, "xbrl_problems_log.csv"), index=False)
    print(f"Done. Wrote {len(all_data)} firm-year rows across {len(firms)} firms.")

if __name__ == "__main__":
    main()

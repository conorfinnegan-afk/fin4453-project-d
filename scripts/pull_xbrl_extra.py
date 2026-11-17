"""Pull the balance-sheet and cash-flow items the firm-specific DCF scenario needs.

Same companyfacts source and matching rules as pull_xbrl.py, with one difference:
each value is taken as ORIGINALLY reported (earliest 10-K that contains it), so a
later restatement in the FY2025 10-K can't leak into the FY2024 inputs.

Writes data/financials_extra.csv (one row per firm per fiscal year, FY2023-FY2024)
and data/xbrl_extra_problems_log.csv.
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime

HEADERS = {"User-Agent": "UF FIN4453 Capstone Team c.finnegan@ufl.edu"}
DATA_DIR = "data"
YEARS = [2023, 2024]

# first tag found wins; the tag used is saved next to each value
TAGS = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "Cash"],
    "lt_debt_total": ["LongTermDebt",                       # includes the current portion
                      "LongTermDebtAndCapitalLeaseObligations",
                      "DebtLongtermAndShorttermCombinedAmount"],
    "lt_debt_noncurrent": ["LongTermDebtNoncurrent",
                           "LongTermDebtAndCapitalLeaseObligationsNoncurrent"],
    "lt_debt_current": ["LongTermDebtCurrent",
                        "LongTermDebtAndCapitalLeaseObligationsCurrent"],
    "short_term_debt": ["ShortTermBorrowings", "CommercialPaper", "DebtCurrent"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "dna": ["DepreciationDepletionAndAmortization",
            "DepreciationAmortizationAndAccretionNet",
            "DepreciationAndAmortization"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"],
    "minority_interest": ["MinorityInterest"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
SHARE_TAGS = {"diluted_shares"}            # unit is "shares", not USD


def matches_year(entry, fy):
    """10-K, full-year flag, period ending in fiscal year fy (same rule as pull_xbrl.py)."""
    if entry.get("form") not in ["10-K", "10-K/A"] or entry.get("fp") != "FY":
        return False
    try:
        end = datetime.strptime(entry["end"], "%Y-%m-%d")
    except (KeyError, ValueError):
        return False
    if end.year != fy:
        return False
    if entry.get("start"):                  # flows: ~1 year long; balances have no start
        days = (end - datetime.strptime(entry["start"], "%Y-%m-%d")).days
        if days < 300 or days > 400:
            return False
    return True


def first_reported(facts, tags, fy, unit="USD"):
    """Value as first reported in a 10-K for fiscal year fy: (value, tag, filed date)."""
    for tag in tags:
        entries = facts.get(tag, {}).get("units", {}).get(unit, [])
        hits = [e for e in entries if matches_year(e, fy)]
        if hits:
            hits.sort(key=lambda e: e.get("filed", ""))      # earliest filing first
            return float(hits[0]["val"]), tag, hits[0].get("filed")
    return None, None, None


def cover_shares(dei, fy_end_year):
    """Shares outstanding from the cover page of the 10-K for that fiscal year."""
    entries = dei.get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    hits = [e for e in entries if e.get("form") in ["10-K", "10-K/A"] and e.get("fy") == fy_end_year]
    if not hits:
        return None, None
    hits.sort(key=lambda e: e.get("filed", ""))
    first_filed = hits[0].get("filed")
    total = sum(float(e["val"]) for e in hits if e.get("filed") == first_filed)   # sums share classes
    return total, first_filed


def process(ticker, cik, problems):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    time.sleep(0.12)
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    facts = r.json().get("facts", {})
    gaap, dei = facts.get("us-gaap", {}), facts.get("dei", {})

    rows = []
    for fy in YEARS:
        rec = {"ticker": ticker, "fiscal_year": fy}
        for field, tags in TAGS.items():
            unit = "shares" if field in SHARE_TAGS else "USD"
            val, tag, filed = first_reported(gaap, tags, fy, unit)
            rec[field], rec[field + "_tag"] = val, tag
            if field == "cash":
                rec["first_filed"] = filed
            if val is None and field in ["cash", "assets_current", "liabilities_current", "capex", "dna"]:
                problems.append({"ticker": ticker, "fiscal_year": fy, "issue": f"no {field}"})

        # 1. total debt: one all-in figure if the firm reports one, else the parts
        if rec["lt_debt_total"] is not None:
            debt = rec["lt_debt_total"]
        else:
            debt = (rec["lt_debt_noncurrent"] or 0) + (rec["lt_debt_current"] or 0)
        debt = debt + (rec["short_term_debt"] or 0)
        rec["total_debt"] = debt
        # 2. net debt and operating working capital (cash and debt taken out)
        rec["net_debt"] = debt - (rec["cash"] or 0)
        if rec["assets_current"] is not None and rec["liabilities_current"] is not None:
            short_debt = (rec["lt_debt_current"] or 0) + (rec["short_term_debt"] or 0)
            rec["op_nwc"] = (rec["assets_current"] - (rec["cash"] or 0)) - (rec["liabilities_current"] - short_debt)
        else:
            rec["op_nwc"] = None
        # 3. effective tax rate
        if rec["income_tax"] is not None and rec["pretax_income"]:
            rec["tax_rate"] = rec["income_tax"] / rec["pretax_income"]
        else:
            rec["tax_rate"] = None
        rec["cover_shares"], rec["cover_shares_filed"] = cover_shares(dei, fy)
        rows.append(rec)
    return rows


def main():
    firms = pd.read_csv(os.path.join(DATA_DIR, "master.csv"))[["ticker", "cik"]]
    rows, problems = [], []
    for _, f in firms.iterrows():
        print(f"{f['ticker']}: fetching companyfacts...")
        try:
            rows.extend(process(f["ticker"], f["cik"], problems))
        except Exception as e:
            print(f"  FAILED {f['ticker']}: {e}")
            problems.append({"ticker": f["ticker"], "fiscal_year": "ALL", "issue": str(e)})

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA_DIR, "financials_extra.csv"), index=False)
    pd.DataFrame(problems).to_csv(os.path.join(DATA_DIR, "xbrl_extra_problems_log.csv"), index=False)

    fy24 = out[out["fiscal_year"] == 2024]
    print(f"\nDone: {len(out)} rows. FY2024 coverage:")
    for col in ["cash", "total_debt", "op_nwc", "capex", "dna", "tax_rate", "cover_shares", "diluted_shares"]:
        print(f"  {col:<15} {fy24[col].notna().sum()} of {len(fy24)}")


if __name__ == "__main__":
    main()

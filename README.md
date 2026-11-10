# FIN 4453 Capstone — Project D Data Pipeline (Fall 2026)

This repository contains the standardized, versioned data pipeline and deliverables for **Project D (Industrials Backlog Forecasting)**. 
Downstream teammates (Person 2: DCF / Baseline Forecaster, Person 3: Language Model Pipeline, Person 4: Validation & Scoring) can consume these files directly without querying EDGAR or XBRL.

---

## 1. Directory Structure

```
fin4453-project-d/
├── README.md                            # Schema documentation and team data loading guide
├── .gitignore                           # Python cache and temp files ignore rules
├── data/
│   ├── sp500_industrials_candidates.csv # Full initial pool of 95 industrial candidates
│   ├── excluded_firms_prefilter.csv     # 28 firms excluded at mechanical pre-filter
│   ├── firm_list.csv                    # 67 qualified industrial candidates (S&P 500 + S&P 1500)
│   ├── extraction_log.csv               # 10-K section text extraction status and character counts
│   ├── xbrl_problems_log.csv            # XBRL tag audit and missing fact log
│   ├── excluded_firms.csv               # Documented excluded firms with reasons
│   ├── master.csv                       # Single consolidated dataset (>= 50 firms)
│   ├── CHANGELOG.md                     # Schema versioning and changelog
│   ├── filings/                         # Item 1 and Item 7 text files for LM prompting
│   │   ├── {TICKER}_item1.txt
│   │   └── {TICKER}_item7.txt
│   └── financials/                      # Multi-year historical financials per firm
│       └── {TICKER}_financials.csv
└── scripts/
    ├── finalize_firm_list.py            # Generates firm_list.csv from candidate pool
    ├── pull_filings.py                  # Fetches 10-K filings and parses Item 1/Item 7
    ├── pull_xbrl.py                     # Queries SEC companyfacts API for financial tags
    └── build_master.py                  # Builds and validates master.csv and excluded_firms.csv
```

---

## 2. Master Dataset Schema (`data/master.csv`)

The primary data contract consumed across the project:

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticker` | string | Company stock ticker symbol (e.g. `CAT`, `BA`, `LMT`) |
| `cik` | string | SEC Central Index Key, zero-padded to 10 digits |
| `name` | string | Legal company name |
| `sample_year` | int | Fiscal year target being forecast (`2025`) |
| `item1_path` | string | Relative path to extracted Item 1 (Business) text file |
| `item7_path` | string | Relative path to extracted Item 7 (MD&A) text file |
| `revenue_fy_minus_3` | float | Annual revenue from 3 years prior (FY2022) |
| `revenue_fy_minus_2` | float | Annual revenue from 2 years prior (FY2023) |
| `revenue_fy_minus_1` | float | Annual revenue from 1 year prior (FY2024) |
| `margin_fy_minus_3` | float | Operating margin from 3 years prior (FY2022) |
| `margin_fy_minus_2` | float | Operating margin from 2 years prior (FY2023) |
| `margin_fy_minus_1` | float | Operating margin from 1 year prior (FY2024) |
| `actual_revenue_growth` | float | Realized revenue growth in sample year (FY2025 vs FY2024) |
| `actual_margin` | float | Realized operating margin in sample year (FY2025) |
| `backlog_mentioned` | bool | Boolean flag: backlog/order-book terms present in Item 1 or 7 |

---

## 3. Rubric & Honest Test Compliance

1. **Sample Size:** Contains >= 50 large industrial firms as mandated by the project criteria.
2. **Temporal Separation (Zero Look-Ahead):** Input text files (`Item 1` and `Item 7`) are extracted strictly from the **FY2024 10-K** (filed in early 2025) to forecast **FY2025 outcomes**, guaranteeing zero look-ahead bias during inference.
3. **Macro Cleanliness:** Baseline averages use FY2022–FY2024, cleanly skipping the 2020–2021 pandemic supply-chain disruptions.

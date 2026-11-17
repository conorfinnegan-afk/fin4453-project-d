# Person 2: Baseline and DCF

`02_dcf_baseline.ipynb` reads `../data/master.csv` and runs top to bottom. You need `pandas` and `numpy`. `numpy_financial` is optional and only used for one check.

## What's in the notebook

| Part | Contents |
| :--- | :--- |
| 0 | Data checks, the four flagged firms, assumptions with sources, WACC |
| 1 | Three-year-average baseline plus a "last year" benchmark, and their FY2025 accuracy |
| 2 | `npv`, `growth_path` and `dcf`, tested on dummy numbers first |
| 3 | All 53 firms valued under each forecast, with the error split into growth and margin |
| 4 | Growth x margin grid, one-at-a-time sensitivity, and whether the assumptions change who wins |
| 5 | Firm-specific robustness: each firm's own WACC, tax and reinvestment, plus value per share vs the 52-week price range |
| 6 | Notes for Persons 3 and 4 |

## Output files

`output/baseline_forecasts.csv` has one row per firm: baseline and last-year growth and margin, the actuals, and the `backlog` and `flag` columns.

`output/per_share_vs_price.csv` and `.png` compare firm-specific value per share with each firm's 52-week range (a level check, not a score).

`output/dcf_valuations.csv` has one row per firm per scenario: `ev`, `ev_perfect_foresight` (our DCF fed actual FY2025 results, not a market value), `err_growth_only`, `err_margin_part`, `err_full`.

## Backlog rule

`data/rule_labels.csv` holds a mechanical backlog rule applied to 28 firms (applied with Claude, evidence in `data/rule_labels_evidence.csv`). The notebook scores every scenario on those 28 firms in Part 3.

## Secondary backlog split

`flag_quantified_backlog.py` flags firms whose 10-K quantifies the change in backlog; it writes `backlog_quantified.csv` with the evidence sentence for each firm. The notebook adds it as two extra groups.

## Adding the model's forecasts

Save `data/lm_forecasts.csv` with columns `ticker, label, growth, margin` (decimals, one label per run like `AI full` or `AI no MD&A`) and rerun the notebook. Any firm missing from a run gets the baseline forecast, and the notebook prints how many.

## Main modelling choices

Year-1 growth is the forecast, and it fades in a straight line to 2.5% by year 5 (FY2029). Reinvestment is max(growth, 0) / ROIC, so faster growth costs cash. WACC (8.8%), terminal growth, tax (25%) and ROIC (20%) are the same for every forecast, and Part 4 shows changing them one at a time doesn't change the order. Giving each firm its own inputs (Part 5) does reshuffle the model against "last year".

## Validation

`../eval/03_validation.ipynb` checks the model's output (quotes, backlog read, leak) and recomputes the headline numbers a second way, including the bootstrap without the four flagged firms.

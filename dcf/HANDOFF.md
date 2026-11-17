# Handoff: Project D, Person 2 (Baseline + DCF)

Written 11 Nov 2026 at the end of the Person 2 build. It's meant for whoever (person or AI) picks this up next, and assumes you've seen none of the earlier conversation. Read the whole thing before you change anything.

---

## 1. The project in one paragraph

FIN 4453 (Financial Modeling, UF, Fall 2026, Prof. Yanbin Wu) final project, "Project D". The question is whether a language model that reads an industrial company's FY2024 10-K, especially its backlog and order commentary, can forecast FY2025 revenue growth (and operating margin) better than a simple three-year-average rule, and how much the difference matters for a DCF valuation. Backlog is signed-but-undelivered orders, so it's a preview of next year's revenue that a backward-looking average can't see. There's an optional ablation: run the model once with the full 10-K and once without Item 7 (MD&A) to see whether management commentary is what helps.

Group pitch line: *"We're testing whether an AI that reads industrial companies' backlog commentary can forecast next year's sales better than a simple three-year average, and then seeing how much that changes the DCF value."*

## 2. Team roles (from the project brief)

| Role | Owns | Deliverable |
| :--- | :--- | :--- |
| Person 1, Data | firm list, 10-K Item 1/7 text, XBRL financials | `data/` folder (done, in the repo) |
| Person 2, DCF/Baseline | 3-yr-average calculator, DCF taking any growth/margin, sensitivity table | **`dcf/` folder (this, done)** |
| Person 3, Language model | prompt that reads 10-K backlog language; growth + margin forecast with a justifying quote, fixed format; record of model/version and training cutoff | script: 10-K in, structured forecasts out |
| Person 4, Validation & write-up | blind hand-labeled answers; MAE of LM vs baseline vs actual, only on years after the model's cutoff; memo, AI Use Log, slides | final memo, AI Use Log, slides |

Repo: `https://github.com/conorfinnegan-afk/fin4453-project-d` (public, built by Person 1). Person 2's local clone is at `C:\Users\Agnivesh Kaundinya\Desktop\Special Projects\fin4453-project-d`. The `dcf/` folder was created locally and **may not be pushed yet**. The intended branch is `person2-dcf`. Person 2 (Agnivesh) does the git pushing himself.

## 3. What's in `dcf/`

| File | What it is |
| :--- | :--- |
| `02_dcf_baseline.ipynb` | The deliverable. Runs top to bottom from `../data/master.csv`, saved with outputs. **This is the source of truth; edit it directly.** |
| `README.md` | Short user guide (what's in each part, outputs, how to add LM forecasts). |
| `output/baseline_forecasts.csv` | One row per firm (53): `base_growth, base_margin, last_growth, last_margin, actual_growth, actual_margin, backlog, flag`. Index `ticker`. |
| `output/dcf_valuations.csv` | One row per firm per scenario: `ticker, scenario, growth, margin, ev, ev_perfect_foresight, err_growth_only, err_margin_part, err_full`. |
| `HANDOFF.md` | This file. |
| `../eval/03_validation.ipynb` | Person 4's validation (Agnivesh took this over on 17 Nov): output checks, quote grounding, backlog flag agreement, leak checks, the headline numbers recomputed a second way, and which Lecture 1 check backs each number. Writes `eval/output/quote_check.csv` and `verification_scorecard.csv`. Run from `eval/`. |

Outside `dcf/`, Person 2 added `scripts/pull_xbrl_extra.py` and `scripts/pull_market_data.py` (and their outputs in `data/`), `data/rule_labels.csv` with its evidence file, and the fiscal-2024 filing fixes in Section 7. Otherwise `data/` and `scripts/` belong to Person 1.

Requirements: `pandas`, `numpy`; `numpy-financial` optional (one check only, wrapped in try/except). To open: `jupyter` or VS Code + `ipykernel`. The notebook must run with `dcf/` as the working directory because it reads `../data/master.csv` and writes `output/`.

## 4. The data it uses (`data/master.csv`, from Person 1)

53 firms, no missing values, 38 with `backlog_mentioned = True`. Columns used: `ticker`, `revenue_fy_minus_3/2/1` (FY2022/23/24), `margin_fy_minus_3/2/1` (operating margin FY2022/23/24), `actual_revenue_growth` (FY2025 vs FY2024), `actual_margin` (FY2025), `backlog_mentioned`. Text for Person 3 is at `item1_path` / `item7_path` (FY2024 10-Ks, filed early 2025). Excluded firms and reasons: `data/excluded_firms.csv`.

**FY2021 is not in the data, on purpose.** `scripts/pull_xbrl.py` sets `TARGET_YEARS = [2022, 2023, 2024, 2025]`, and the README says the window avoids pandemic distortions. The team decided to keep it that way. Don't add FY2021.

### Known data problems (flagged in the notebook, not dropped)

| Ticker | Problem |
| :--- | :--- |
| DD | FY22 revenue $13.0B vs FY23 $6.6B: FY22 looks un-restated for a divestiture. Its "operating margin" uses the pre-tax income tag (`IncomeLossFromContinuingOperationsBefore...`), not operating income. |
| FTV | FY22 $5.8B vs FY23 $3.9B: same kind of restatement mismatch (likely the Ralliant spin). |
| MMM | FY23 margin −43% from one-off litigation charges, which distorts its 3-yr margin average. |
| BA | Operating losses FY22–24, then +34% revenue in FY25. Real numbers, but extreme. |

The notebook keeps all 53 and reports every summary with and without these four (`flag != ""`). Also not flags but worth knowing: XYL (Evoqua acquisition inflated FY23) and CARR (portfolio reshaping) are large baseline misses caused by M&A, not backlog. AXON has a negative FY2025 actual margin (−2.2%), so its actual-results EV is negative and it's excluded from the "full" percentage-error stats (the notebook prints this).

Possible subtle look-ahead (tell Person 4): restated FY2023–24 figures for DD/FTV may come from the FY2025 10-K, i.e. after the valuation date. Minor.

## 5. Every modelling decision and why

These were all discussed and agreed with Person 2. Don't change them without a reason you can write down.

**Baseline (the official benchmark).** Margin = mean of FY22, FY23, FY24 margins. Growth = mean of FY23 and FY24 YoY growth. That's only two growth rates, because three revenue years give two growth rates and FY2021 is excluded. Describe it accurately in writing ("average of FY2023 and FY2024 growth"). The FY22→FY24 CAGR was tested and is essentially identical (MAE 6.59% vs 6.51%).

**Second benchmark: "last year".** FY2024 growth and FY2024 margin alone. It captures momentum. If the LM beats the 3-yr average but not last year, it may be reading momentum, not backlog. The 3-yr average stays the official baseline because the rubric names it.

**Valuation date and timeline.** Early 2025, right after the FY2024 10-K. Base year (t=0) = FY2024 revenue. Year 1 = FY2025, **the only year scored**, using each scenario's forecast. Years 2–5 = FY2026–FY2029. Terminal value from FY2030 at 2.5%. Discounting uses the Lecture 6/7 convention `first_at=1`.

**Fade.** Year-1 growth = the forecast, then a straight line to `G_TERM` by year 5 (weights 0, .25, .5, .75, 1). Both the baseline and the LM forecast one year only; holding e.g. AXON's 32.5% for five years would compound to about 4x revenue and swamp every comparison. Margin is held flat at the forecast for all years (FY24 margin correlates 0.91 with FY25 margin). `fade=False` exists only for one comparison cell.

**Reinvestment = max(growth, 0) / ROIC.** It ties the cost of growth to growth, so a higher growth forecast doesn't get free value. It's floored at 0 so shrinking doesn't create cash. Above 20% growth, reinvestment exceeds 100% and FCF goes negative in that year, which is intended.

**FCF and EV.** FCF_t = Revenue_t × margin × (1 − tax) × (1 − reinvestment_t). TV = Revenue_5 × (1+g) × margin × (1−tax) × (1 − g/ROIC) / (WACC − g). Output is **enterprise value**, not per share, because there's no net debt or share count in the data. Scored as ratios, so size drops out.

**Two margin versions (both run).** "Growth only": the same margin for every scenario, so only growth differs (the clean backlog test). "Full": each scenario's own growth and margin. Because EV is exactly proportional to margin, the full error splits exactly: `(1 + full) = (1 + growth part) × (1 + margin part)`, with margin part = forecast margin / actual margin − 1. The notebook asserts this identity on every firm.

**Valuation error.** `EV(forecast) / EV(actual FY2025 growth and margin) − 1`. Report median absolute error as the headline (a few firms produce errors in the hundreds of percent) and the mean alongside.

### Fixed assumptions (same for every forecast)

| Constant | Value | Source |
| :--- | :--- | :--- |
| `RF` | 4.5% | 10-yr Treasury closed 4.49% on 7 Feb 2025 ([ETF Trends / Advisor Perspectives](https://www.etftrends.com/fixed-income-channel/treasury-yields-snapshot-february-7-2025/)). Dated to when the FY2024 10-Ks were filed. |
| `ERP` | 5.0% | Course value (Lecture 7 WACC slide). Damodaran implied ERP was 4.33% on 1 Jan 2025 ([BVWire](https://www.bvresources.com/articles/bvwire/damodaran-posts-his-first-data-update-for-2025)), used as a sensitivity. |
| `BETA` | 1.00 | Damodaran Jan 2026: Machinery 0.96, Aerospace/Defense 0.95 ([wacc.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html)) |
| `D_WT` | 13% | Damodaran: Machinery 12.81%, A&D 13.47% ([optvar.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/optvar.html)) |
| `KD_AT` | 4.0% | Damodaran Machinery: 5.29% pre-tax, 3.97% after tax (wacc.html) |
| `WACC` | 8.8% | Computed: ke = 4.5% + 1.0 × 5.0% = 9.5%; 0.87 × 9.5% + 0.13 × 4.0% = 8.79%, rounded |
| `G_TERM` | 2.5% | Judgment: below RF, under the ~3% Lecture 7 flags as "outgrowing the economy" |
| `TAX` | 25% | 21% federal + state; Damodaran's 5.29% → 3.97% implies 25% |
| `ROIC` | 20% | Damodaran Jan 2026 after-tax ROIC (lease & R&D adj.): Machinery 24.41%, A&D 16.01%, Electrical Equipment 15.60% ([roc.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/roc.html)). Cross-check: Machinery reinvestment rate 34.33% ([fundgrEB.html](https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/fundgrEB.html)) |
| `YEARS` | 5 | Lectures 7–8 structure |

Caveat for the memo: the Damodaran tables are January 2026, the valuation date is February 2025. It's a small effect; one line in the memo is enough.

## 6. Results on clean data (updated 17 Nov 2026)

All 53 firms, after the fiscal-year fix in Section 7. Growth and margin MAE against actual FY2025:

| Group | n | 3-yr avg | Last year | AI full | AI no MD&A | Margin: 3-yr / last / AI full |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| all | 53 | 6.5% | 5.6% | **4.8%** | 5.3% | 2.8% / 1.9% / 1.8% |
| backlog | 38 | 7.5% | 6.6% | **5.2%** | 5.8% | 2.4% / 2.0% / 1.7% |
| no backlog | 15 | 4.1% | **3.1%** | 3.8% | 4.0% | 3.8% / 1.7% / 2.0% |

Paired bootstrap on growth error (10,000 draws, firms resampled):

| Comparison | All 53 | Backlog (38) | No backlog (15) |
| :--- | :--- | :--- | :--- |
| AI full vs 3-yr avg | −1.7pp [−3.6, −0.0] reliably better | −2.3pp [−4.5, −0.2] reliably better | −0.3pp, not distinguishable |
| AI full vs last year | −0.8pp, not distinguishable | −1.4pp, not distinguishable | +0.6pp, not distinguishable |
| AI full vs no MD&A | −0.5pp, not distinguishable | −0.6pp, not distinguishable | −0.2pp, not distinguishable |

The all-firm result depends on the four flagged firms. Without BA, DD, FTV and MMM (`eval/03_validation.ipynb`, Part 5): AI full vs 3-yr average −0.9pp [−2.5, +0.7], backlog ex-flagged −1.6pp [−3.6, +0.3], neither distinguishable. The two biggest wins are DD and FTV, where the 3-yr average averages over a restated FY2022. Firm by firm, AI full beats the 3-yr average on 27 of 53 and last year on 21 of 53. In dollars (summed absolute growth-only miss): 3-yr $134bn, last year $132bn, AI full $101bn; ex-flagged $107bn / $101bn / $83bn.

Valuation error (median absolute, growth only, all 53): last year 4.4%, AI full 5.2%, 3-yr 5.3%, no MD&A 5.5%. Means tell the other half: AI full 7.6% vs last year 9.0% vs 3-yr 11.1%, so the AI mostly avoids large misses rather than winning the typical firm. Backlog firms, median growth-only: AI full 5.2%, 3-yr 5.9%, last year 7.6%. Growth and margin combined, median: 3-yr 11.4%, last year 9.1%, AI full 9.5%, no MD&A 8.7%.

Decomposition (ex-flagged, median): 3-yr average growth part 4.9%, margin part 11.5%; AI full 5.2% and 6.1%. Margin drove the 3-yr average's valuation gap; the AI closed most of it by tracking the latest margin.

Secondary split (`backlog_quantified.csv`, rule in `flag_quantified_backlog.py`): 29 firms whose 10-K quantifies the change in backlog, 24 that don't. Growth MAE, quantified: AI full 5.6%, last year 6.8%, 3-yr 7.1%; not quantified: AI full 3.8%, last year 4.2%, 3-yr 5.8%. The AI's edge over the 3-yr average is similar in both groups; over last year it is larger where backlog is quantified (−1.2pp vs −0.4pp). No gap in this split clears the bootstrap. The rule was fixed before results were split by it; the 38/15 split stays primary.

Firm-specific robustness (notebook Part 5, data from `scripts/pull_xbrl_extra.py` and `scripts/pull_market_data.py`): each firm gets its own beta (2-yr weekly vs S&P 500, Blume-adjusted), debt weight (book debt / book debt + market cap on 28 Feb 2025), cost of debt (interest / debt, 3% to 9%), tax rate (effective, 15% to 30%), and reinvestment ((capex − D&A) and working capital as shares of revenue; terminal capex at least covers D&A). WACCs run from 6.4% (LMT) to 13.0% (VRT), median 9.3%. Results: the AI beats the 3-yr average on every measure; against last year the order shuffles (AI has the lowest median growth-only error, 5.7% vs 6.0%; last year keeps the lowest combined median, 10.0% vs 12.2%). Per-firm AI errors correlate 0.89 (rank) with the flat-input version. Gaps filled with medians: net capex for EME, IEX, ITW, PH, PNR, PWR; working capital for PCAR, DE; tax for ITW; cost of debt for 18 firms without an interest-expense tag. Terex shows $0 debt (tag gap after the ESG acquisition).

Market level check (`output/per_share_vs_price.csv`, `.png`): perfect-foresight value per share is inside the 52-week range for 10 of 53 firms; median value / price 0.56. Defense primes land above price (low betas), thin-margin firms (AXON, DD, BA) far below. This is why the main test scores against perfect foresight, not price.

Robustness: the median growth-only ranking (last year first) holds in all 10 settings (base + 9 alternatives).

Backlog rule (28 firms, 19 backlog / 9 not; `data/rule_labels.csv`): growth MAE rule 3.9%, AI full 3.1%, AI no MD&A 2.7%, 3-yr 3.4%, last year 3.3%. On backlog firms the AI beats the rule by 1.8pp [−3.5, −0.4]. The rule's backlog step (G2) fails on firms like PNR and HUBB, whose backlog fell 17–18% as supply-chain backlogs normalised while sales kept growing; PNR's 10-K says outright that backlog isn't an indicator of 2025 sales. Reading context beats reading the number. The 28 firms exclude the most dramatic movers, so compare within that table only.

Sensitivity (median firm: growth 6.7%, margin 15.2%, EV ≈ 1.73x FY2024 revenue). Swing per point, as % of EV: WACC 16.8, terminal growth 10.2, margin 6.6, year-1 growth 1.5, tax 1.3, ROIC 1.0.

Level check: ~1.7x EV/revenue is about half Damodaran's Machinery EV/Sales of 3.43x. `ev_perfect_foresight` is our DCF fed actual FY2025 results, not a market value; every forecast is scored as a ratio to it, so the level cancels.

## 7. Data problems found and fixed

**Fiscal-year leak (fixed 16 Nov).** `scripts/pull_filings.py` took the first 10-K "filed in 2025". For the 9 non-December filers (DE, DY, EMR, J, JCI, NDSN, PH, ROK, TDG) that was the FY2025 10-K, so the answer was in the text, and the model copied it (J and NDSN growth and TDG margin matched actuals exactly). The 18 text files were replaced with the fiscal-2024 10-Ks (Dycom: fiscal year ended 27 Jan 2024) and Person 3 reran those 9 firms (commits 5708a93, dc488bd). The script itself still has the bug if anyone reruns it.

**Table-of-contents extractions.** Several Item 7 files start at the 10-K's table of contents and run through Items 1–6 before the MD&A: GNRC, HUBB, HII, LII, PWR, RTX, FLS, WSO (and IR's Item 1). The MD&A is inside each, so nothing is missing; it is extra text. Deere and Dycom were extracted by hand.

**Plug-in format for model forecasts:** `data/lm_forecasts.csv` with `ticker, label, growth, margin` (decimals). Rerunning `lm/forecast.py` with `--tickers` overwrites the file with only those firms; to redo a subset, delete their JSONs in `lm/output/raw/` and run without `--tickers`.

## 8. What's next (as of 17 Nov)

1. **Firm-specific scenario:** done (see Section 6, notebook Part 5).
2. **Quantified-backlog split:** done (see Section 6).
3. **Person 4's work:** Agnivesh took it over on 17 Nov. Validation notebook done (`eval/03_validation.ipynb`). Memo (Prof. Wu's three sentences from Lecture 8) and AI Use Log (Lecture 1's four questions) are in a Claude doc, with a Word copy in `eval/Project_D_Memo_and_AI_Use_Log.docx`. Teammates still need to fill in their own lines of the AI Use Log.
4. **Slides:** handed off by Agnivesh to a teammate. The Part 2 slide-content doc has the clean numbers.

## 9. Style rules (follow these if you edit the notebook)

**Code style matches Prof. Wu's lectures** (lecture HTML exports are on Agnivesh's PC at `Downloads\course_files_export`). Small flat functions with short names, defaults pulled from uppercase constants, one-line docstrings only when there's a convention to explain, no classes, no type hints. Loops written out (`total = total + ...`) before any library, then checked against a library or identity. Assumptions as uppercase constants, several per line, each with a source comment. Numbered step comments inside the main function. Aligned f-string prints (`:,.0f`, `:.2%`, `:+.1%`), `print(df.round(3).to_string())`. A sanity check after every calculation.

**Prose and comments must not read as AI-written.** Agnivesh supplied a style template; the rules are:
- Direct, point first, specific examples. Use contractions. "We" for the group.
- Banned words: delve, dive into, navigate (figurative), underscore, bolster, foster, harness, leverage, unpack, shed light on, pave the way, pivotal, groundbreaking, cutting-edge, transformative, game-changing, innovative, robust, comprehensive, seamless, intricate, nuanced, vibrant, multifaceted, holistic, testament, landscape, realm.
- Banned phrases: "In today's ... world", "It's important/worth noting", "One of the most ...", "When it comes to", "At its core", "At the end of the day", "This is where X comes in", "Let's break it down", "Plays a crucial role", "underscoring the importance", "highlighting the need", "reflecting a broader trend", "marking a significant shift".
- Banned structures: "It's not just X, it's Y", "Not only X but Y", "This isn't about X. It's about Y.", "No X. No Y. Just Z."
- No "**Bold term:** explanation" lists. No signposting. No sweeping opener or summary wrap-up. Vary sentence and paragraph length.
- At most one em dash per piece (the notebook currently has zero). No emojis in headers.

The notebook was checked against this list after the rewrite. Keep it that way.

## 10. Checks to rerun after any change

1. Notebook runs top to bottom with no errors from inside `dcf/`.
2. Part 2: `npv` agrees with `numpy_financial`; the vectorised dummy-firm EV equals `dcf()`; the Gordon identity difference is about 1e-12; the guard raises `ValueError`; the margin and revenue scaling are both exactly 2.000000.
3. Part 3: the identity `(1+total) = (1+growth)(1+margin)` prints `True`.
4. A CAT spot check: 3-yr EV ≈ $126.0bn vs perfect-foresight EV ≈ $117.3bn (+7.4%) at base assumptions.
5. An independent recompute of all EVs in `dcf_valuations.csv` with separately written code matched to 2e-15 at handoff. Redo it if you touch `dcf()`.
6. Prose still clean against Section 9.

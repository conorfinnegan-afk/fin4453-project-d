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
| `output/dcf_valuations.csv` | One row per firm per scenario: `ticker, scenario, growth, margin, ev, ev_actual, err_growth_only, err_margin_part, err_full`. |
| `HANDOFF.md` | This file. |

Nothing outside `dcf/` was modified. Don't edit `data/` or `scripts/`; they belong to Person 1.

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

## 6. Results so far (benchmarks only, no LM forecasts yet)

Growth and margin accuracy, FY2025 MAE:

| Group | n | growth, 3-yr | growth, last yr | 3-yr growth bias | margin, 3-yr | margin, last yr |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 53 | 6.51% | 5.61% | +1.08% | 2.82% | 1.87% |
| backlog | 38 | 7.47% | 6.59% | +1.82% | 2.42% | 1.95% |
| no backlog | 15 | 4.10% | 3.14% | −0.77% | 3.83% | 1.67% |
| ex-flagged | 49 | 5.42% | 4.98% | +2.80% | 2.36% | 1.54% |

Valuation error (median absolute), growth-only version: 3-yr average 5.3%, last year 4.4% (all 53). By group the ranking flips: among backlog firms the 3-yr average is better (5.9% vs 7.6%), and ex-flagged too (4.7% vs 5.4%). Full version: 11.4% vs 9.1%.

Decomposition (ex-flagged, median): for the 3-yr average, growth part 4.9%, margin part 11.5%; the margin part is bigger for about 71% of firms. Without the fade the growth part about doubles (9.6%). So **margin misses drive valuation error more than growth misses**, partly by construction (EV ∝ margin; growth only drives year 1). This matters for the story: an LM that nails backlog-driven growth gains less in value terms than in accuracy terms.

Sensitivity (median firm: growth 6.7%, margin 15.2%, EV ≈ 1.73x FY2024 revenue). Swing per percentage point: WACC 0.29, terminal growth 0.18, margin 0.11, year-1 growth 0.026, tax 0.023, ROIC 0.017 (in x revenue). Ranked by raw swing, margin comes first only because it was varied over a wider range; that's the Lecture 8 tornado warning, and the table reports ranges for that reason.

Robustness: the same benchmark wins under all 10 alternative settings (WACC ±1pp, WACC 8.2% with ERP 4.33%, g 1.5%/3.5%, tax 21%, ROIC 15%/25%, no fade). The fixed assumptions change the size of errors, not the ranking.

Level check: the model's ~1.7x EV/revenue is about half Damodaran's Machinery EV/Sales of 3.43x ([psdata.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/psdata.html)). That's fine for a ratio-based comparison, but these aren't price targets.

## 7. How the LM forecasts plug in (Person 3 → Person 2)

Save `data/lm_forecasts.csv`:

| column | meaning |
| :--- | :--- |
| `ticker` | matches `master.csv` |
| `label` | one per run, e.g. `AI full`, `AI no MD&A` |
| `growth` | FY2025 revenue growth forecast, decimal |
| `margin` | FY2025 operating margin forecast, decimal |

Rerun the notebook. Each label becomes a scenario in every table, the decomposition, the robustness check and `dcf_valuations.csv`. Firms missing from a run fall back to the baseline and the notebook prints how many. This path was tested with a synthetic file (two labels, two missing firms) and worked. If Person 3's script outputs a different format (e.g. JSON with quotes), write a small adapter to this CSV rather than changing the notebook. Percentages must be decimals.

**Critical issue for Person 3/4: training cutoff.** FY2025 results were published roughly Jan–Mar 2026. A model whose training data extends past about January 2026 may already know actual FY2025 revenue, which breaks the "honest test". The brief requires testing only on years after the model's cutoff. Record the exact model, version and cutoff in the AI Use Log, and if the cutoff is too late, say so in the memo.

## 8. What's next

1. **Person 3:** produce `data/lm_forecasts.csv` (full 10-K run, and the no-MD&A run if doing the ablation).
2. **Rerun the notebook** and read every table again, especially the robustness table: if the winner flips under a plausible setting, report it.
3. **Person 4:** score accuracy on FY2025 only; report the LM against both benchmarks; split by `backlog` (the 15 non-backlog firms are a control group: an edge only on backlog firms supports the thesis); report with and without the four flags; keep M&A-driven wins (XYL, CARR) separate from backlog wins.
4. **Memo:** use Prof. Wu's three-sentence format from Lecture 8: the number and the gap, the assumption carrying it with its magnitude, and a specific condition under which you'd be wrong. State that the growth-vs-margin split depends on the fade.

Optional improvements nobody has asked for yet: date-matched (Jan 2025) Damodaran inputs; industry-specific ROIC (no industry column exists in `firm_list.csv`, so it would need a hand mapping); a bootstrap confidence interval on the median errors, since n = 53 and the gaps between methods are small.

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
4. A CAT spot check: 3-yr EV ≈ $126.0bn vs actual-results EV ≈ $117.3bn (+7.4%) at base assumptions.
5. An independent recompute of all EVs in `dcf_valuations.csv` with separately written code matched to 2e-15 at handoff. Redo it if you touch `dcf()`.
6. Prose still clean against Section 9.

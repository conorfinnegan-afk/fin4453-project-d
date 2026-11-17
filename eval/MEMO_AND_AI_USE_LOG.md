# Project D: Memo and AI Use Log

17 Nov 2026. Working copy lives in the team's Claude doc; this file is the copy that ships with the repo.

## The memo

From FY2024 10-Ks, Llama 3.3 cut FY2025 revenue-growth error for 53 industrials from 6.5 to 4.8 points against the three-year average, shrinking the growth-driven DCF miss from $134bn to $101bn. That edge leans on four firms with broken histories (BA, DD, FTV, MMM); without them it's $23bn and 0.9 points, within noise. We're wrong if the same prompt on FY2023 10-Ks can't beat that average on FY2024 outside those four.

69 words. Every number comes from code: `dcf/02_dcf_baseline.ipynb` (Part 3) and `eval/03_validation.ipynb` (Parts 5 and 6). The FY2023 test in the last sentence stays honest because Llama 3.3's training data stops in December 2023, before any FY2024 results were out.

## The numbers behind it

The model beats the three-year average on growth, ties "last year" on margin, and never reliably beats simply repeating FY2024. Errors are against actual FY2025 results; valuation errors are against our DCF fed those actuals (perfect foresight), not market prices.

| Measure (53 firms unless noted) | 3-yr average | Last year | AI full | AI no MD&A |
| --- | --- | --- | --- | --- |
| Growth error, mean absolute | 6.5% | 5.6% | 4.8% | 5.3% |
| Growth error, 38 backlog firms | 7.5% | 6.6% | 5.2% | 5.8% |
| Growth error, 15 no-backlog firms | 4.1% | 3.1% | 3.8% | 4.0% |
| Growth error, without the 4 flagged firms | 5.4% | 5.0% | 4.5% | 4.8% |
| Margin error, mean absolute | 2.8% | 1.9% | 1.8% | 1.8% |
| Valuation error from growth, median firm | 5.3% | 4.4% | 5.2% | 5.5% |
| Valuation error from growth and margin, median firm | 11.4% | 9.1% | 9.5% | 8.7% |
| Summed valuation miss from growth, $bn | 134 | 132 | 101 | 102 |
| Summed valuation miss from growth and margin, $bn | 404 | 275 | 313 | 310 |

A paired bootstrap (10,000 draws, firms resampled) says how much of each gap could be luck. Against the three-year average the model's growth edge is 1.7 points, 95% range [-3.6, -0.02], and 2.3 points [-4.5, -0.2] on backlog firms. Without BA, DD, FTV and MMM it falls to 0.9 points [-2.5, +0.7]. Against "last year" no group clears zero, and adding the MD&A (full run vs no-MD&A run) is worth 0.5 points [-1.2, +0.2].

The edge comes from a few big misses avoided, not from winning the typical firm: the model beats the three-year average on 27 of 53 firms and "last year" on 21. Its two biggest wins are DD and FTV, where the baseline averages over a restated FY2022 and forecasts -24% and -14%. The next four (XYL, OSK, TEX, CARR) are backlog firms where the baseline extrapolated an acquisition or a boom year, which is the thesis working.

On a 28-firm subset, a fixed backlog rule (company guidance if given, else FY2024 growth averaged with the change in backlog) loses to the model on backlog firms by 1.8 points [-3.5, -0.4]. The rule fails on firms like PNR and HUBB, whose backlog fell as supply chains normalised while sales kept growing. Reading the context mattered more than reading the backlog number.

## Before you trust it

The edge over the three-year average is real but small, and these are the places it could bend.

- The yardstick is our own DCF, not the market. Every firm shares an 8.8% WACC and a 20% ROIC. With each firm's own beta, debt, tax and reinvestment, every error gets bigger and the model and "last year" swap places depending on the measure (5.7% vs 6.0% on growth, 12.2% vs 10.0% on growth and margin). Fed perfect foresight, the DCF still lands at about 0.56 times the share price for the median firm.
- The growth-versus-margin split depends on the fade. Holding year-1 growth for five years instead of fading it to 2.5% doubles the growth share of the three-year average's miss (4.9% to 9.6% of value).
- Our first run leaked. For nine non-December filers the filing script picked up the FY2025 10-K, so the model was reading the answers. We swapped in the fiscal-2024 10-Ks and reran. The model still does better on those nine (3.4% error vs 5.1% on the rest) while the baseline doesn't, which is probably luck with nine firms; none lands within half a point of actual.
- The model can't have seen FY2025: Llama 3.3's training data stops in December 2023, and asked with no filing, it recalled nothing for any of the 53 firms. That cutoff also means it never saw 2024 news, only the 10-K and the history table.
- Six of 212 quotes the model gave as support aren't in the filing. EMR's cites a 24.7% adjusted margin where the 10-K says 25.8%. The quotes don't feed the DCF, but none should be repeated without checking.
- The 28-firm backlog rule was applied with Claude, not by hand; the sentence behind each number is in `data/rule_labels_evidence.csv`.
- Data choices: FY2021 is left out to avoid the pandemic rebound, so baseline growth averages two years. Nine extracts start at the table of contents (the text we need is still in them), DE and DY were cut by hand, and Terex shows $0 debt because its debt tags didn't match after an acquisition.

## AI Use Log

Llama 3.3 is the model being tested, and Claude helped build and check everything around it. Lines in square brackets are for teammates to fill in for their own parts.

### Which tools, for which parts?

| Part | Tool | What it did |
| --- | --- | --- |
| Forecasts (Person 3) | Llama 3.3 70B Instruct (`llama-3.3-70b-instruct`) on UF NaviGator, temperature 0, prompt v1.0 (hash 9a51f8c2fcc61005), run 15 and 16 Nov 2026, 1.82M input and 26.5k output tokens | Read each FY2024 10-K with the company's name replaced by "the Company" and returned FY2025 growth, margin, a backlog read and two supporting quotes. This is the LLM component under test. |
| Baseline, DCF, sensitivity (Person 2) | Claude (Anthropic, Claude Opus 5.5 in claude.ai) | Wrote `dcf/02_dcf_baseline.ipynb` in the lectures' code style, the extra data scripts (`pull_xbrl_extra.py`, `pull_market_data.py`), the quantified-backlog flag and the firm-specific scenario. |
| Data fixes | Claude | Found the fiscal-year leak and extracted the replacement fiscal-2024 10-Ks for nine firms. |
| Backlog rule, 28 firms | Claude | Applied our fixed rule to each 10-K and saved the sentence behind every number. |
| Validation, memo, this log (Person 4's part) | Claude | Wrote `eval/03_validation.ipynb` and drafted this doc. |
| Data pipeline (Person 1) | [Conor: tools used for `pull_filings.py`, `pull_xbrl.py`, `build_master.py`, or "none"] | |
| Forecast script (Person 3) | [Person 3: was `lm/forecast.py` written with an assistant? Which one?] | |
| Slides | [whoever builds them] | |

### What did we ask for?

Llama got the prompt in `lm/prompt.py`: it's February 2025, here's the FY2022 to FY2024 revenue and margin table and Item 1 (plus Item 7 in the full run), now forecast FY2025 growth and GAAP operating margin, say whether backlog is disclosed, and quote the filing for each number, in fixed JSON.

From Claude we asked for, in order: a read of the lecture notebooks so the code would match Prof. Wu's style; a baseline and a DCF that take any growth and margin, tested on dummy numbers before real data; a check of every fixed assumption against a source; the firm-specific version after a teammate pointed out that one WACC and no capex or working capital is crude; the backlog rule applied to 28 firms; a validation of the model's output; and drafts of the memo and this log. We also asked it to rewrite comments and prose to follow our writing style guide.

### What did we change, and why was it wrong?

- The first model run leaked. `pull_filings.py` took the first 10-K filed in 2025, which for nine non-December filers was the FY2025 10-K, and the model copied actual results for J, NDSN, ROK and TDG. Found while checking filing cover dates; fixed by downloading the fiscal-2024 10-Ks and rerunning those nine.
- Claude's re-extraction of DE and DY grabbed the table of contents instead of the MD&A, and its first cover-date check read exhibit dates. We cut those two by hand and changed the check to the first "fiscal year ended" phrase.
- Claude's first quantified-backlog rule counted acquired-backlog intangibles (EME) and loose matches (EMR, OSK, RTX). We tightened it before splitting any results by it.
- Claude said the winner stayed the same under every setting. That holds when fixed assumptions change one at a time, but not when each firm gets its own inputs. Corrected in the notebook.
- The notebook called the model "reliably better" than the three-year average without testing that claim without the four flagged firms. The validation did, and it isn't; the memo says so.
- In the validation, Claude described results before running the code (it named BA among the biggest wins; it isn't), and its first check on numbers inside quotes was too loose to catch EMR's wrong margin. Both rewritten from the actual output.
- Small ones: an output column named "index", a chart title that misdescribed the fade, a printed `np.float64`.
- [Person 3: anything you changed in the model's setup after a bad answer, e.g. JSON retries or the name scrubbing.]

### How did we verify it?

Each number in the memo traces to a printed output, and each has one of Lecture 1's four checks (the full list is Part 7 of `eval/03_validation.ipynb`).

- DCF engine: `npv` matches `numpy_financial`; a numpy rewrite of the dummy firm matches the loop; the Gordon identity holds to 1e-12; the guard against terminal growth above WACC raises an error; doubling margin or revenue doubles value exactly.
- All 212 valuations recomputed as one array formula (largest gap 2.3e-15), and Caterpillar done by hand in five rounded steps ($130.64bn both ways).
- Accuracy rebuilt from the raw files and matched to four decimals; the bootstrap rerun with a different method and seed, matching within 0.05 points.
- Model output: no forecast outside sanity bounds; quotes checked two ways (89% in the filing, 97% with close paraphrases); the model's backlog read matches our separately written rule on all 53 firms; the leak probe recalled nothing; the model lands within half a point of actual no more often than "last year" does.
- Backlog rule: Agnivesh labelled AME by hand first to pin the rule down, and every other label has its source sentence on file.
- [Conor and Person 3: how you checked your parts, e.g. XBRL totals against the 10-K, the `--mock` run.]

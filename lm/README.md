# Person 3: Language model forecasts

`forecast.py` reads each firm's FY2024 10-K text (Item 1 and Item 7 from `data/filings/`), asks a language model for an FY2025 revenue growth and operating margin forecast, and saves the answers in the format Person 2's DCF notebook reads. Every answer comes back in the same fixed format with a supporting quote from the filing, and the script checks that each quote really appears in the text.

## Setup

```
pip install -r lm/requirements.txt
```

Run everything from the repo root. Pick one of these:

**Free, for UF students: NaviGator Toolkit (Llama 3.3 70B).** Every UF student gets a $100 a month credit for UF's locally hosted models, and both runs cost about $1 of it.

1. Log in at https://api.navigator.ai.ufl.edu/ui with your GatorLink.
2. Go to **Virtual Keys** and click **Create New Virtual Key**. Set **Team** to `navigator-toolkit` (a key with no team gets "model not available" errors), give it access to `llama-3.3-70b-instruct`, and create it. Copy the key right away; it's only shown once.
3. Set it, then add `--provider navigator` to every command below:

```
export NAVIGATOR_TOOLKIT_API_KEY=sk-...        # Windows PowerShell: $env:NAVIGATOR_TOOLKIT_API_KEY="sk-..."
python lm/forecast.py --provider navigator --run full --limit 3
```

If UF moves the API again, set `NAVIGATOR_BASE_URL` to the new address (it ends in `/v1`).

**Paid: Anthropic API (Claude Haiku 4.5).** A few dollars for both runs.

```
export ANTHROPIC_API_KEY=sk-ant-...      # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
```

## Running it

| Command | What it does |
| :--- | :--- |
| `python lm/forecast.py --run full --limit 3` | Try 3 firms first to check the key and the output |
| `python lm/forecast.py --run both` | Full run (Item 1 + Item 7) and the no-MD&A ablation (Item 1 only), all 53 firms |
| `python lm/forecast.py --probe` | Leak probe: asks the model, with no filing, whether it remembers each firm's actual FY2025 results |
| `python lm/forecast.py --summary` | Quick MAE of each run against the 3-yr average and last-year benchmarks |
| `python lm/forecast.py --show-prompt CAT` | Prints the exact prompt one firm gets |
| `python lm/forecast.py --run both --mock` | Offline test with fake answers, writes to `lm/output_mock/` only |

Each firm's answer is saved as soon as it comes back, so if a run stops halfway, rerun the same command and it picks up where it left off. Use `--force` to redo firms already saved (for example after changing the prompt).

Cost: the full run averages about 32k input tokens per firm and the no-MD&A run about 10k, so both runs together are a little over 2 million input tokens. At Haiku 4.5's list price that's a few dollars. Check current pricing before you run.

## Outputs

| File | Contents |
| :--- | :--- |
| `data/lm_forecasts.csv` | `ticker, label, growth, margin`. Labels are `AI full` and `AI no MD&A`. This is what Person 2's notebook picks up. |
| `lm/output/lm_forecasts_detailed.csv` | Everything: forecasts, backlog summary, both quotes, whether each quote was found in the text, reasoning, confidence, tokens, model served |
| `lm/output/raw/<run>/<TICKER>.json` | One file per firm per run, the raw answer. Kept on the computer that ran it and left out of git, since `lm_forecasts_detailed.csv` has the same fields. If you rerun without these files, the script calls the model again for every firm. |
| `lm/output/leak_probe.csv` | Probe results: does the model claim to know FY2025, what it recalls, and whether that's within 1pp of the actual |
| `lm/output/run_log.json` | Model ID, cutoffs, temperature, prompt version and hash, token totals, run time. Paste into the AI Use Log. |

After the run, open `dcf/02_dcf_baseline.ipynb` and rerun it. Both AI labels show up as new scenarios in every table.

## How the prompt works

The prompt text is in `prompt.py` so it can be copied straight into the AI Use Log. The model is told it's February 2025 and it's just read the FY2024 10-K. It gets:

1. The FY2022 to FY2024 revenue and operating margin from `master.csv`, the same numbers the 3-yr average uses. Both runs get this table, so the ablation only changes the text.
2. Item 1, and in the full run, Item 7.
3. Steps to follow: find backlog, orders, RPO and guidance; judge how much of FY2025 the backlog covers; start from history and move only with a reason; strip one-time margin items.

The model has to answer through a tool call (`record_forecast`), which forces the fixed format: growth, margin, whether backlog was disclosed, a one-line backlog summary, a growth quote, a margin quote, short reasoning and a confidence level. Temperature is 0.

Margin is defined as GAAP operating income over revenue, to match `master.csv`. Many 10-Ks talk about "adjusted" margin, so the prompt spells this out.

## The honest test and the model choice

The brief says to score only on years after the model's training cutoff. FY2025 results came out in early 2026, so the model can't have seen them if its training data stops before then. The cleaner standard is a cutoff before the 10-Ks were filed (around February 2025).

| | Llama 3.3 70B (UF NaviGator, free) | Claude Haiku 4.5 (Anthropic API) | Claude Sonnet 4 (AWS Bedrock) |
| :--- | :--- | :--- | :--- |
| Model ID | `llama-3.3-70b-instruct` | `claude-haiku-4-5-20251001` | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| Knowledge cutoff | Dec 2023 (Meta model card) | Feb 2025 reliable, Jul 2025 training data | Jan 2025 reliable, Mar 2025 training data (confirm on the system card) |
| Context window | 128k tokens | 200k | 200k |
| How to run | `--provider navigator` | default | `--provider bedrock`, needs AWS credentials and `pip install boto3` |

Llama 3.3 is the cleanest honest test: its training data stops more than a year before FY2025 started, so it can't have seen any 2025 results. It also hasn't seen 2024 news, but it reads the FY2024 10-K and the FY2024 numbers in the prompt, so that's covered. The longest prompt in the sample is about 94k tokens, under its 128k limit. NaviGator doesn't use tool calls here, so the script asks Llama for plain JSON, checks every field, and retries up to 3 times if the reply won't parse.

Every older Claude with a pre-2025 cutoff (3.5 Sonnet, 3.5 Haiku, 3.7 Sonnet) is retired from Anthropic's API, so Haiku 4.5 is the oldest Claude still callable. Neither Claude option has seen full-year FY2025 results. Haiku 4.5's training data does run into mid-2025, so it may have seen Q1 or Q2 2025 earnings for some firms. That's a partial leak and the memo should say so. Three things limit it:

1. Company names, short brand names, tickers of 3+ letters and website addresses are replaced with "the Company" before the text goes to the model. This is partial. Segment names and dollar figures still give big firms away (CAT's $64.8 billion revenue, for example).
2. The system prompt tells the model not to use anything after February 2025.
3. `--probe` asks the model directly what it remembers about each firm's FY2025. Firms where it claims to know, or recalls growth within 1pp of the actual, should be reported separately by Person 4.

## Notes for Person 4

* Record in the AI Use Log: the model ID in `run_log.json` (`model_served` is what the API actually ran), both cutoffs, temperature 0, prompt version and hash, and the run date.
* `growth_quote_verified` and `margin_quote_verified` show whether the quote was found word for word in the filing text (ignoring spacing, case and punctuation). Report the share that pass. A false here doesn't mean the forecast is wrong, but the quote shouldn't be used in the memo without checking it.
* `backlog_disclosed` is the model's own read. Compare it with `backlog_mentioned` in `master.csv`, which is a keyword flag.
* The 15 firms with no backlog mention are the control group. An edge only on backlog firms supports the thesis.
* If `AI full` beats `AI no MD&A`, management commentary is doing the work. If they're about the same, the model is mostly using the history table and Item 1.

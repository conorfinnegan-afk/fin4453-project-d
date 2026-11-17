# Person 4: Validation, memo and AI Use Log

`03_validation.ipynb` checks Person 3's model output against ground truth and recomputes Person 2's headline numbers a second way. Run it from `eval/`; it only reads files already in the repo (`data/`, `lm/output/`, `dcf/output/`) and needs `pandas` and `numpy`.

| Part | What it checks |
| :--- | :--- |
| 0 | Loads everything and prints the model ID, cutoff and prompt hash |
| 1 | One answer per firm per run, short file = detailed file, sanity bounds |
| 2 | Quotes against the filing (two methods), numbers inside quotes, the model's backlog read vs our two flags |
| 3 | Leak checks: the probe, closeness to actuals, the nine re-extracted firms |
| 4 | Accuracy rebuilt from raw files, wins firm by firm |
| 5 | A second bootstrap, plus the groups without the four flagged firms; confidence and momentum |
| 6 | Every EV recomputed as one array formula, Caterpillar by hand, the result in dollars |
| 7 | Which Lecture 1 check backs each reported number |

Outputs: `output/quote_check.csv` (one row per quote) and `output/verification_scorecard.csv`.

`MEMO_AND_AI_USE_LOG.md` is the three-sentence memo, the numbers behind it, the limitations and the AI Use Log. Lines in square brackets are for teammates to fill in.

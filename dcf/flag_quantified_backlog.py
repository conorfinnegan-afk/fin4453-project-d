"""Secondary backlog split: does the FY2024 10-K put a number on the change in backlog?

A firm counts as "quantified backlog" if Item 1 or Item 7 mentions backlog / remaining
performance obligations / unfilled orders and, in the window from 150 characters before
that mention to the end of its sentence, either
  (a) gives dollar amounts for both 2024 and 2023, or
  (b) after the mention, states a percent with a change word (increase, decrease, change, ...).
Mentions in an intangible-assets context ("contract backlog" acquired in a deal) are skipped.
The first draft matched whole sentences and picked up false positives where sentence
splitting merged a table or a neighbouring sentence (EME, EMR, OSK, RTX); it was tightened
to this window before any results were split by it. The 38/15 keyword flag in master.csv
stays the primary split.

Run from dcf/:  python flag_quantified_backlog.py   ->  backlog_quantified.csv
"""
import os
import re
import pandas as pd

FILINGS = os.path.join("..", "data", "filings")
BACKLOG = re.compile(r"(backlog|remaining performance obligation|unfilled order)", re.I)
DOLLARS = re.compile(r"\$\s?\d[\d,]*(\.\d+)?")
PCT = re.compile(r"\d+(\.\d+)?\s?(%|percent)", re.I)
DIRECTION = re.compile(r"\b(increas\w*|decreas\w*|change\w*|up|down|grew|grow\w*|declin\w*|higher|lower|rose|fell)\b", re.I)


def window(text, start, end):
    """150 characters before the mention, then on to the end of its sentence (max 400)."""
    before = text[max(0, start - 150):start]
    after = text[end:end + 400]
    stop = re.search(r"\.\s+(?=[A-Z(0-9])", after)
    if stop:
        after = after[:stop.start() + 1]
    return before, after


def quantified(text):
    """Window that meets the rule, or None."""
    text = re.sub(r"\s+", " ", text)
    for m in BACKLOG.finditer(text):
        before, after = window(text, m.start(), m.end())
        whole = before + m.group(0) + after
        if re.search(r"intangible", whole, re.I):
            continue
        both_years = "2024" in whole and "2023" in whole and len(DOLLARS.findall(whole)) >= 2
        pct_change = PCT.search(after) and DIRECTION.search(after)
        if both_years or pct_change:
            return whole
    return None


master = pd.read_csv(os.path.join("..", "data", "master.csv"))
rows = []
for tk in master["ticker"]:
    text = ""
    for item in ["item7", "item1"]:
        path = os.path.join(FILINGS, f"{tk}_{item}.txt")
        if os.path.exists(path):
            text = text + " " + open(path, encoding="utf-8", errors="ignore").read()
    hit = quantified(text)
    rows.append({"ticker": tk, "quantified_backlog": hit is not None, "evidence": (hit or "")[:400]})

out = pd.DataFrame(rows)
out.to_csv("backlog_quantified.csv", index=False)
flag = master.set_index("ticker")["backlog_mentioned"]
q = out.set_index("ticker")["quantified_backlog"]
print(f"quantified backlog: {q.sum()} of {len(q)}")
print(pd.crosstab(flag.rename("keyword flag"), q.rename("quantified")))

# Project D, Person 3: language model forecasts.
# 10-K text in, structured FY2025 growth and margin forecasts out.
#
# Run from the repo root:
#   python lm/forecast.py --run both            # full text and no-MD&A runs
#   python lm/forecast.py --run full --limit 3  # quick test on 3 firms
#   python lm/forecast.py --probe               # leak probe (no filing text)
#   python lm/forecast.py --summary             # MAE vs the 3-yr baseline
#   python lm/forecast.py --run both --mock     # offline test, no API calls
#
# Needs ANTHROPIC_API_KEY in the environment (or AWS credentials with --provider bedrock).

import argparse, datetime, hashlib, json, os, re, sys, time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt as P

# ---- settings -------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "data", "master.csv")
OUT_DIR = os.path.join(ROOT, "lm", "output")
HANDOFF_CSV = os.path.join(ROOT, "data", "lm_forecasts.csv")   # format Person 2's notebook reads
BASELINE_CSV = os.path.join(ROOT, "dcf", "output", "baseline_forecasts.csv")

PROVIDER = "anthropic"
MODEL = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.0          # same answer every time, as far as the API allows
MAX_TOKENS = 1500
MAX_CHARS = 350_000        # per section; longest Item 7 in the sample is ~322k chars
ANONYMIZE = True

# Cutoffs from Anthropic's model pages (checked 15 Nov 2026). Goes into run_log.json.
MODEL_INFO = {
    "claude-haiku-4-5-20251001": {"reliable_knowledge_cutoff": "Feb 2025", "training_data_cutoff": "Jul 2025",
                                  "source": "https://platform.claude.com/docs/en/models/haiku-4-5/overview"},
    "us.anthropic.claude-sonnet-4-20250514-v1:0": {"reliable_knowledge_cutoff": "Jan 2025", "training_data_cutoff": "Mar 2025",
                                  "source": "Anthropic Sonnet 4 system card; confirm before citing"},
}

RUNS = {"full": {"label": "AI full", "item7": True},
        "no_mdna": {"label": "AI no MD&A", "item7": False}}

# Extra names to scrub, beyond the name in master.csv. Short brand names
# the filings use for themselves.
ALIASES = {
    "GWW": ["Grainger"], "PH": ["Parker"], "DD": ["DuPont"], "CARR": ["Carrier"], "HII": ["Huntington Ingalls"],
    "JCI": ["Johnson Controls"], "WAB": ["Wabtec", "Westinghouse Air Brake"], "LMT": ["Lockheed"],
    "NOC": ["Northrop"], "ROK": ["Rockwell"], "TT": ["Trane"], "AWI": ["Armstrong"], "WTS": ["Watts"],
    "FIX": ["Comfort Systems"], "DE": ["John Deere", "Deere"], "J": ["Jacobs"], "EME": ["EMCOR"],
    "AME": ["AMETEK"], "MMM": ["3M"], "RTX": ["Raytheon"], "OTIS": ["Otis"], "AXON": ["Axon"],
    "LECO": ["Lincoln Electric"], "HWM": ["Howmet"], "ITW": ["ITW"], "IR": ["Ingersoll Rand"],
}
SUFFIXES = r"(,?\s+(Inc\.?|Incorporated|Corporation|Corp\.?|Company|Co\.|Holdings|Group|Global|Worldwide|Solutions|Enterprise|International|Industries|plc|Ltd\.?|& Company|de Nemours))+$"


# ---- text prep ------------------------------------------------------------
def read_text(rel_path):
    path = os.path.join(ROOT, rel_path)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def name_variants(ticker, name):
    core = re.sub(SUFFIXES, "", name.strip(), flags=re.I).strip()
    names = [name.strip(), core] + ALIASES.get(ticker, [])
    names = [n for n in names if len(n) >= 2]
    return sorted(set(names), key=len, reverse=True)     # longest first so "Deere & Company" goes before "Deere"


def scrub(text, ticker, name):
    """Replace the company's own name and ticker with 'the Company'."""
    for n in name_variants(ticker, name):
        flags = re.I if len(n) >= 5 else 0                # short names: exact case only
        text = re.sub(r"(?<![\w&])" + re.escape(n) + r"(?![\w&])", "the Company", text, flags=flags)
    if len(ticker) >= 3:
        text = re.sub(r"\b" + re.escape(ticker) + r"\b", "the Company", text)
    text = re.sub(r"\b(?:https?://|www\.)\S+", "[website]", text)    # URLs give the name away
    text = re.sub(r"(the Company)(\s+the Company)+", r"\1", text)
    return text


def history_table(row):
    lines = ["Fiscal year | Revenue ($ millions) | Operating margin"]
    for k, fy in [(3, 2022), (2, 2023), (1, 2024)]:
        rev = row[f"revenue_fy_minus_{k}"] / 1e6
        mar = row[f"margin_fy_minus_{k}"]
        lines.append(f"FY{fy} | {rev:,.0f} | {mar:.1%}")
    g23 = row["revenue_fy_minus_2"] / row["revenue_fy_minus_3"] - 1
    g24 = row["revenue_fy_minus_1"] / row["revenue_fy_minus_2"] - 1
    lines.append(f"Revenue growth: FY2023 {g23:+.1%}, FY2024 {g24:+.1%}")
    return "\n".join(lines)


def build_prompt(row, use_item7, anonymize=ANONYMIZE):
    parts = [("ITEM 1. BUSINESS", row["item1_path"])]
    if use_item7:
        parts.append(("ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS (MD&A)", row["item7_path"]))
    sections, source = [], []
    for title, rel in parts:
        txt = read_text(rel)[:MAX_CHARS]
        if anonymize:
            txt = scrub(txt, row["ticker"], row["name"])
        source.append(txt)
        sections.append(f"=== {title} (FY2024 10-K) ===\n{txt}")
    user = P.USER.format(history=history_table(row), sections="\n\n".join(sections))
    return user, "\n".join(source)


# ---- quote check ----------------------------------------------------------
def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    return re.sub(r"[^a-z0-9%$.]+", " ", s.lower()).strip()


def quote_found(quote, source):
    """True if the quote appears in the text (ignoring spacing, case and punctuation)."""
    q = norm(quote).strip(" .")
    return len(q) > 0 and q in norm(source)


# ---- model calls ----------------------------------------------------------
def make_client(provider):
    import anthropic
    if provider == "bedrock":
        return anthropic.AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"), max_retries=6)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. See lm/README.md.")
    return anthropic.Anthropic(max_retries=6)


def call_tool(client, model, system, user, tool):
    msg = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, system=system,
        tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            return block.input, msg.usage.input_tokens, msg.usage.output_tokens, msg.model
    raise ValueError("model did not call the tool")


def mock_forecast(row, source):
    """Offline stand-in: 3-yr average plus a real backlog sentence, so the plumbing can be tested."""
    g = ((row["revenue_fy_minus_2"] / row["revenue_fy_minus_3"] - 1) + (row["revenue_fy_minus_1"] / row["revenue_fy_minus_2"] - 1)) / 2
    m = (row["margin_fy_minus_3"] + row["margin_fy_minus_2"] + row["margin_fy_minus_1"]) / 3
    hit = re.search(r"[^.\n]*backlog[^.\n]*\.", source, flags=re.I)
    q = hit.group(0).strip() if hit else source[:150]
    return {"revenue_growth_fy2025": g, "operating_margin_fy2025": m, "backlog_disclosed": bool(hit),
            "backlog_summary": "mock", "growth_quote": q, "margin_quote": q,
            "reasoning": "mock run", "confidence": "low"}, 0, 0, "mock"


# ---- main runs ------------------------------------------------------------
def slug(label):
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def run_forecasts(df, run_key, client, model, mock=False, force=False):
    label, use7 = RUNS[run_key]["label"], RUNS[run_key]["item7"]
    raw_dir = os.path.join(OUT_DIR, "raw", slug(label))
    os.makedirs(raw_dir, exist_ok=True)
    rows = []
    for i, row in df.iterrows():
        t = row["ticker"]
        path = os.path.join(raw_dir, f"{t}.json")
        if os.path.exists(path) and not force:                # resume: skip firms already done
            with open(path) as f:
                rec = json.load(f)
        else:
            user, source = build_prompt(row, use7)
            # 1. call the model (or the mock)
            if mock:
                out, tin, tout, served = mock_forecast(row, source)
            else:
                out, tin, tout, served = call_tool(client, model, P.SYSTEM, user, P.TOOL)
            # 2. check the quotes against the text the model saw
            rec = {"ticker": t, "label": label, "model": served, "prompt_version": P.PROMPT_VERSION,
                   "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "input_tokens": tin, "output_tokens": tout, **out,
                   "growth_quote_verified": quote_found(out["growth_quote"], source),
                   "margin_quote_verified": quote_found(out["margin_quote"], source)}
            with open(path, "w") as f:
                json.dump(rec, f, indent=2)
            if not mock:
                time.sleep(0.5)
        rows.append(rec)
        print(f"{label:<11} {t:<5} growth {rec['revenue_growth_fy2025']:+7.1%}  margin {rec['operating_margin_fy2025']:6.1%}"
              f"  backlog {str(rec['backlog_disclosed']):<5}  quotes ok {rec['growth_quote_verified']}/{rec['margin_quote_verified']}")
    return rows


def sanity(rows):
    """Flag answers that look like a units mistake (e.g. 6 instead of 0.06)."""
    bad = [r["ticker"] + " " + r["label"] for r in rows
           if abs(r["revenue_growth_fy2025"]) > 1 or abs(r["operating_margin_fy2025"]) > 1]
    if bad:
        print("WARNING, check these (|value| > 100%):", ", ".join(bad))
    n = len(rows)
    ok = sum(r["growth_quote_verified"] and r["margin_quote_verified"] for r in rows)
    print(f"Quotes found word for word in the 10-K text: {ok} of {n} forecasts")


def save_outputs(rows):
    det = pd.DataFrame(rows)
    det.to_csv(os.path.join(OUT_DIR, "lm_forecasts_detailed.csv"), index=False)
    short = det[["ticker", "label", "revenue_growth_fy2025", "operating_margin_fy2025"]]
    short = short.rename(columns={"revenue_growth_fy2025": "growth", "operating_margin_fy2025": "margin"})
    short.to_csv(HANDOFF_CSV, index=False)
    print(f"Saved {len(short)} rows to {os.path.relpath(HANDOFF_CSV, ROOT)} and {os.path.relpath(OUT_DIR, ROOT)}/lm_forecasts_detailed.csv")


def write_log(args, model, rows):
    info = MODEL_INFO.get(model, {})
    log = {"model_requested": model, "model_served": sorted({r["model"] for r in rows}),
           "provider": args.provider, "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
           "anonymized": ANONYMIZE, "prompt_version": P.PROMPT_VERSION,
           "prompt_sha256": hashlib.sha256((P.SYSTEM + P.USER + json.dumps(P.TOOL)).encode()).hexdigest()[:16],
           "runs": sorted({r["label"] for r in rows}), "firms": len({r["ticker"] for r in rows}),
           "input_tokens": int(sum(r["input_tokens"] for r in rows)),
           "output_tokens": int(sum(r["output_tokens"] for r in rows)),
           "run_finished": datetime.datetime.now().isoformat(timespec="seconds"),
           "mock": args.mock, **info}
    with open(os.path.join(OUT_DIR, "run_log.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(f"Run log saved: {log['input_tokens']:,} input tokens, {log['output_tokens']:,} output tokens")


def run_probe(df, client, model, mock=False):
    rows = []
    for i, row in df.iterrows():
        user = P.PROBE_USER.format(name=row["name"], ticker=row["ticker"])
        if mock:
            out = {"knows_actual_fy2025": False, "recalled_growth": None, "recalled_margin": None, "latest_period_known": "mock"}
        else:
            out, tin, tout, served = call_tool(client, model, P.PROBE_SYSTEM, user, P.PROBE_TOOL)
        g = out.get("recalled_growth")
        close = g is not None and abs(g - row["actual_revenue_growth"]) < 0.01
        rows.append({"ticker": row["ticker"], **out, "actual_growth": row["actual_revenue_growth"],
                     "recall_within_1pp": close})
        print(f"{row['ticker']:<5} knows FY2025: {str(out['knows_actual_fy2025']):<5} recalled {g}  actual {row['actual_revenue_growth']:+.1%}  latest known: {out['latest_period_known']}")
    probe = pd.DataFrame(rows)
    probe.to_csv(os.path.join(OUT_DIR, "leak_probe.csv"), index=False)
    print(f"Claims to know FY2025: {int(probe.knows_actual_fy2025.sum())} of {len(probe)}. "
          f"Recalled growth within 1pp of actual: {int(probe.recall_within_1pp.sum())}")


def summary():
    if not os.path.exists(HANDOFF_CSV):
        sys.exit("No data/lm_forecasts.csv yet. Run --run both first.")
    lm = pd.read_csv(HANDOFF_CSV)
    base = pd.read_csv(BASELINE_CSV).set_index("ticker")
    print(f"{'forecast':<14}{'group':<12}{'n':>4}{'growth MAE':>12}{'margin MAE':>12}")
    sets = [("3-yr average", base["base_growth"], base["base_margin"]),
            ("last year", base["last_growth"], base["last_margin"])]
    for label, g in lm.groupby("label"):
        g = g.set_index("ticker")
        sets.append((label, g["growth"], g["margin"]))
    for name, gr, mr in sets:
        for grp, mask in [("all", base.index), ("backlog", base.index[base.backlog]), ("no backlog", base.index[~base.backlog])]:
            idx = [t for t in mask if t in gr.index]
            ge = (gr[idx] - base.loc[idx, "actual_growth"]).abs().mean()
            me = (mr[idx] - base.loc[idx, "actual_margin"]).abs().mean()
            print(f"{name:<14}{grp:<12}{len(idx):>4}{ge:>12.2%}{me:>12.2%}")
    print("Person 4 owns the official scoring. This is a quick look only.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", choices=["full", "no_mdna", "both"])
    ap.add_argument("--probe", action="store_true", help="leak probe: can the model recall FY2025 actuals?")
    ap.add_argument("--summary", action="store_true", help="print MAE vs the baselines")
    ap.add_argument("--provider", default=PROVIDER, choices=["anthropic", "bedrock"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--tickers", default=None, help="comma list, e.g. CAT,BA")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--mock", action="store_true", help="no API calls; tests the pipeline")
    ap.add_argument("--force", action="store_true", help="redo firms already saved")
    ap.add_argument("--show-prompt", default=None, metavar="TICKER", help="print the full prompt for one firm and stop")
    args = ap.parse_args()

    global OUT_DIR, HANDOFF_CSV
    if args.mock:                                   # keep test output away from the real files
        OUT_DIR = os.path.join(ROOT, "lm", "output_mock")
        HANDOFF_CSV = os.path.join(OUT_DIR, "lm_forecasts.csv")
    df = pd.read_csv(MASTER)
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.show_prompt:
        row = df[df.ticker == args.show_prompt].iloc[0]
        print(P.SYSTEM + "\n\n" + build_prompt(row, True)[0])
        return
    if args.summary:
        summary()
        return
    if args.tickers:
        df = df[df.ticker.isin(args.tickers.split(","))]
    if args.limit:
        df = df.head(args.limit)

    model = args.model or ("us.anthropic.claude-sonnet-4-20250514-v1:0" if args.provider == "bedrock" else MODEL)
    client = None if args.mock else make_client(args.provider)
    print(f"Model: {model}   provider: {args.provider}   firms: {len(df)}   mock: {args.mock}")

    if args.probe:
        run_probe(df, client, model, args.mock)
    if args.run:
        keys = ["full", "no_mdna"] if args.run == "both" else [args.run]
        for k in keys:
            run_forecasts(df, k, client, model, args.mock, args.force)
        # rebuild the outputs from every saved answer, so partial runs add up
        rows = []
        for k in RUNS:
            d = os.path.join(OUT_DIR, "raw", slug(RUNS[k]["label"]))
            if os.path.isdir(d):
                for fn in sorted(os.listdir(d)):
                    with open(os.path.join(d, fn)) as f:
                        rows.append(json.load(f))
        sanity(rows)
        save_outputs(rows)
        write_log(args, model, rows)


if __name__ == "__main__":
    main()

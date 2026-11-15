# Prompt text for the Project D language model forecasts.
# Kept in its own file so the exact wording can be pasted into the AI Use Log.
# Change it here, not in forecast.py, and bump PROMPT_VERSION when you do.

PROMPT_VERSION = "v1.0"

SYSTEM = """You are an equity research analyst who covers US industrial companies.
The date is February 2025. The company has just filed its FY2024 annual report (Form 10-K).
You only know what is in the excerpts you are given and what was public before the filing.
Do not use any knowledge of events, results or prices after February 2025.
The company's name has been replaced with "the Company" on purpose. Do not try to identify it."""

USER = """Below are the company's reported results for the last three fiscal years, followed by text from its FY2024 10-K.

Your job: forecast the company's FY2025 total revenue growth and FY2025 operating margin.

Definitions (use these exactly, they match the history table):
- Revenue growth = FY2025 total revenue / FY2024 total revenue - 1
- Operating margin = GAAP operating income / total revenue. Not "adjusted" or "segment" margin.

How to work:
1. Look for forward-looking demand signals: backlog, order book, remaining performance obligations (RPO), book-to-bill, orders growth, funded vs unfunded backlog, and any FY2025 outlook or guidance management gives.
2. Ask how much of FY2025 revenue the backlog already covers, and whether orders are rising or falling.
3. Start from the history table, then move away from it only when the text gives you a reason.
4. For margin, look for pricing, cost, restructuring, mix and one-time charge comments. Strip out one-time items that will not repeat.
5. Back each forecast with one quote copied word for word from the 10-K text below. Keep each quote under 40 words. Do not paraphrase inside the quote.
6. If the filing has no backlog or order disclosure, set backlog_disclosed to false and say what you relied on instead.

Give growth and margin as decimals (0.05 means 5%). Call the record_forecast tool once with your answer.

=== REPORTED HISTORY (from SEC XBRL data) ===
{history}

{sections}"""

# Fixed output format. The model has to call this tool, so every answer
# comes back with the same fields.
TOOL = {
    "name": "record_forecast",
    "description": "Record the FY2025 forecast for this company.",
    "input_schema": {
        "type": "object",
        "properties": {
            "revenue_growth_fy2025": {"type": "number", "description": "FY2025 revenue growth as a decimal, e.g. 0.06"},
            "operating_margin_fy2025": {"type": "number", "description": "FY2025 GAAP operating margin as a decimal, e.g. 0.15"},
            "backlog_disclosed": {"type": "boolean", "description": "True if the text gives a backlog, order book or RPO figure or trend"},
            "backlog_summary": {"type": "string", "description": "One sentence: the backlog or order number and its trend, or 'none disclosed'"},
            "growth_quote": {"type": "string", "description": "Exact quote from the 10-K text that best supports the growth forecast"},
            "margin_quote": {"type": "string", "description": "Exact quote from the 10-K text that best supports the margin forecast"},
            "reasoning": {"type": "string", "description": "Two to four sentences on how you got from the history to the forecast"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["revenue_growth_fy2025", "operating_margin_fy2025", "backlog_disclosed",
                     "backlog_summary", "growth_quote", "margin_quote", "reasoning", "confidence"],
    },
}

# Leak probe: same model, no filing text, real company name.
# If the model can recall FY2025 results from memory, the honest test is compromised for that firm.
PROBE_SYSTEM = "Answer from your own training knowledge only. If you do not know, say so. Do not guess to be helpful."

PROBE_USER = """Company: {name} (ticker {ticker}).
1. Do you know this company's actual reported total revenue for fiscal year 2025 (the full year, not a forecast)?
2. If yes, what was its FY2025 revenue growth versus FY2024, and its FY2025 GAAP operating margin?
Call the record_recall tool once."""

PROBE_TOOL = {
    "name": "record_recall",
    "description": "Record what you remember about the company's actual FY2025 results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "knows_actual_fy2025": {"type": "boolean"},
            "recalled_growth": {"type": ["number", "null"], "description": "Decimal, or null if unknown"},
            "recalled_margin": {"type": ["number", "null"], "description": "Decimal, or null if unknown"},
            "latest_period_known": {"type": "string", "description": "Most recent quarter or year of this company's results you remember, e.g. 'FY2024' or 'Q2 2025'"},
        },
        "required": ["knows_actual_fy2025", "recalled_growth", "recalled_margin", "latest_period_known"],
    },
}

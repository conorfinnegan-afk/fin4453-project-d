"""Market data for the firm-specific DCF scenario and the price appendix.

For each firm, as of the valuation date (end of February 2025, after the FY2024
10-Ks were filed): closing price, 52-week high and low, and beta from two years of
weekly returns against the S&P 500. Nothing after the valuation date is used.

Needs: pip install yfinance
Writes data/market_data.csv.
"""
import os
import pandas as pd
import yfinance as yf

DATA_DIR = "data"
VAL_DATE = "2025-02-28"          # valuation date: every FY2024 10-K was public by then
MARKET = "^GSPC"                  # S&P 500 index


def weekly_returns(prices):
    """Friday-to-Friday returns from a daily close series."""
    return prices.resample("W-FRI").last().pct_change().dropna()


def beta(stock_ret, mkt_ret):
    """Slope of stock on market: cov / var, plus the Blume adjustment (0.67 raw + 0.33)."""
    both = pd.concat([stock_ret, mkt_ret], axis=1, join="inner").dropna()
    both.columns = ["s", "m"]
    raw = both["s"].cov(both["m"]) / both["m"].var()
    return raw, 0.67 * raw + 0.33, len(both)


def closes(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    col = df["Close"]
    if isinstance(col, pd.DataFrame):          # newer yfinance returns one column per ticker
        col = col.iloc[:, 0]
    return col.dropna()


def main():
    val = pd.Timestamp(VAL_DATE)
    stop = val + pd.Timedelta(days=1)          # yfinance 'end' is exclusive
    tickers = pd.read_csv(os.path.join(DATA_DIR, "master.csv"))["ticker"].tolist()

    mkt = closes(MARKET, val - pd.DateOffset(years=2, days=7), stop)
    mkt_ret = weekly_returns(mkt)

    rows = []
    for tk in tickers:
        print(f"{tk}: downloading prices...")
        try:
            px = closes(tk, val - pd.DateOffset(years=2, days=7), stop)
            last_year = px[px.index > val - pd.DateOffset(weeks=52)]
            raw, adj, n = beta(weekly_returns(px), mkt_ret)
            rows.append({"ticker": tk, "price_date": px.index[-1].date(), "close": px.iloc[-1],
                         "high_52w": last_year.max(), "low_52w": last_year.min(),
                         "beta_raw": raw, "beta_adj": adj, "beta_weeks": n})
        except Exception as e:
            print(f"  FAILED {tk}: {e}")
            rows.append({"ticker": tk, "note": str(e)})

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA_DIR, "market_data.csv"), index=False)
    ok = out["close"].notna().sum() if "close" in out else 0
    print(f"\nDone: prices for {ok} of {len(tickers)} firms, valuation date {VAL_DATE}")
    print(out[["ticker", "close", "low_52w", "high_52w", "beta_adj"]].head().round(2).to_string(index=False))


if __name__ == "__main__":
    main()

import os
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {"User-Agent": "UF FIN4453 Capstone Team c.finnegan@ufl.edu"}
DATA_DIR = "data"
FILINGS_DIR = os.path.join(DATA_DIR, "filings")
os.makedirs(FILINGS_DIR, exist_ok=True)

BACKLOG_PATTERN = re.compile(
    r"\b(backlog|order\s+book|unfilled\s+orders|booked\s+orders|remaining\s+performance\s+obligations?)\b",
    re.I
)

def get_ex_ante_10k_url(cik):
    """
    Finds the 10-K filed in early 2025 (covering FY2024).
    This serves as the ex-ante filing to predict FY2025 outcomes with zero look-ahead bias.
    """
    cik_padded = str(cik).zfill(10)
    sub_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    r = requests.get(sub_url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    acc_nums = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    
    # Target 10-K filed in calendar 2025 or late 2024
    for idx, form in enumerate(forms):
        if form == "10-K":
            date = filing_dates[idx]
            if date.startswith("2025") or (date.startswith("2024") and int(date[5:7]) >= 7):
                acc_num = acc_nums[idx]
                acc_clean = acc_num.replace("-", "")
                doc_name = primary_docs[idx]
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc_name}"
                return doc_url, acc_num, date
                
    # Fallback to latest regular 10-K
    for idx, form in enumerate(forms):
        if form == "10-K":
            acc_num = acc_nums[idx]
            acc_clean = acc_num.replace("-", "")
            doc_name = primary_docs[idx]
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc_name}"
            return doc_url, acc_num, filing_dates[idx]

    raise ValueError(f"No regular 10-K found for CIK {cik}")

def clean_html_to_text(html_bytes):
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    raw = soup.get_text(separator="\n")
    cleaned = raw.replace("\xa0", " ").replace("&nbsp;", " ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
    return cleaned

def is_toc_or_xref(text, sm_start, sm_end):
    # 1. Cross-reference check backward
    backward = text[max(0, sm_start - 60):sm_start].lower()
    if re.search(r"\b(see|refer\s+to|included\s+in|discussed\s+in|described\s+in)\b", backward):
        return True
        
    # 2. Quotation mark check immediately following title
    forward_short = text[sm_end:sm_end + 25].strip()
    if forward_short.startswith(('"', "“", "'", "”")):
        return True
        
    # 3. Table of Contents check forward:
    # In a TOC, an adjacent Item (1A, 2, 7A, 8) appears within 350 chars,
    # or a standalone page number on its own line (e.g. "\n27\n") is present
    forward_snippet = text[sm_end:sm_end + 350]
    if re.search(r"\bitem\s+(?:1a|2|3|4|7a|8|9|10)\b", forward_snippet, re.I):
        return True
    if re.search(r"(?:\.{3,}|\n\s*\d{1,3}\s*\n)", forward_snippet):
        if re.search(r"\bitem\s+", forward_snippet, re.I):
            return True
            
    return False

def extract_section(text, item_num, next_items, title_pattern_str, min_chars=12000, max_chars=350000):
    pattern_start = re.compile(
        rf"(?:^|\n)\s*(?:part\s+(?:i|ii)[\s,]+)?item\s+{item_num}\b[.\s–—:-]*(?:{title_pattern_str})?",
        re.I
    )
    pattern_end = re.compile(
        rf"(?:^|\n)\s*(?:part\s+(?:i|ii)[\s,]+)?item\s+(?:{'|'.join(next_items)})\b",
        re.I
    )

    start_matches = list(pattern_start.finditer(text))
    end_matches = list(pattern_end.finditer(text))

    # Exclude Table of Contents lines and cross-references
    valid_starts = [sm for sm in start_matches if not is_toc_or_xref(text, sm.start(), sm.end())]
    if not valid_starts:
        valid_starts = start_matches

    candidates = []
    for sm in valid_starts:
        s = sm.start()
        for em in end_matches:
            e = em.start()
            if e > s:
                length = e - s
                # Do not stop at a TOC entry for the next item
                if is_toc_or_xref(text, em.start(), em.end()):
                    continue
                if min_chars <= length <= max_chars:
                    cand = text[s:e].strip()
                    candidates.append((length, s, cand))
                    break

    if candidates:
        # Prioritize the full narrative section
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2], "high confidence"

    # Fallback to any span >= 2500 chars
    for sm in valid_starts:
        s = sm.start()
        for em in end_matches:
            e = em.start()
            if 2500 <= (e - s) <= max_chars:
                if not is_toc_or_xref(text, em.start(), em.end()):
                    return text[s:e].strip(), "low confidence"

    return "", "no_match"

def main():
    firm_list_path = os.path.join(DATA_DIR, "firm_list.csv")
    firms = pd.read_csv(firm_list_path)
    log_rows = []

    for _, row in firms.iterrows():
        ticker = row["ticker"]
        cik = row["cik"]
        print(f"{ticker}: fetching filing index...")
        time.sleep(0.12)

        try:
            url, acc, f_date = get_ex_ante_10k_url(cik)
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()

            text = clean_html_to_text(r.content)
            
            item1, i1_conf = extract_section(
                text, "1", ["1a", "2"], r"business|our\s+business", min_chars=5000
            )
            item7, i7_conf = extract_section(
                text, "7", ["7a", "8"], r"management(?:['’]|&#39;)?s\s+discussion", min_chars=12000
            )

            backlog_flag = bool(BACKLOG_PATTERN.search(item1) or BACKLOG_PATTERN.search(item7))

            with open(os.path.join(FILINGS_DIR, f"{ticker}_item1.txt"), "w", encoding="utf-8") as f:
                f.write(item1)
            with open(os.path.join(FILINGS_DIR, f"{ticker}_item7.txt"), "w", encoding="utf-8") as f:
                f.write(item7)

            print(f"  -> item1: {len(item1)} chars ({i1_conf}), item7: {len(item7)} chars ({i7_conf}), backlog={backlog_flag}")
            log_rows.append({
                "ticker": ticker,
                "status": "success" if (len(item1) >= 1000 and len(item7) >= 1000) else "failed",
                "item1_len": len(item1),
                "item1_confidence": i1_conf,
                "item7_len": len(item7),
                "item7_confidence": i7_conf,
                "backlog": backlog_flag,
                "filing_date": f_date
            })
        except Exception as e:
            print(f"  FAILED {ticker}: {str(e)}")
            log_rows.append({
                "ticker": ticker,
                "status": "failed",
                "item1_len": 0,
                "item1_confidence": "failed",
                "item7_len": 0,
                "item7_confidence": "failed",
                "backlog": False,
                "filing_date": None
            })

    pd.DataFrame(log_rows).to_csv(os.path.join(DATA_DIR, "extraction_log.csv"), index=False)
    print("Full log: data/extraction_log.csv")

if __name__ == "__main__":
    main()
from __future__ import annotations

"""Financial Data Ingestion Agent."""
import json
import re
import numpy as np
import pandas as pd

def _parse_amount(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return np.nan
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace("₹", "").replace("$", "").replace(",", "").replace(" ", "")
    text = text.replace("CR", "").replace("DR", "")
    if text.lower().startswith("dr"):
        negative = True
        text = text[2:]
    if text.lower().startswith("cr"):
        text = text[2:]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if text.startswith("+"):
        text = text[1:]
    try:
        number = float(text)
    except ValueError:
        try:
            number = float(text.replace("-", ""))
        except ValueError:
            return np.nan
    return -abs(number) if negative else abs(number)


def parse_pdf_text(raw_text):
    rows = []
    for line in str(raw_text).splitlines():
        line = line.strip()
        if not line or line.lower().startswith("statement"):
            continue
        match = re.search(r"(\d{1,2}[/-][A-Za-z]{3,9}[/-]\d{2,4})\s*,\s*([^,]+?)\s*,\s*(.+)", line)
        if not match:
            continue
        date_str, merchant, amount_text = match.groups()
        amount = _parse_amount(amount_text)
        if pd.isna(amount):
            continue
        rows.append({
            "date": date_str,
            "merchant": merchant.strip().title(),
            "amount": float(amount),
            "type": "debit" if amount < 0 else "credit",
        })
    return rows


def parse_pdf_file(file_path_or_bytes):
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required to parse PDF statements. Install it with pip install pdfplumber.") from exc

    if isinstance(file_path_or_bytes, (bytes, bytearray)):
        import io
        text = ""
        with pdfplumber.open(io.BytesIO(file_path_or_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or "\n"
        return pd.DataFrame(parse_pdf_text(text))

    with pdfplumber.open(file_path_or_bytes) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    return pd.DataFrame(parse_pdf_text(text))


# ---- Agent 1: Data Ingestion -------------------------------------------------
def ingest(src):
    if isinstance(src, (bytes, bytearray)):
        return parse_pdf_file(src)
    if isinstance(src, str) and src.lower().endswith(".pdf"):
        return parse_pdf_file(src)
    if isinstance(src, pd.DataFrame):
        df = src.copy()
    elif isinstance(src, list):
        df = pd.DataFrame.from_records(src)
    elif isinstance(src, dict):
        account = src.get("Account")
        if isinstance(account, dict) and isinstance(account.get("Transactions"), dict):
            payload = account["Transactions"].get("Transaction", [])
        else:
            payload = next(
                (src[key] for key in ("transactions", "data", "records", "results", "items") if key in src),
                src,
            )
        if isinstance(payload, list):
            df = pd.DataFrame.from_records(payload)
        elif isinstance(payload, dict):
            if payload and all(isinstance(value, dict) for value in payload.values()):
                df = pd.DataFrame.from_dict(payload, orient="index")
            else:
                df = pd.DataFrame(payload)
        else:
            raise ValueError("JSON statement must contain transaction records.")
    elif isinstance(src, str) and src.lower().endswith(".json"):
        with open(src, "r", encoding="utf-8") as f:
            return ingest(json.load(f))
    else:
        df = pd.read_csv(src)

    df.columns = [str(c).strip().lower() for c in df.columns]
    alias = {"narration": "description", "merchant": "description", "details": "description", "txn date": "date", "txn_date": "date", "value date": "date", "valuedate": "date", "posted date": "date", "transaction date": "date", "transaction_date": "date", "transactiondate": "date", "transaction timestamp": "date", "transactiontimestamp": "date", "transaction_type": "type", "transaction type": "type", "transactiontype": "type", "txn_type": "type", "txn type": "type", "direction": "type", "debit": "debit_amt", "credit": "credit_amt", "debit_amt": "debit_amt", "credit_amt": "credit_amt"}
    df = df.rename(columns={k: v for k, v in alias.items() if k in df.columns})
    if not df.columns.is_unique:
        df = pd.concat(
            [df.loc[:, df.columns == column].bfill(axis=1).iloc[:, 0].rename(column) for column in dict.fromkeys(df.columns)],
            axis=1,
        )

    if "amount" in df.columns:
        df["amount"] = df["amount"].apply(_parse_amount)
    if "debit_amt" in df.columns or "credit_amt" in df.columns:
        debit = pd.to_numeric(df.get("debit_amt"), errors="coerce").fillna(0)
        credit = pd.to_numeric(df.get("credit_amt"), errors="coerce").fillna(0)
        df["amount"] = debit + credit
        df["type"] = np.where(credit > 0, "credit", "debit")
    if "debit_amt" in df.columns:
        df["debit_amt"] = df["debit_amt"].apply(_parse_amount)
    if "credit_amt" in df.columns:
        df["credit_amt"] = df["credit_amt"].apply(_parse_amount)

    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df.index, errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if isinstance(df["date"].dtype, pd.DatetimeTZDtype):
        df["date"] = df["date"].dt.tz_localize(None)
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce")
    if "type" not in df.columns:
        if "debit_amt" in df.columns and "credit_amt" in df.columns:
            df["type"] = np.where(df["credit_amt"] > 0, "credit", "debit")
        else:
            df["type"] = np.where(df["amount"] < 0, "debit", "credit")
    df["type"] = df["type"].fillna("debit").astype(str).str.lower().str.strip()
    df["type"] = df["type"].replace({"expense": "debit", "expenses": "debit", "withdrawal": "debit", "withdraw": "debit", "payment": "debit", "purchase": "debit", "outflow": "debit", "dr": "debit", "income": "credit", "deposit": "credit", "receipt": "credit", "inflow": "credit", "cr": "credit"})
    df["amount"] = df["amount"].fillna(0).abs()

    desc_col = next((c for c in ["description", "merchant", "narration", "details", "particulars"] if c in df.columns), None)
    if desc_col is None:
        df["description"] = "Unknown"
        desc_col = "description"
    df["merchant"] = df[desc_col].fillna("Unknown").astype(str).str.strip().str.title()
    df = df.dropna(subset=["date", "amount"]).sort_values("date").reset_index(drop=True)
    keep = ["date", "merchant", "amount", "type"] + (["true_category"] if "true_category" in df.columns else [])
    return df[keep]

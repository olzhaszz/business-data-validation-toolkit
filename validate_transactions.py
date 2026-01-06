import argparse
import json
import os
from dataclasses import dataclass
from typing import List, Dict

import numpy as np
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check


@dataclass
class Issue:
    issue_type: str
    severity: str
    row_count: int
    owner: str
    recommended_fix: str


def build_schema() -> DataFrameSchema:
    # NOTE: We keep schema rules business-friendly and not overly strict.
    return DataFrameSchema(
        {
            "InvoiceNo": Column(str, nullable=False),
            "StockCode": Column(str, nullable=False),
            "Description": Column(str, nullable=True),
            "Quantity": Column(float, nullable=False),
            "InvoiceDate": Column(object, nullable=False),  # parsed later
            "UnitPrice": Column(float, nullable=False),
            "CustomerID": Column(float, nullable=True),
            "Country": Column(str, nullable=False),
        },
        strict=False,
        coerce=True,
    )


def add_issue(issues: List[Issue], issue_type: str, severity: str, n: int, fix: str, owner: str = "Data Owner"):
    if n <= 0:
        return
    issues.append(
        Issue(
            issue_type=issue_type,
            severity=severity,
            row_count=int(n),
            owner=owner,
            recommended_fix=fix,
        )
    )


def compute_quality_score(issues: List[Issue], total_rows: int) -> Dict:
    # Simple scoring: start at 100; subtract weighted penalties.
    weights = {"HIGH": 8, "MEDIUM": 4, "LOW": 2}
    penalty = 0
    for it in issues:
        w = weights.get(it.severity.upper(), 2)
        penalty += w * (it.row_count / max(total_rows, 1)) * 100

    score = max(0, round(100 - penalty, 1))
    grade = "A" if score >= 95 else "B" if score >= 90 else "C" if score >= 80 else "D" if score >= 70 else "E"
    return {"score": score, "grade": grade, "total_rows": int(total_rows), "issue_count": len(issues)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to transactions CSV")
    ap.add_argument("--product-master", required=True, help="Path to product master CSV")
    ap.add_argument("--outdir", default="outputs", help="Output directory")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.input)
    pm = pd.read_csv(args.product_master)

    issues: List[Issue] = []

    # 1) Schema/type validation (coerce types)
    schema = build_schema()
    try:
        df = schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        # record schema errors but continue with coerced df where possible
        failure_cases = e.failure_cases
        add_issue(
            issues,
            "SCHEMA_VALIDATION_FAILED",
            "HIGH",
            len(failure_cases),
            "Align column names/types; enforce consistent export format (e.g., SAP -> CSV template).",
            owner="Reporting Owner",
        )

    # 2) Parse dates
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    bad_dates = df["InvoiceDate"].isna().sum()
    add_issue(
        issues,
        "INVALID_INVOICE_DATE",
        "MEDIUM",
        bad_dates,
        "Ensure InvoiceDate exports are consistent; fix locale/time format; re-export if needed.",
    )

    # 3) Completeness
    missing_cust = df["CustomerID"].isna().sum()
    add_issue(
        issues,
        "MISSING_CUSTOMER_ID",
        "LOW",
        missing_cust,
        "If CustomerID is required for the report, make it mandatory upstream; otherwise exclude from customer-level KPIs.",
    )

    empty_desc = (df["Description"].fillna("").str.strip() == "").sum()
    add_issue(
        issues,
        "EMPTY_DESCRIPTION",
        "LOW",
        empty_desc,
        "Fill from product master or enforce description capture upstream.",
    )

    # 4) Validity checks
    neg_or_zero_qty = (df["Quantity"] <= 0).sum()
    add_issue(
        issues,
        "NON_POSITIVE_QUANTITY",
        "MEDIUM",
        neg_or_zero_qty,
        "Separate returns vs sales; enforce Quantity>0 for sales extracts; tag returns with a flag.",
        owner="Process Owner",
    )

    neg_price = (df["UnitPrice"] <= 0).sum()
    add_issue(
        issues,
        "NON_POSITIVE_UNIT_PRICE",
        "HIGH",
        neg_price,
        "Fix price master / ensure UnitPrice is extracted correctly; block reporting until corrected.",
        owner="Master Data Owner",
    )

    bad_code = (~df["StockCode"].astype(str).str.match(r"^[A-Z0-9]+$")).sum()
    add_issue(
        issues,
        "INVALID_STOCKCODE_FORMAT",
        "MEDIUM",
        bad_code,
        "Standardize StockCode format; strip spaces; validate during data entry/export.",
        owner="Master Data Owner",
    )

    # 5) Duplicates (InvoiceNo + StockCode + InvoiceDate)
    dup = df.duplicated(subset=["InvoiceNo", "StockCode", "InvoiceDate"], keep=False).sum()
    add_issue(
        issues,
        "DUPLICATE_LINES",
        "MEDIUM",
        dup,
        "Define a unique key; deduplicate by latest timestamp; investigate double-exports.",
        owner="Reporting Owner",
    )

    # 6) Mapping integrity vs product master
    pm_codes = set(pm["StockCode"].astype(str))
    missing_map = (~df["StockCode"].astype(str).isin(pm_codes)).sum()
    add_issue(
        issues,
        "STOCKCODE_NOT_IN_PRODUCT_MASTER",
        "HIGH",
        missing_map,
        "Update product master mapping table or correct StockCodes in the source export.",
        owner="Master Data Owner",
    )

    # 7) Outlier price vs reference (simple rule)
    pm_ref = pm.set_index("StockCode")["UnitPrice_Ref"].to_dict()
    ref_price = df["StockCode"].map(pm_ref)
    # if missing ref, we already counted mapping issue; ignore NaN here
    price_ratio = df["UnitPrice"] / ref_price
    outlier = ((price_ratio < 0.3) | (price_ratio > 3.0)).fillna(False).sum()
    add_issue(
        issues,
        "UNITPRICE_OUTLIER_VS_REFERENCE",
        "LOW",
        outlier,
        "Review outliers; check currency/decimal issues; fix master price or export transformation.",
        owner="Finance/Reporting",
    )

    # Create exception log confirmation: row-level samples for each issue
    exception_rows = []

    def sample_rows(mask, issue_type, severity, max_n=50):
        subset = df.loc[mask].copy()
        if len(subset) == 0:
            return
        subset = subset.head(max_n)
        subset["IssueType"] = issue_type
        subset["Severity"] = severity
        exception_rows.append(subset)

    sample_rows(df["InvoiceDate"].isna(), "INVALID_INVOICE_DATE", "MEDIUM")
    sample_rows(df["CustomerID"].isna(), "MISSING_CUSTOMER_ID", "LOW")
    sample_rows(df["Description"].fillna("").str.strip() == "", "EMPTY_DESCRIPTION", "LOW")
    sample_rows(df["Quantity"] <= 0, "NON_POSITIVE_QUANTITY", "MEDIUM")
    sample_rows(df["UnitPrice"] <= 0, "NON_POSITIVE_UNIT_PRICE", "HIGH")
    sample_rows(~df["StockCode"].astype(str).str.match(r"^[A-Z0-9]+$"), "INVALID_STOCKCODE_FORMAT", "MEDIUM")
    sample_rows(df.duplicated(subset=["InvoiceNo", "StockCode", "InvoiceDate"], keep=False), "DUPLICATE_LINES", "MEDIUM")
    sample_rows(~df["StockCode"].astype(str).isin(pm_codes), "STOCKCODE_NOT_IN_PRODUCT_MASTER", "HIGH")
    sample_rows(((price_ratio < 0.3) | (price_ratio > 3.0)).fillna(False), "UNITPRICE_OUTLIER_VS_REFERENCE", "LOW")

    if exception_rows:
        ex = pd.concat(exception_rows, ignore_index=True)
    else:
        ex = pd.DataFrame()

    # Compact issue summary
    issue_df = pd.DataFrame([i.__dict__ for i in issues]).sort_values(["severity", "row_count"], ascending=[True, False])

    # Quality score
    score = compute_quality_score(issues, len(df))

    # Summary KPIs (value report building blocks)
    df["LineRevenue"] = df["Quantity"] * df["UnitPrice"]
    kpis = {
        "rows": len(df),
        "unique_invoices": df["InvoiceNo"].nunique(),
        "unique_customers": int(df["CustomerID"].nunique(dropna=True)),
        "countries": df["Country"].nunique(),
        "gross_revenue": float(df["LineRevenue"].sum(skipna=True)),
        "avg_order_value": float(df.groupby("InvoiceNo")["LineRevenue"].sum().mean()),
    }
    kpis_df = pd.DataFrame([kpis])

    # Write outputs
    issue_df.to_csv(os.path.join(args.outdir, "exception_log.csv"), index=False)
    ex.to_csv(os.path.join(args.outdir, "exception_samples.csv"), index=False)
    kpis_df.to_csv(os.path.join(args.outdir, "summary_kpis.csv"), index=False)
    with open(os.path.join(args.outdir, "data_quality_score.json"), "w", encoding="utf-8") as f:
        json.dump(score, f, indent=2)

    print("✅ Done. Outputs written to:", args.outdir)
    print("Data quality score:", score)


if __name__ == "__main__":
    main()

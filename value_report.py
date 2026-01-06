import argparse
import os
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default="outputs")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.input, parse_dates=["InvoiceDate"], infer_datetime_format=True)
    df["LineRevenue"] = df["Quantity"] * df["UnitPrice"]

    # Weekly trend (simple value report)
    df["Week"] = df["InvoiceDate"].dt.to_period("W").astype(str)
    weekly = df.groupby("Week").agg(
        invoices=("InvoiceNo","nunique"),
        customers=("CustomerID","nunique"),
        revenue=("LineRevenue","sum"),
        lines=("InvoiceNo","count")
    ).reset_index()

    # Top products by revenue
    top_products = df.groupby(["StockCode","Description"]).agg(
        revenue=("LineRevenue","sum"),
        qty=("Quantity","sum"),
        invoices=("InvoiceNo","nunique")
    ).reset_index().sort_values("revenue", ascending=False).head(25)

    weekly.to_csv(os.path.join(args.outdir, "value_report_weekly.csv"), index=False)
    top_products.to_csv(os.path.join(args.outdir, "value_report_top_products.csv"), index=False)

    print("✅ Value report files written to", args.outdir)

if __name__ == "__main__":
    main()

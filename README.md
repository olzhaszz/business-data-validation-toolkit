# Business Data Validation & Integrity Toolkit (Python + Excel-friendly outputs)

A reusable workflow to validate business datasets **before** reporting:
- Missing fields / duplicates / invalid formats
- Mapping issues vs reference tables (product master)
- Control totals and outlier flags
- Produces an **exception log** + a simple **data quality score** for weekly project updates

This project is designed to match an internship focused on **data analysis & validation** (Excel / SAP exports / Power BI / process data).

## Dataset
This repo includes a **synthetic large retail transactions dataset** (200k rows) in:
- `data/raw/transactions_synthetic_large.csv`

Column structure matches popular transaction datasets (InvoiceNo, StockCode, Quantity, UnitPrice, CustomerID, Country).

> If you want a real dataset instead, you can also use Kaggle’s “Online Retail” dataset (same columns).  
> Example pages:  
> - https://www.kaggle.com/datasets/rupakroy/online-retail  
> - https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci

## Quickstart
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python src/validate_transactions.py --input data/raw/transactions_synthetic_large.csv --product-master data/reference/product_master.csv
```

Outputs:
- `outputs/exception_log.csv`
- `outputs/data_quality_score.json`
- `outputs/summary_kpis.csv`

## What the toolkit checks
1. **Schema & types** (basic rules)
2. **Completeness** (null reminders)
3. **Uniqueness** (duplicate rows / keys)
4. **Validity** (negative quantities, empty descriptions, bad codes)
5. **Mapping integrity** (StockCode exists in product master)
6. **Outliers** (UnitPrice far from reference)

## “How to talk about this in an interview”
**Problem:** reporting was inconsistent because source data had duplicates/missing fields/mismatches.  
**Approach:** defined validation rules + exception log + weekly quality score.  
**Impact:** faster reporting, fewer errors, clearer ownership (who fixes what).

## Folder structure
- `src/` scripts
- `data/` raw + reference data
- `outputs/` generated results (ignored by git)

## License
MIT (use freely).

# Quick Walkthrough

1. Install deps: `pip install -r requirements.txt`
2. Run validation:
   ```bash
   python src/validate_transactions.py --input data/raw/transactions_synthetic_large.csv --product-master data/reference/product_master.csv
   ```
3. Open outputs:
   - `outputs/exception_log.csv` (issue summary)
   - `outputs/exception_samples.csv` (row samples)
   - `outputs/data_quality_score.json` (score + grade)
   - `outputs/summary_kpis.csv` (KPIs)

Suggested interview line:
- “I set up validation gates and an exception log so reports are consistent, and ownership is clear.”

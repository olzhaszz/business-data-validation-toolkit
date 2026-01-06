"""Optional: Download a real dataset from Kaggle (requires Kaggle API token).

1) Create a Kaggle account -> Account settings -> Create New API Token
2) Put kaggle.json in:
   - Windows: C:\Users\<you>\.kaggle\kaggle.json
   - macOS/Linux: ~/.kaggle/kaggle.json
3) Install kaggle:
   pip install kaggle
4) Run:
   python src/kaggle_download.py --dataset rupakroy/online-retail --out data/raw

This will download and unzip the dataset into data/raw.
"""

import argparse
import os
import subprocess

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="rupakroy/online-retail")
    ap.add_argument("--out", default="data/raw")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    cmd = ["kaggle", "datasets", "download", "-d", args.dataset, "-p", args.out, "--unzip"]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)
    print("✅ Downloaded into", args.out)

if __name__ == "__main__":
    main()

"""
UC-0C: Number That Looks Right
Budget Growth Analyser — Civic Tech Edition

Computes year-on-year budget growth per ward per category.
Never aggregates across wards or categories before computing growth.

Usage:
    python uc-0c/app.py
    python uc-0c/app.py --input data/budget/ward_budget.csv --output uc-0c/growth_output.csv

Output: growth_output.csv
"""

import csv
import sys
import os
import argparse
from collections import defaultdict


# ---------------------------------------------------------------------------
# Skill: Load and Validate Budget CSV
# ---------------------------------------------------------------------------

def load_budget(filepath: str) -> list[dict]:
    """
    Load and validate the ward budget CSV.
    Required columns: ward, category, year, amount
    Returns a list of validated row dicts.
    """
    required_columns = {"ward", "category", "year", "amount"}
    rows = []

    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Check columns
        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            print(f"[ERROR] Missing columns in CSV: {missing}", file=sys.stderr)
            sys.exit(1)

        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            # Coerce year
            try:
                year = int(row["year"].strip())
            except (ValueError, AttributeError):
                print(f"[ERROR] Row {i}: invalid year value '{row['year']}' — skipping row.", file=sys.stderr)
                continue

            # Coerce amount
            try:
                amount = float(row["amount"].strip())
            except (ValueError, AttributeError):
                print(f"[ERROR] Row {i}: invalid amount value '{row['amount']}' — skipping row.", file=sys.stderr)
                continue

            # Reject negative amounts
            if amount < 0:
                print(f"[WARNING] Row {i}: negative amount {amount} for ward='{row['ward']}' "
                      f"category='{row['category']}' year={year} — skipping row.", file=sys.stderr)
                continue

            rows.append({
                "ward": row["ward"].strip(),
                "category": row["category"].strip(),
                "year": year,
                "amount": amount,
            })

    print(f"[INFO] Loaded {len(rows)} valid rows from '{filepath}'.")
    return rows


# ---------------------------------------------------------------------------
# Skill: Build Per-Ward Per-Category Pivot
# ---------------------------------------------------------------------------

def build_pivot(rows: list[dict]) -> dict:
    """
    Build a pivot dict: { (ward, category): { year: amount } }

    ENFORCEMENT: Each (ward, category, year) triple must be unique.
    Raises ValueError if a duplicate is detected — never silently overwrites.
    """
    pivot = defaultdict(dict)

    for row in rows:
        key = (row["ward"], row["category"])
        year = row["year"]

        if year in pivot[key]:
            raise ValueError(
                f"[ERROR] Duplicate entry detected: ward='{row['ward']}' "
                f"category='{row['category']}' year={year}. "
                f"Input data must have at most one amount per ward+category+year."
            )

        pivot[key][year] = row["amount"]

    print(f"[INFO] Pivot built: {len(pivot)} unique ward+category combinations.")
    return dict(pivot)


# ---------------------------------------------------------------------------
# Skill: Compute Growth with Guard Rails
# ---------------------------------------------------------------------------

def compute_growth(pivot: dict) -> list[dict]:
    """
    For each (ward, category) pair, compute year-on-year growth percentage.

    Guard rails:
    - MISSING_YEAR: fewer than 2 years of data → growth_pct = None
    - BASE_ZERO: base year amount is 0 → growth_pct = None
    - OK: valid computation

    Every (ward, category) pair emits exactly one row. Nothing is dropped.
    """
    results = []

    for (ward, category), year_map in pivot.items():
        years = sorted(year_map.keys())

        # Guard: MISSING_YEAR
        if len(years) < 2:
            results.append({
                "ward": ward,
                "category": category,
                "base_year": years[0] if years else None,
                "target_year": None,
                "base_amount": year_map.get(years[0]) if years else None,
                "target_amount": None,
                "growth_pct": None,
                "flag": "MISSING_YEAR",
            })
            continue

        base_year = years[0]
        target_year = years[-1]
        base_amount = year_map[base_year]
        target_amount = year_map[target_year]

        # Guard: BASE_ZERO
        if base_amount == 0:
            results.append({
                "ward": ward,
                "category": category,
                "base_year": base_year,
                "target_year": target_year,
                "base_amount": base_amount,
                "target_amount": target_amount,
                "growth_pct": None,
                "flag": "BASE_ZERO",
            })
            continue

        # Normal computation — per-ward, per-category only
        growth_pct = round((target_amount - base_amount) / base_amount * 100, 2)

        results.append({
            "ward": ward,
            "category": category,
            "base_year": base_year,
            "target_year": target_year,
            "base_amount": base_amount,
            "target_amount": target_amount,
            "growth_pct": growth_pct,
            "flag": "OK",
        })

    return results


# ---------------------------------------------------------------------------
# Skill: Write growth_output.csv
# ---------------------------------------------------------------------------

def write_output(results: list[dict], output_path: str) -> None:
    """
    Write results to growth_output.csv with deterministic ordering.
    Uses empty string (not 'None') for null fields.
    """
    # Deterministic sort: ward → category
    results_sorted = sorted(results, key=lambda r: (r["ward"], r["category"]))

    fieldnames = [
        "ward", "category",
        "base_year", "target_year",
        "base_amount", "target_amount",
        "growth_pct", "flag",
    ]

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results_sorted:
            # Convert None → empty string for clean CSV output
            writer.writerow({k: ("" if v is None else v) for k, v in row.items()})

    # Summary
    total = len(results_sorted)
    ok_count = sum(1 for r in results_sorted if r["flag"] == "OK")
    missing = sum(1 for r in results_sorted if r["flag"] == "MISSING_YEAR")
    base_zero = sum(1 for r in results_sorted if r["flag"] == "BASE_ZERO")

    print(f"\n[DONE] growth_output.csv written to '{output_path}'")
    print(f"       Total rows   : {total}")
    print(f"       OK           : {ok_count}")
    print(f"       MISSING_YEAR : {missing}")
    print(f"       BASE_ZERO    : {base_zero}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="UC-0C: Compute per-ward per-category budget growth."
    )
    parser.add_argument(
        "--input",
        default="data/budget/ward_budget.csv",
        help="Path to ward_budget.csv (default: data/budget/ward_budget.csv)",
    )
    parser.add_argument(
        "--output",
        default="uc-0c/growth_output.csv",
        help="Path to write growth_output.csv (default: uc-0c/growth_output.csv)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("UC-0C: Number That Looks Right — Budget Growth Analyser")
    print("=" * 60)

    # Step 1: Load and validate
    rows = load_budget(args.input)

    # Step 2: Build per-ward per-category pivot (no cross-aggregation)
    pivot = build_pivot(rows)

    # Step 3: Compute growth with guard rails
    results = compute_growth(pivot)

    # Step 4: Write output
    write_output(results, args.output)


if __name__ == "__main__":
    main()

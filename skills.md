# skills.md — UC-0C: Number That Looks Right

## Skill: Load and Validate Budget CSV

### What it does
Reads `ward_budget.csv` and enforces schema before any computation begins.

### Steps
1. Load CSV with `csv.DictReader` — no pandas required, keeps it dependency-free.
2. Assert required columns are present: `ward`, `category`, `year`, `amount`.
3. Coerce `year` to `int` and `amount` to `float`. On failure, raise a descriptive error naming the row and column.
4. Reject any row where `amount` is negative — log a warning and skip.
5. Return a list of dicts, one per validated row.

### Failure this skill prevents
Silently processing malformed data that produces numerically plausible but incorrect outputs.

---

## Skill: Build Per-Ward Per-Category Pivot

### What it does
Groups the validated rows into a dict keyed by `(ward, category)`, mapping each key to a `{year: amount}` sub-dict.

### Steps
1. Iterate over all validated rows.
2. For each row, insert `pivot[(ward, category)][year] = amount`.
3. After building, verify: no (ward, category) pair has duplicate year entries. If a duplicate is found, raise an error — do not silently overwrite.

### Failure this skill prevents
Cross-ward and cross-category aggregation. The pivot enforces that each combination is independent before any arithmetic occurs.

---

## Skill: Compute Growth with Guard Rails

### What it does
For each `(ward, category)` pair, finds the base year and target year and computes growth percentage — safely.

### Steps
1. Identify the two years available. If fewer than 2 years present → `growth_pct = None`, `flag = MISSING_YEAR`.
2. Sort years ascending. Base year = min, target year = max.
3. If `base_amount == 0` → `growth_pct = None`, `flag = BASE_ZERO`.
4. Otherwise: `growth_pct = round((target - base) / base * 100, 2)`, `flag = OK`.
5. Always emit a row — never skip.

### Failure this skill prevents
Division-by-zero suppression and silent row drops. Every ward+category pair must appear in output.

---

## Skill: Write growth_output.csv

### What it does
Writes the results list to `growth_output.csv` with a fixed column order.

### Steps
1. Sort results by `ward` then `category` (alphabetical) for deterministic output.
2. Write header: `ward,category,base_year,target_year,base_amount,target_amount,growth_pct,flag`
3. Write each row — use empty string for `None` fields (not "None", not "null").
4. Print a summary: total rows written, count of OK / MISSING_YEAR / BASE_ZERO flags.

### Failure this skill prevents
Non-deterministic row ordering that makes diff-based review hard during CRAFT testing.

---

## CRAFT Loop Reference

| Step | What to do |
|------|-----------|
| **C**reate | Prompt → generate `app.py` using the skills above |
| **R**un | `python uc-0c/app.py` — confirm it exits without error and produces `growth_output.csv` |
| **A**ssert | Check row count = number of unique ward+category pairs in input |
| **F**ix | If aggregation bug found, add enforcement to the pivot skill and re-run |
| **T**est | Manually verify 2–3 rows by hand calculation — base_amount, target_amount, growth_pct |

---

## Commit Message Template

```
UC-0C Fix [what]: [why it failed] → [what you changed]
```

Examples:
```
UC-0C Fix silent aggregation: no scope in enforcement → restricted growth to per-ward per-category only
UC-0C Fix base-zero drop: division by zero silently skipped rows → added BASE_ZERO flag and null output
UC-0C Fix missing-year drop: single-year pairs disappeared → added MISSING_YEAR flag and null output
```

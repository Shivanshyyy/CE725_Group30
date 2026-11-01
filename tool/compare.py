"""Compare the tool with the team's independent Excel benchmark.

The team types its benchmark results into ../benchmark/benchmark_results.csv (column benchmark_value).
Run:  python3 compare.py
Writes ../benchmark/discrepancy_table.csv and prints the table. Tolerance: ±0.1% (USER_CONTEXT.md, section 6).
"""
import csv
from pathlib import Path

import model as M

HERE = Path(__file__).parent
BENCH = HERE.parent / "benchmark" / "benchmark_results.csv"
OUT = HERE.parent / "benchmark" / "discrepancy_table.csv"
TOLERANCE = 0.001

SPOT_QUARTERS = (6, 10)


def tool_outputs(ev):
    """The outputs the benchmark recomputes, keyed as in benchmark_results.csv."""
    r, m = ev["result"], ev["result"]["metrics"]
    out = {
        "built_up_area_sqft": r["bua_sqft"],
        "saleable_area_sqft": r["saleable_sqft"],
        "total_construction_cost_cr": sum(r["costs"]["construction"]),
        "total_bookings_cr": m["total_bookings"],
        "total_collections_cr": m["total_collections"],
        "total_cost_cr": m["total_cost"],
        "project_npv_cr": m["project_npv"],
        "project_irr_pct": None if m["project_irr"] is None else 100 * m["project_irr"],
        "payback_years": m["payback_years"],
        "profit_on_cost_pct": None if m["profit_on_cost"] is None else 100 * m["profit_on_cost"],
        "peak_funding_cr": m["peak_funding"],
        "peak_quarter": m["peak_quarter"],
        "equity_irr_pct": None if m["equity_irr"] is None else 100 * m["equity_irr"],
        "total_loan_interest_cr": m["finance_cost"],
        "breakeven_price_psf": ev["breakeven_price"],
        "max_land_price_cr": ev["breakeven_land"],
    }
    for q in SPOT_QUARTERS:
        out[f"collections_q{q}_cr"] = r["collections"][q] if q <= r["T"] else None
        out[f"construction_q{q}_cr"] = r["costs"]["construction"][q] if q <= r["T"] else None
        out[f"rera_balance_q{q}_cr"] = r["escrow_balance"][q] if q <= r["T"] else None
    return out


def compare(ev, path=BENCH):
    """Rows: output, unit, tool, benchmark, difference, % difference, status."""
    tool = tool_outputs(ev)
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key, raw = row["output"], (row.get("benchmark_value") or "").strip()
            t = tool.get(key)
            if not raw:
                rows.append([key, row["unit"], t, None, None, None, "benchmark not entered yet"])
                continue
            b = float(raw.replace(",", ""))
            diff = None if t is None else t - b
            rel = None if diff is None else (abs(diff) / abs(b) if b else abs(diff))
            ok = rel is not None and rel <= TOLERANCE
            rows.append([key, row["unit"], t, b, diff, rel, "match" if ok else "DIFFERENT: find the cause"])
    return rows


def write(rows, path=OUT):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["output", "unit", "tool", "benchmark", "difference", "relative difference", "status", "cause", "how resolved"])
        for r in rows:
            w.writerow(r + ["", ""])


if __name__ == "__main__":
    inp, _ = M.load_case()
    rows = compare(M.evaluate(inp))
    write(rows)
    fmt = lambda x: "" if x is None else f"{x:,.4f}"
    for key, unit, t, b, d, rel, status in rows:
        print(f"{key:30s} {unit:14s} tool {fmt(t):>16s}  bench {fmt(b):>16s}  {status}")
    entered = [r for r in rows if r[3] is not None]
    print(f"\n{sum(r[6] == 'match' for r in entered)}/{len(entered)} entered outputs match within ±{TOLERANCE:.1%}. "
          f"Table written to {OUT}")

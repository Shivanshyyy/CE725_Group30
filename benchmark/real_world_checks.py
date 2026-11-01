"""Real-world checks: run published Indian projects through tool/model.py and compare with what was published.
Run from this folder:  python3 real_world_checks.py
Writes real_cases/*.json, which the website's 'Load inputs from a file' button can open.
AI-prepared (Claude, 1 Nov 2026); sources in REAL_WORLD_CHECKS.md. Not a substitute for the team's hand-built benchmark.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "tool"))
import model as M  # noqa: E402

BASE, _ = M.load_case()
ACRE = 43560


def case(**over):
    inp = dict(BASE)
    inp.update(over)
    return inp


# 1. Silver Gracia, Ravet, Pune (IRJET 2021 feasibility study): costs ₹102.73 cr, developer's revenue share ₹146.54 cr
#    (60% of ₹244.24 cr at ₹5,900/sq ft), 36 months, 10% discount rate, all units sold. Land owner takes 40% (JV),
#    so land = 0 and the price is the developer's 60% share. Costs and price held flat, as in the paper.
SALEABLE_SG = 2_442_350_531 / 5900            # sq ft implied by the paper's revenue
SG = case(plot_area_sqft=5 * ACRE, saleable_ratio=0.6, fsi=SALEABLE_SG / 0.6 / (5 * ACRE),
          construction_rate_psf=1_027_255_067 / (SALEABLE_SG / 0.6),
          land_price_cr=0, ready_reckoner_cr=0, stamp_duty_pct=0, approvals_cr=0, premiums_cr=0,
          cost_escalation_pct=0, soft_cost_pct=0, contingency_pct=0, marketing_pct=0,
          construction_start_q=0, construction_quarters=12, launch_q=0, price_psf=5900 * 0.6, price_growth_pct=0,
          sales_pace_pct=100 / 12, tax_rate_pct=0, hurdle_rate_pct=10, equity_hurdle_pct=10,
          equity_limit_cr=200, loan_limit_cr=0, min_profit_on_cost_pct=10)

# 2. Godrej Properties, Kharadi-Wagholi, Pune (exchange filing, 2 Jun 2025): 14 acres, 3.7 mn sq ft, revenue ₹4,200 cr;
#    land ~₹800 cr (market sources). Developable area treated as saleable. Market inputs as in the base case.
GK = case(plot_area_sqft=14 * ACRE, saleable_ratio=0.8, fsi=3.7e6 / 0.8 / (14 * ACRE),
          land_price_cr=800, ready_reckoner_cr=800, approvals_cr=0, premiums_cr=0,
          price_psf=4200e7 / 3.7e6, construction_start_q=3, construction_quarters=16, launch_q=3,
          sales_pace_pct=8, equity_limit_cr=1500, loan_limit_cr=1000, loan_rate_pct=10)


def show(name, inp):
    ev = M.evaluate(inp)
    m = ev["result"]["metrics"]
    rev, cost = m["total_bookings"], m["total_cost"] + m["finance_cost"]
    print(f"\n{name}")
    print(f"  revenue (bookings) ₹{rev:,.2f} cr | total cost ₹{cost:,.2f} cr | profit on cost {m['profit_on_cost']:.1%} "
          f"| margin on revenue {(rev - cost) / rev:.1%}")
    print(f"  NPV ₹{m['project_npv']:,.2f} cr | IRR {M.pct(m['project_irr'])} | peak funding ₹{m['peak_funding']:,.2f} cr "
          f"in Q{m['peak_quarter']} | max land price {M.cr(ev['breakeven_land']) if ev['breakeven_land'] is not None else 'n/a'} "
          f"| verdict {ev['verdict']}")
    return ev


if __name__ == "__main__":
    # check 0: the engine's NPV/IRR on the paper's own simplified cash flow (all cost now, all revenue in one year)
    cf = [-102.7255067, 146.5410319]
    print(f"Check 0: paper's one-period cash flow -> NPV at 10% ₹{M.npv(0.10, cf):.2f} cr (paper ₹30.49 cr), "
          f"IRR {100 * M.irr(cf):.1f}% (paper 42.7%)")
    show("Check 1: Silver Gracia, Ravet (IRJET 2021), quarter by quarter", SG)
    show("Check 2: Godrej Kharadi-Wagholi (Jun 2025)", GK)
    show("Check 2b: same, sold at today's price (no price growth), to match the filing's ₹4,200 cr",
         {**GK, "price_growth_pct": 0})
    (HERE / "real_cases").mkdir(exist_ok=True)
    for fname, title, inp in (("silver_gracia_ravet.json", "Silver Gracia, Ravet (IRJET 2021 case study)", SG),
                              ("godrej_kharadi_wagholi.json", "Godrej Kharadi-Wagholi, Pune (Jun 2025 filing)", GK)):
        (HERE / "real_cases" / fname).write_text(json.dumps({"project_name": title, "inputs": inp}, indent=2))

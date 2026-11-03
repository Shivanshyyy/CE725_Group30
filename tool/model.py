"""Real estate feasibility model for one residential project (CE725 Topic 2).

Conventions (keep these identical in the Excel benchmark):
- Periods are quarters t = 0, 1, ..., T. Every cash flow happens at the END of its quarter.
- Land is paid at quarter 0. Money in is +, money out is -. Amounts are in Rs crore.
- Hurdle (discount) rates are effective annual rates -> quarterly (1 + r)^(1/4) - 1 (course notes, Ch 2).
- The loan rate is a nominal annual rate with interest charged monthly -> quarterly (1 + r/12)^3 - 1.
- Quarter inputs are whole numbers; fractions are rounded with a warning.

Each function is small and pure so it can be tested and explained on its own.
"""
import json
import math
from pathlib import Path

CRORE = 1e7
BASE_CASE = Path(__file__).with_name("base_case.json")


# ---------- inputs ----------

def load_case(path=BASE_CASE):
    """Return (values, meta). values: {key: number}; meta: the full input records with source/date/flag."""
    data = json.loads(Path(path).read_text())
    meta = data["inputs"]
    return {k: v["value"] for k, v in meta.items()}, data


def q_rate(annual_pct):
    """Effective quarterly rate from an effective annual % (Ch 2: i_q = (1 + i)^(1/4) - 1). Used for hurdle rates."""
    return (1 + annual_pct / 100) ** 0.25 - 1


def q_rate_loan(annual_pct):
    """Quarterly rate for a bank loan quoted as a nominal annual rate with interest charged monthly
    (Ch 2: nominal r compounded m times a year). 12% a year -> (1 + 0.01)^3 - 1 = 3.03% a quarter."""
    return (1 + annual_pct / 1200) ** 3 - 1


QUARTER_INPUTS = {"construction_start_q": "Construction start quarter", "construction_quarters": "Construction duration",
                  "launch_q": "Sales launch quarter", "delay_q": "Construction delay"}


def whole(x):
    """Quarter inputs are whole numbers: round half up (run() warns when rounding changed the value)."""
    return int(math.floor(x + 0.5))


# ---------- 1. areas ----------

def areas(inp):
    """Built-up area = plot x FSI; saleable area = built-up x saleable ratio (sq ft)."""
    bua = inp["plot_area_sqft"] * inp["fsi"]
    return bua, bua * inp["saleable_ratio"]


# ---------- 2. costs ----------

def s_curve_shares(n):
    """Share of construction cost spent in each of n quarters, from S(x) = 3x^2 - 2x^3. Shares sum to 1."""
    s = lambda x: 3 * x * x - 2 * x ** 3
    return [s(k / n) - s((k - 1) / n) for k in range(1, n + 1)]


def timeline(inp):
    """Key quarters: construction start, actual duration (incl. delay), promised and actual possession."""
    start = max(0, whole(inp["construction_start_q"]))
    planned = max(1, whole(inp["construction_quarters"]))
    delay = max(0, whole(inp["delay_q"]))
    return {"start": start, "duration": planned + delay,
            "promised_possession": start + planned, "possession": start + planned + delay}


def construction_schedule(inp, bua, tl, T):
    """Construction spend per quarter (Rs cr), escalated at the cost escalation rate, and % complete (PC)."""
    shares = s_curve_shares(tl["duration"])
    spend, pc, done = [0.0] * (T + 1), [0.0] * (T + 1), 0.0
    for t in range(T + 1):
        k = t - tl["start"]
        if 0 <= k < len(shares):
            rate = inp["construction_rate_psf"] * (1 + inp["cost_escalation_pct"] / 100) ** (t / 4)
            spend[t] = bua * rate * shares[k] / CRORE
            done += shares[k]
        pc[t] = min(done, 1.0)
    return spend, pc


def spread(total, first, last, T):
    """Spread a total evenly over quarters first..last (inclusive); all at `first` if last < first."""
    out = [0.0] * (T + 1)
    last = max(first, last)
    n = last - first + 1
    for t in range(first, min(last, T) + 1):
        out[t] = total / n
    return out


# ---------- 3. sales and collections ----------

def sales_schedule(inp, saleable, max_q=200):
    """Area sold and booking value (Rs cr) per quarter, from launch until sold out."""
    pace = inp["sales_pace_pct"] / 100 * saleable
    launch = max(0, whole(inp["launch_q"]))
    area, price, left, t = [], [], saleable, 0
    while left > 1e-6 and t <= max_q:
        sold = min(pace, left) if t >= launch and pace > 0 else 0.0
        area.append(sold)
        price.append(inp["price_psf"] * (1 + inp["price_growth_pct"] / 100) ** ((t - launch) / 4) if t >= launch else 0.0)
        left -= sold
        t += 1
    return area, price


def collections(bookings, pc, possession, b, f):
    """Construction-linked plan. Every buyer has paid the same share CE_t of their price by quarter t:
    CE_t = b + (1 - b - f) x PC_t + f x [t >= possession]. Cumulative collections = cumulative bookings x CE_t."""
    out, cum_book, prev = [], 0.0, 0.0
    for t, bk in enumerate(bookings):
        cum_book += bk
        ce = b + (1 - b - f) * pc[t] + (f if t >= possession else 0.0)
        cum = cum_book * ce
        out.append(cum - prev)
        prev = cum
    return out


def buyer_delay_interest(coll, promised, actual, annual_pct):
    """RERA s.18: interest to buyers on what they have paid, for each quarter possession is late (simple rate / 4)."""
    out, paid = [0.0] * len(coll), 0.0
    for t in range(len(coll)):
        if promised < t <= actual:
            out[t] = paid * annual_pct / 100 / 4
        paid += coll[t]
    return out


# ---------- 4. tax ----------

def tax_on_cumulative_profit(taxable, rate_pct):
    """Tax on cumulative taxable profit; early losses carry forward; no refunds (stated simplification, Ch 11)."""
    out, cum, paid = [], 0.0, 0.0
    for x in taxable:
        cum += x
        due = max(0.0, rate_pct / 100 * cum - paid)
        out.append(due)
        paid += due
    return out


# ---------- 5. cash-flow maths (Ch 5, 7, 8) ----------

def npv(rate, cfs):
    return sum(c / (1 + rate) ** t for t, c in enumerate(cfs))


def irr(cfs):
    """Periodic IRR by bisection on the first sign change of NPV over a rate grid; None if NPV never crosses 0."""
    grid = [-0.9 + 0.01 * k for k in range(400)]
    vals = [npv(r, cfs) for r in grid]
    for i in range(len(grid) - 1):
        if vals[i] == 0:
            return grid[i]
        if vals[i] * vals[i + 1] < 0:
            lo, hi = grid[i], grid[i + 1]
            for _ in range(100):
                mid = (lo + hi) / 2
                if npv(lo, cfs) * npv(mid, cfs) <= 0:
                    hi = mid
                else:
                    lo = mid
            return (lo + hi) / 2
    return None


def annualise(rq):
    return None if rq is None else (1 + rq) ** 4 - 1


def sign_changes(cfs):
    signs = [c > 0 for c in cfs if abs(c) > 1e-9]
    return sum(a != b for a, b in zip(signs, signs[1:]))


def mirr(cfs, finance_q, reinvest_q):
    """MIRR (Ch 8): outflows discounted to t=0 at the finance rate, inflows compounded to T at the reinvestment rate."""
    n = len(cfs) - 1
    pv_out = -sum(c / (1 + finance_q) ** t for t, c in enumerate(cfs) if c < 0)
    fv_in = sum(c * (1 + reinvest_q) ** (n - t) for t, c in enumerate(cfs) if c > 0)
    if pv_out <= 0 or fv_in <= 0 or n == 0:
        return None
    return (fv_in / pv_out) ** (1 / n) - 1


def payback_years(cfs):
    """Simple payback (Ch 1): first time cumulative cash turns non-negative after being negative, interpolated."""
    cum, was_negative = 0.0, False
    for t, c in enumerate(cfs):
        prev = cum
        cum += c
        was_negative = was_negative or prev < 0
        if was_negative and cum >= 0 and c > 0:
            return ((t - 1) + (-prev / c)) / 4
    return None


# ---------- 6. the full run ----------

ESCROW_ELIGIBLE = ("land", "stamp_duty", "approvals", "premiums", "construction")
COST_LINES = ("land", "stamp_duty", "approvals", "premiums", "construction", "soft_costs",
              "contingency", "marketing", "buyer_delay_interest")


def run(inp):
    """Run one scenario. Returns a dict of quarterly series, headline metrics and plain-language warnings."""
    warnings = []
    bua, saleable = areas(inp)
    tl = timeline(inp)
    area, price = sales_schedule(inp, saleable)
    for key, label in QUARTER_INPUTS.items():
        if abs(inp[key] - whole(inp[key])) > 1e-9:
            warnings.append(f"{label} of {inp[key]:g} quarters was rounded to {whole(inp[key])}; the model works in whole quarters.")
    if inp["sales_pace_pct"] <= 0:
        warnings.append("Sales pace is zero, so no flats are sold and no money comes in.")
    elif saleable - sum(area) > 1e-6:
        warnings.append(f"At this sales pace {(saleable - sum(area)) / saleable:.0%} of the saleable area is still unsold "
                        f"after {len(area) - 1} quarters, where the model stops. Results leave that area unsold.")
    T = max(tl["possession"], len(area) - 1, tl["start"] + tl["duration"])
    area += [0.0] * (T + 1 - len(area))
    price += [0.0] * (T + 1 - len(price))
    bookings = [a * p / CRORE for a, p in zip(area, price)]
    sold_out = max((t for t, a in enumerate(area) if a > 0), default=None)
    gaps = [t for t in range(whole(inp["launch_q"]), (sold_out or 0) + 1) if area[t] <= 0]
    if gaps:
        warnings.append(f"No sales in quarter(s) {', '.join(f'Q{t}' for t in gaps)} while flats are still unsold.")

    constr, pc = construction_schedule(inp, bua, tl, T)
    pre_end = tl["start"] - 1
    L = {
        "land": [inp["land_price_cr"]] + [0.0] * T,
        "stamp_duty": [inp["stamp_duty_pct"] / 100 * max(inp["land_price_cr"], inp["ready_reckoner_cr"])] + [0.0] * T,
        "approvals": spread(inp["approvals_cr"], 0, pre_end, T),
        "premiums": spread(inp["premiums_cr"], 0, pre_end, T),
        "construction": constr,
    }
    L["soft_costs"] = [inp["soft_cost_pct"] / 100 * c for c in constr]
    L["contingency"] = [inp["contingency_pct"] / 100 * (c + s) for c, s in zip(constr, L["soft_costs"])]
    L["marketing"] = [inp["marketing_pct"] / 100 * b for b in bookings]

    b, f = inp["booking_pct"] / 100, inp["possession_pct"] / 100
    if b > 0.10 + 1e-9:
        warnings.append("Booking amount is above 10%. RERA Section 13 does not allow more than 10% before a registered sale agreement.")
    if b + f > 1:
        warnings.append("Booking % plus possession % is more than 100% of the price.")
    coll = collections(bookings, pc, tl["possession"], b, f)
    L["buyer_delay_interest"] = buyer_delay_interest(coll, tl["promised_possession"], tl["possession"], inp["buyer_interest_pct"])
    costs = [sum(L[k][t] for k in COST_LINES) for t in range(T + 1)]

    # project (unlevered) cash flow, after tax, ignoring escrow timing: the basis for project NPV/IRR
    tax_unlev = tax_on_cumulative_profit([c - k for c, k in zip(coll, costs)], inp["tax_rate_pct"])
    project_cf = [c - k - x for c, k, x in zip(coll, costs, tax_unlev)]

    # escrow + funding waterfall (developer's view, quarter by quarter)
    e = inp["escrow_pct"] / 100
    eligible = [sum(L[k][t] for k in ESCROW_ELIGIBLE) for t in range(T + 1)]
    eligible_total = sum(eligible)
    rq_loan = q_rate_loan(inp["loan_rate_pct"])
    rows = {k: [0.0] * (T + 1) for k in (
        "escrow_in", "escrow_out", "escrow_balance", "free_cash", "interest", "tax", "equity_in", "extra_equity",
        "loan_draw", "loan_repay", "loan_balance", "distribution", "cash_balance", "outstanding", "cfads")}
    esc = loan = cash = eq_in_cum = eq_back_cum = w_cum = elig_cum = 0.0
    cum_taxable = tax_paid = 0.0
    escrow_short = []
    loan_full_q = None
    for t in range(T + 1):
        dep = e * coll[t]
        elig_cum += eligible[t]
        allowed = max(0.0, min(pc[t] * eligible_total, elig_cum) - w_cum)
        avail = esc + dep
        w = min(avail, allowed)
        if allowed - w > 1e-6:
            escrow_short.append((t, allowed - w))
        if t >= tl["possession"]:
            w = avail  # project complete: remaining balance is released (simplification)
        esc = avail - w
        w_cum += w
        interest = rq_loan * loan
        cum_taxable += coll[t] - costs[t] - interest
        tax = max(0.0, inp["tax_rate_pct"] / 100 * cum_taxable - tax_paid)
        tax_paid += tax
        cash_in = (1 - e) * coll[t] + w
        cfads = cash_in - costs[t] - tax
        net = cfads - interest + cash
        cash = 0.0
        eq = extra = draw = repay = dist = 0.0
        if net < 0:
            need = -net
            eq = min(need, max(0.0, inp["equity_limit_cr"] - eq_in_cum))
            need -= eq
            draw = min(need, max(0.0, inp["loan_limit_cr"] - loan))
            need -= draw
            extra = need  # beyond both limits: shown as extra equity needed
            if draw > 0 and inp["loan_limit_cr"] - (loan + draw) < 1e-6 and loan_full_q is None:
                loan_full_q = t
        else:
            repay = min(net, loan)
            surplus = net - repay
            if t >= tl["possession"]:
                dist = surplus  # returned to equity once the project is complete
            else:
                cash = surplus  # held for later deficits
        loan += draw - repay
        eq_in_cum += eq + extra
        eq_back_cum += dist
        for k, v in (("escrow_in", dep), ("escrow_out", w), ("escrow_balance", esc), ("free_cash", (1 - e) * coll[t]),
                     ("interest", interest), ("tax", tax), ("equity_in", eq), ("extra_equity", extra),
                     ("loan_draw", draw), ("loan_repay", repay), ("loan_balance", loan), ("distribution", dist),
                     ("cash_balance", cash), ("outstanding", eq_in_cum - eq_back_cum + loan), ("cfads", cfads)):
            rows[k][t] = v
    # anything left at the end goes back to equity
    rows["distribution"][T] += rows["cash_balance"][T]
    rows["cash_balance"][T] = 0.0

    equity_cf = [rows["distribution"][t] - rows["equity_in"][t] - rows["extra_equity"][t] for t in range(T + 1)]

    # ---- metrics ----
    hq = q_rate(inp["hurdle_rate_pct"])
    total_cost = sum(costs)
    finance = sum(rows["interest"])
    peak = max(rows["outstanding"])
    peak_q = rows["outstanding"].index(peak)
    eq_at_peak = peak - rows["loan_balance"][peak_q]
    debt_quarters = [t for t in range(T + 1) if rows["loan_repay"][t] > 1e-9]
    dscr = None
    if debt_quarters:
        q0, q1 = debt_quarters[0], debt_quarters[-1]
        service = sum(rows["interest"][t] + rows["loan_repay"][t] for t in range(q0, q1 + 1))
        dscr = sum(rows["cfads"][t] for t in range(q0, q1 + 1)) / service if service > 0 else None
    cover = []
    cum_book = cum_coll = 0.0
    for t in range(T + 1):
        cum_book += bookings[t]
        cum_coll += coll[t]
        if rows["loan_balance"][t] > 1e-6:
            unsold_value = max(0.0, saleable - sum(area[:t + 1])) * (price[t] or inp["price_psf"]) / CRORE
            cover.append((cum_book - cum_coll + unsold_value) / rows["loan_balance"][t])
    p_irr_q = irr(project_cf)
    e_irr_q = irr(equity_cf)
    changes = sign_changes(project_cf)

    held = [(t, rows["escrow_balance"][t]) for t in range(tl["possession"])]
    t_held, max_held = max(held, key=lambda x: x[1]) if held else (0, 0.0)
    if max_held > 0.01:
        warnings.append(f"The RERA account holds up to ₹{max_held:.2f} cr of buyers' money (Q{t_held}) that cannot be used "
                        f"until construction catches up. Plan funding for that gap.")
    elif escrow_short:
        t, amt = max(escrow_short, key=lambda x: x[1])
        warnings.append(f"The RERA account never builds up: every rupee paid in can be withdrawn at once, because land and "
                        f"construction spending runs ahead of sales (up to ₹{amt:.2f} cr ahead, Q{t}). Slow sales, not the "
                        f"RERA rule, are what limit your cash here.")
    if sum(rows["extra_equity"]) > 1e-6:
        q = next(t for t in range(T + 1) if rows["extra_equity"][t] > 1e-6)
        warnings.append(f"Equity and loan limits are not enough: ₹{sum(rows['extra_equity']):.2f} cr more is needed, "
                        f"starting Q{q}. It is shown as extra equity.")
    if loan_full_q is not None:
        warnings.append(f"The loan limit (₹{inp['loan_limit_cr']:.1f} cr) is fully used by Q{loan_full_q}.")
    if rows["loan_balance"][T] > 1e-6:
        warnings.append(f"The loan is not fully repaid by the end of the project (₹{rows['loan_balance'][T]:.2f} cr left).")
    project_npv = npv(hq, project_cf)
    if project_npv < 0:
        warnings.append(f"Project NPV is negative at the {inp['hurdle_rate_pct']:.1f}% hurdle: it does not earn the target return.")
    if changes > 1:
        m = annualise(mirr(project_cf, rq_loan, hq))
        warnings.append(f"Project cash flow changes sign {changes} times, so IRR may not be unique. Rely on NPV"
                        + (f"; MIRR is {m:.1%}." if m is not None else "."))
    if tl["possession"] > tl["promised_possession"]:
        warnings.append(f"Possession is {tl['possession'] - tl['promised_possession']} quarter(s) late: "
                        f"₹{sum(L['buyer_delay_interest']):.2f} cr interest is owed to buyers under RERA Section 18.")

    return {
        "T": T, "timeline": tl, "bua_sqft": bua, "saleable_sqft": saleable,
        "area_sold": area, "price": price, "bookings": bookings, "collections": coll, "pc": pc,
        "costs": L, "total_costs": costs, "project_tax": tax_unlev, "project_cf": project_cf,
        "equity_cf": equity_cf, **rows, "warnings": warnings,
        "metrics": {
            "total_bookings": sum(bookings), "total_collections": sum(coll),
            "total_cost": total_cost, "finance_cost": finance, "total_tax": sum(rows["tax"]),
            "project_npv": project_npv, "project_irr": annualise(p_irr_q),
            "project_mirr": annualise(mirr(project_cf, rq_loan, hq)), "sign_changes": changes,
            "payback_years": payback_years(project_cf),
            "profit_on_cost": (sum(coll) - total_cost - finance) / (total_cost + finance) if total_cost + finance else None,
            "peak_funding": peak, "peak_quarter": peak_q, "peak_equity": eq_at_peak,
            "peak_loan": rows["loan_balance"][peak_q],
            "equity_npv": npv(q_rate(inp["equity_hurdle_pct"]), equity_cf), "equity_irr": annualise(e_irr_q),
            "peak_loan_balance": max(rows["loan_balance"]),
            "loan_to_cost": max(rows["loan_balance"]) / total_cost if total_cost else None,
            "dscr": dscr, "min_receivables_cover": min(cover) if cover else None,
            "extra_equity": sum(rows["extra_equity"]),
        },
    }


def cash_flow_rows(res):
    """Quarter-by-quarter table: (label, values, whether a total makes sense). Rs crore unless the label says otherwise."""
    c = res["costs"]
    rows = [
        ("Area sold (sq ft)", res["area_sold"], True), ("Sale price (₹/sq ft)", res["price"], False),
        ("Bookings", res["bookings"], True), ("Collections from buyers", res["collections"], True),
        ("Construction % complete", [100 * p for p in res["pc"]], False),
        ("Land", c["land"], True), ("Stamp duty + registration", c["stamp_duty"], True),
        ("Approval fees", c["approvals"], True), ("Premiums (FSI, fungible, TDR)", c["premiums"], True),
        ("Construction", c["construction"], True), ("Soft costs", c["soft_costs"], True),
        ("Contingency", c["contingency"], True), ("Marketing", c["marketing"], True),
        ("Interest owed to buyers (delay)", c["buyer_delay_interest"], True), ("Total costs", res["total_costs"], True),
        ("Tax (project basis)", res["project_tax"], True),
        ("Project cash flow (after tax, before loan)", res["project_cf"], True),
        ("Into RERA account", res["escrow_in"], True), ("Out of RERA account", res["escrow_out"], True),
        ("RERA account balance", res["escrow_balance"], False), ("Free cash (not in RERA account)", res["free_cash"], True),
        ("Loan interest", res["interest"], True), ("Tax (with loan interest)", res["tax"], True),
        ("Equity put in", res["equity_in"], True), ("Extra equity needed (beyond limits)", res["extra_equity"], True),
        ("Loan drawn", res["loan_draw"], True), ("Loan repaid", res["loan_repay"], True),
        ("Loan balance", res["loan_balance"], False), ("Cash held in project", res["cash_balance"], False),
        ("Returned to equity", res["distribution"], True),
        ("Equity + loan outstanding (negative = more returned than put in)", res["outstanding"], False),
        ("Equity cash flow", res["equity_cf"], True),
    ]
    return rows


# ---------- 7. scenarios, break-evens, sensitivity ----------

PRESETS = {
    "Base case": {"price": 0, "cost": 0, "pace": 0, "delay": 0},
    "Downside": {"price": -10, "cost": 10, "pace": -25, "delay": 2},
    "Upside": {"price": 5, "cost": -5, "pace": 15, "delay": 0},
}
PRESET_NOTE = "Preset shocks are team assumptions, not forecasts."


def scenario(inp, price=0, cost=0, pace=0, delay=0):
    """Copy of the inputs with % shocks to price, construction cost and sales pace, plus extra delay quarters."""
    s = dict(inp)
    s["price_psf"] = inp["price_psf"] * (1 + price / 100)
    s["construction_rate_psf"] = inp["construction_rate_psf"] * (1 + cost / 100)
    s["sales_pace_pct"] = inp["sales_pace_pct"] * (1 + pace / 100)
    s["delay_q"] = inp["delay_q"] + delay
    return s


def breakeven(inp, key, lo, hi, tol=1e-6):
    """Value of inp[key] at which project NPV = 0 (bisection, Ch 12). None if NPV does not cross 0 in [lo, hi]."""
    f = lambda x: run({**inp, key: x})["metrics"]["project_npv"]
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
        if hi - lo < tol * max(1.0, abs(mid)):
            break
    return (lo + hi) / 2


def breakeven_price(inp):
    return breakeven(inp, "price_psf", 0.1 * inp["price_psf"], 5 * inp["price_psf"])


def breakeven_land(inp):
    """Maximum land price (residual land value at the hurdle). None if even free land fails the hurdle."""
    return breakeven(inp, "land_price_cr", 0.0, max(10 * inp["land_price_cr"], 50.0))


SENSITIVITY_DRIVERS = [
    ("Sale price", "price"), ("Construction cost", "cost"), ("Sales pace", "pace"), ("Land price", "land"),
]


def sensitivity(inp, steps=(-20, -10, 10, 20)):
    """One-at-a-time changes. Returns rows: driver, change label, project NPV, project IRR, peak funding, equity IRR."""
    def metrics(s):
        m = run(s)["metrics"]
        return m["project_npv"], m["project_irr"], m["peak_funding"], m["equity_irr"]

    rows = []
    for name, key in SENSITIVITY_DRIVERS:
        for pct in steps:
            s = {**inp, "land_price_cr": inp["land_price_cr"] * (1 + pct / 100)} if key == "land" else scenario(inp, **{key: pct})
            rows.append((name, f"{pct:+d}%", *metrics(s)))
    for d in (2, 4):
        rows.append(("Delay", f"+{d} quarters", *metrics(scenario(inp, delay=d))))
    for pct in (-20, 20):
        rows.append(("Loan interest rate", f"{pct:+d}%", *metrics({**inp, "loan_rate_pct": inp["loan_rate_pct"] * (1 + pct / 100)})))
    return rows


def tornado(inp, pct=20):
    """NPV swing for each driver at -pct% / +pct% (delay: 0 vs +4 quarters), sorted by swing size."""
    base = run(inp)["metrics"]["project_npv"]
    out = []
    for name, key in SENSITIVITY_DRIVERS:
        lo_inp = {**inp, "land_price_cr": inp["land_price_cr"] * (1 - pct / 100)} if key == "land" else scenario(inp, **{key: -pct})
        hi_inp = {**inp, "land_price_cr": inp["land_price_cr"] * (1 + pct / 100)} if key == "land" else scenario(inp, **{key: pct})
        out.append((f"{name} ±{pct}%", run(lo_inp)["metrics"]["project_npv"], run(hi_inp)["metrics"]["project_npv"]))
    out.append(("Delay 0 → +4 quarters", base, run(scenario(inp, delay=4))["metrics"]["project_npv"]))
    return base, sorted(out, key=lambda r: abs(r[2] - r[1]), reverse=True)


# ---------- 8. decision, plain-language outputs ----------

def verdict(inp, res, downside):
    """Go / Marginal / No-go with the checks that produced it. Thresholds are team assumptions [VALIDATE]."""
    m = res["metrics"]
    checks = [
        ("Project NPV ≥ 0 at the hurdle rate", m["project_npv"] >= 0),
        (f"Profit on cost ≥ {inp['min_profit_on_cost_pct']:.0f}%", (m["profit_on_cost"] or -1) >= inp["min_profit_on_cost_pct"] / 100),
        ("Equity + loan limits cover peak funding", m["extra_equity"] <= 1e-6),
        ("NPV stays ≥ 0 in the downside case", downside["metrics"]["project_npv"] >= 0),
    ]
    if not checks[0][1] or not checks[2][1]:
        label = "No-go"
    elif all(ok for _, ok in checks):
        label = "Go"
    else:
        label = "Marginal"
    return label, checks


def evaluate(inp, base=None):
    """Everything the Decision page needs: run, downside run, verdict and both break-evens.
    `base` = the user's inputs before any what-if shocks; the downside case is always built from it, so choosing
    the Downside preset does not shock the deal twice."""
    res = run(inp)
    down = run(scenario(base if base is not None else inp, **PRESETS["Downside"]))
    label, checks = verdict(inp, res, down)
    return {"result": res, "downside": down, "verdict": label, "checks": checks,
            "breakeven_price": breakeven_price(inp), "breakeven_land": breakeven_land(inp)}


def cr(x):
    return f"{'−' if x < 0 else ''}₹{abs(x):,.2f} cr"


def pct(x):
    return "n/a" if x is None else f"{x:.1%}"


def so_what(inp, ev):
    """One plain sentence per headline number."""
    m = ev["result"]["metrics"]
    h = inp["hurdle_rate_pct"]
    s = {
        "peak_funding": f"You need up to {cr(m['peak_funding'])} of outside money, highest in Q{m['peak_quarter']} "
                        f"({cr(m['peak_equity'])} equity + {cr(m['peak_loan'])} loan). Have it lined up before then.",
        "project_npv": (f"At a {h:.0f}% hurdle the project creates {cr(m['project_npv'])} of value today, over and above that return."
                        if m["project_npv"] >= 0 else
                        f"At a {h:.0f}% hurdle the project falls {cr(-m['project_npv'])} short of your target return."),
        "project_irr": ("The cash flow has no single IRR; use NPV." if m["project_irr"] is None else
                        f"The project returns about {m['project_irr']:.1%} a year on all money put in, against your {h:.0f}% hurdle."),
        "profit_on_cost": ("n/a" if m["profit_on_cost"] is None else
                           f"Every ₹100 spent (including loan interest) comes back as about ₹{100 * (1 + m['profit_on_cost']):.0f} before tax."),
        "equity_irr": ("Your own money has no single IRR here." if m["equity_irr"] is None else
                       f"Your own money earns about {m['equity_irr']:.1%} a year, against your {inp['equity_hurdle_pct']:.0f}% target."),
    }
    bp = ev["breakeven_price"]
    if bp is None:
        s["breakeven_price"] = "No sale price in a sensible range makes NPV zero."
    elif bp <= inp["price_psf"]:
        s["breakeven_price"] = (f"Prices can fall to about ₹{bp:,.0f}/sq ft ({bp / inp['price_psf'] - 1:+.0%} vs your assumption) "
                                f"before the project stops meeting the hurdle.")
    else:
        s["breakeven_price"] = (f"Prices would have to be about ₹{bp:,.0f}/sq ft ({bp / inp['price_psf'] - 1:+.0%} above your "
                                f"assumption) for the project to meet the hurdle.")
    bl = ev["breakeven_land"]
    s["breakeven_land"] = ("Even free land would not meet the hurdle with these inputs." if bl is None else
                           f"At a {h:.0f}% hurdle you can pay up to {cr(bl)} for the land; you assumed {cr(inp['land_price_cr'])}.")
    return s


def flagged_inputs(meta, flags=("illustrative", "assumption")):
    return [(k, v) for k, v in meta["inputs"].items() if v["flag"] in flags]


def memo(inp, meta, ev):
    """Plain-language investment memo built from the results by template. No AI service is called."""
    m = ev["result"]["metrics"]
    d = ev["downside"]["metrics"]
    sw = so_what(inp, ev)
    illus = flagged_inputs(meta, ("illustrative",))
    assum = flagged_inputs(meta, ("assumption",))
    dscr = "n/a" if m["dscr"] is None else f"{m['dscr']:.2f}x"
    rcov = "n/a" if m["min_receivables_cover"] is None else f"{m['min_receivables_cover']:.2f}x"
    lines = [
        f"INVESTMENT MEMO: {meta['project_name']}",
        "",
        f"Recommendation: {ev['verdict'].upper()}",
        *[f"  [{'✓' if ok else '✗'}] {name}" for name, ok in ev["checks"]],
        "",
        "Key numbers (base case)",
        f"  Peak funding: {cr(m['peak_funding'])} in Q{m['peak_quarter']}. {sw['peak_funding']}",
        f"  Project NPV: {cr(m['project_npv'])}. {sw['project_npv']}",
        f"  Project IRR: {pct(m['project_irr'])}. {sw['project_irr']}",
        f"  Profit on cost: {pct(m['profit_on_cost'])}. {sw['profit_on_cost']}",
        f"  Break-even sale price: {sw['breakeven_price']}",
        f"  Maximum land price: {sw['breakeven_land']}",
        f"  Equity IRR: {pct(m['equity_irr'])}. {sw['equity_irr']}",
        "",
        "For the lender",
        f"  Peak loan {cr(m['peak_loan_balance'])}; loan-to-cost {pct(m['loan_to_cost'])}; "
        f"debt service cover {dscr}; minimum receivables cover {rcov}.",
        "",
        "Downside case (price −10%, construction cost +10%, sales 25% slower, 2 quarters late)",
        f"  NPV {cr(d['project_npv'])}; IRR {pct(d['project_irr'])}; peak funding {cr(d['peak_funding'])} in Q{d['peak_quarter']}.",
        "",
        "Warnings",
        *([f"  - {w}" for w in ev["result"]["warnings"]] or ["  - None."]),
        "",
        f"Inputs to verify before relying on this memo: {len(illus)} illustrative placeholder(s) and {len(assum)} assumption(s).",
        *[f"  - {v['label']} ({v['flag']}): {v['value']} {v['unit']}" for _, v in illus + assum],
        "",
        "Limits: one project, one phase; no joint-development or revenue-share deals; GST passed through; "
        "tax on cumulative profit; RERA account balance released at possession.",
    ]
    return "\n".join(lines)

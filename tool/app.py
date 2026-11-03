"""Streamlit front end for the feasibility model. Run: streamlit run app.py"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import model as M

st.set_page_config(page_title="Land Deal Feasibility", layout="wide")

BASE, META = M.load_case()
SHOCKS = ("price_chg", "cost_chg", "pace_chg", "delay_add")

# ---------- state ----------
if "values" not in st.session_state:
    st.session_state["values"] = dict(BASE)
for k in SHOCKS:
    st.session_state.setdefault(k, 0)


def apply_preset():
    p = M.PRESETS[st.session_state["preset"]]
    for key, src in zip(SHOCKS, ("price", "cost", "pace", "delay")):
        st.session_state[key] = p[src]


@st.cache_data(show_spinner=False)
def evaluate(items, base_items):
    return M.evaluate(dict(items), base=dict(base_items))


@st.cache_data(show_spinner=False)
def what_if(items):
    inp = dict(items)
    presets = {name: M.run(M.scenario(inp, **p))["metrics"] for name, p in M.PRESETS.items()}
    return presets, M.sensitivity(inp), M.tornado(inp)


def cr(x):
    return "n/a" if x is None else M.cr(x)


def pct(x):
    return "n/a" if x is None else f"{x:.1%}"


# ---------- sidebar: quick what-ifs ----------
with st.sidebar:
    st.header("What if?")
    st.selectbox("Start from a case", list(M.PRESETS), key="preset", on_change=apply_preset,
                 help=M.PRESET_NOTE)
    st.slider("Sale price change (%)", -30, 30, key="price_chg")
    st.slider("Construction cost change (%)", -30, 30, key="cost_chg")
    st.slider("Sales pace change (%)", -50, 50, key="pace_chg")
    st.slider("Extra delay (quarters)", 0, 8, key="delay_add")
    st.caption("These shocks apply on top of the inputs in the 'Inputs & sources' tab. " + M.PRESET_NOTE)

inp = M.scenario(st.session_state["values"], price=st.session_state["price_chg"], cost=st.session_state["cost_chg"],
                 pace=st.session_state["pace_chg"], delay=st.session_state["delay_add"])
key = tuple(sorted(inp.items()))
ev = evaluate(key, tuple(sorted(st.session_state["values"].items())))
res, m = ev["result"], ev["result"]["metrics"]
sw = M.so_what(inp, ev)

st.title("Should we buy this land?")
st.caption(f"{META['project_name']} · all money in ₹ crore unless shown · quarters counted from the land purchase (Q0)")
n_illus = len(M.flagged_inputs(META, ("illustrative",)))
if n_illus:
    st.info(f"{n_illus} inputs are illustrative placeholders, not real project data. Replace them in 'Inputs & sources' "
            "before using these results for a decision.")

tabs = st.tabs(["Decision", "Cash flow", "Funding & RERA account", "What if", "Inputs & sources", "Memo", "How it works"])

# ---------- 1. Decision ----------
with tabs[0]:
    box = {"Go": st.success, "Marginal": st.warning, "No-go": st.error}[ev["verdict"]]
    box(f"**{ev['verdict'].upper()}**  \n" + "  \n".join(f"{'✓' if ok else '✗'} {name}" for name, ok in ev["checks"]))
    st.caption("The verdict thresholds (hurdle rate, minimum profit on cost) are team assumptions to confirm with developers.")

    cards = [
        (f"Peak funding needed (Q{m['peak_quarter']})", cr(m["peak_funding"]), sw["peak_funding"],
         "The most outside money (equity + loan) the project needs at any one time."),
        ("Net present value (NPV)", cr(m["project_npv"]), sw["project_npv"],
         "All future cash in and out, valued in today's money at your hurdle rate. Above zero means the project beats the hurdle."),
        ("Yearly return (IRR)", pct(m["project_irr"]), sw["project_irr"],
         "Internal rate of return: the yearly return the project's cash flows earn. Compare it with the hurdle rate."),
        ("Profit on cost", pct(m["profit_on_cost"]), sw["profit_on_cost"],
         "Profit before tax divided by total cost including loan interest."),
        ("Break-even sale price", "n/a" if ev["breakeven_price"] is None else f"₹{ev['breakeven_price']:,.0f}/sq ft",
         sw["breakeven_price"], "The launch price at which NPV is exactly zero."),
        ("Maximum land price", cr(ev["breakeven_land"]), sw["breakeven_land"],
         "The land price at which NPV is exactly zero at the hurdle rate (the residual land value)."),
        ("Equity IRR", pct(m["equity_irr"]), sw["equity_irr"], "The yearly return on the developer's own money, after the loan."),
        ("Payback", "n/a" if m["payback_years"] is None else f"{m['payback_years']:.1f} years",
         "Years until the project's cumulative cash turns positive.", "Simple payback, no discounting."),
        ("NPV in the downside case", cr(ev["downside"]["metrics"]["project_npv"]),
         "Price −10%, construction cost +10%, sales 25% slower and 2 quarters late.", M.PRESET_NOTE),
    ]
    for row in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (label, value, sentence, help_text) in zip(cols, cards[row:row + 3]):
            with col:
                st.metric(label, value, help=help_text)
                st.caption(sentence)

    if res["warnings"]:
        st.subheader("Check these")
        for w in res["warnings"]:
            st.warning(w)

    q = list(range(res["T"] + 1))
    cum, total = [], 0.0
    for x in res["project_cf"]:
        total += x
        cum.append(total)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=q, y=cum, name="Project cash, cumulative (before loan)", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=q, y=[-max(0.0, o) for o in res["outstanding"]], name="Outside money in the project (shown negative)",
                             mode="lines"))
    fig.add_annotation(x=m["peak_quarter"], y=-m["peak_funding"], text=f"Peak: {cr(m['peak_funding'])} in Q{m['peak_quarter']}",
                       showarrow=True)
    fig.update_layout(height=380, xaxis_title="Quarter", yaxis_title="₹ crore", legend=dict(orientation="h", y=-0.25),
                      margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---------- 2. Cash flow ----------
ROWS = M.cash_flow_rows(res)
table = pd.DataFrame({name: vals for name, vals, _ in ROWS}, index=[f"Q{t}" for t in range(res["T"] + 1)]).T
table.insert(0, "Total", [sum(v) if summable else float("nan") for _, v, summable in ROWS])
with tabs[1]:
    st.subheader("Quarter by quarter")
    st.caption("₹ crore unless the row says otherwise. Every amount happens at the end of its quarter. Money out is shown as a positive cost.")
    st.dataframe(table.style.format("{:,.2f}", na_rep=""), use_container_width=True, height=720)
    st.download_button("Download as CSV", table.to_csv().encode(), "cash_flow.csv", "text/csv")

# ---------- 3. Funding & RERA account ----------
with tabs[2]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak loan", cr(m["peak_loan_balance"]), help="The highest loan balance.")
    c2.metric("Loan-to-cost", pct(m["loan_to_cost"]), help="Peak loan ÷ total project cost. Lenders cap this.")
    c3.metric("Debt service cover", "n/a" if m["dscr"] is None else f"{m['dscr']:.2f}x",
              help="Cash available (after costs and tax) ÷ (interest + principal) over the quarters the loan is being "
                   "repaid. Above 1 means repayments are covered. Team definition; confirm with a lender.")
    c4.metric("Lowest receivables cover", "n/a" if m["min_receivables_cover"] is None else f"{m['min_receivables_cover']:.2f}x",
              help="(Money still due from sold flats + value of unsold flats) ÷ loan balance, at its lowest point.")
    st.caption(f"Peak funding of {cr(m['peak_funding'])} in Q{m['peak_quarter']} is {cr(m['peak_equity'])} equity and "
               f"{cr(m['peak_loan'])} loan. The loan is repaid only from free cash, never from the RERA account.")
    fig = go.Figure()
    for name, series in (("RERA account balance", res["escrow_balance"]), ("Loan balance", res["loan_balance"]),
                         ("Outside money in the project", [max(0.0, o) for o in res["outstanding"]])):
        fig.add_trace(go.Scatter(x=list(range(res["T"] + 1)), y=series, name=name, mode="lines"))
    fig.update_layout(height=380, xaxis_title="Quarter", yaxis_title="₹ crore", legend=dict(orientation="h", y=-0.25),
                      margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"""
**How the RERA account works here.** {inp['escrow_pct']:.0f}% of every rupee collected from buyers goes into the
separate RERA account. Money comes out only to cover land and construction cost already spent, and only in
proportion to how complete the building is. The rest ({100 - inp['escrow_pct']:.0f}%) is free cash. Whatever is
left in the account is released at possession (Q{res['timeline']['possession']}).
""")

# ---------- 4. What if ----------
with tabs[3]:
    presets, sens, (base_npv, torn) = what_if(tuple(sorted(st.session_state["values"].items())))
    st.subheader("Three cases side by side")
    st.caption(M.PRESET_NOTE + " Downside: price −10%, cost +10%, sales 25% slower, 2 quarters late. "
               "Upside: price +5%, cost −5%, sales 15% faster.")
    st.dataframe(pd.DataFrame({name: {"NPV": cr(x["project_npv"]), "IRR": pct(x["project_irr"]),
                                      "Profit on cost": pct(x["profit_on_cost"]),
                                      "Peak funding": f"{cr(x['peak_funding'])} (Q{x['peak_quarter']})",
                                      "Equity IRR": pct(x["equity_irr"])} for name, x in presets.items()}),
                 use_container_width=True)

    st.subheader("Which assumption matters most?")
    fig = go.Figure()
    labels = [t[0] for t in torn][::-1]
    fig.add_trace(go.Bar(y=labels, x=[min(lo, hi) - base_npv for _, lo, hi in torn][::-1], base=base_npv,
                         orientation="h", name="Worse side", marker_color="#b0532a"))
    fig.add_trace(go.Bar(y=labels, x=[max(lo, hi) - base_npv for _, lo, hi in torn][::-1], base=base_npv,
                         orientation="h", name="Better side", marker_color="#0e6a5b"))
    fig.add_vline(x=base_npv, line_dash="dot")
    fig.update_layout(barmode="overlay", height=320, xaxis_title="Project NPV (₹ crore)",
                      margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Base NPV {cr(base_npv)}. Each bar moves one input by ±20% (delay: 0 to +4 quarters) and keeps the rest fixed.")

    st.subheader("Sensitivity table")
    st.dataframe(pd.DataFrame([{"Input": d, "Change": c, "NPV": cr(n), "IRR": pct(i), "Peak funding": cr(p),
                                "Equity IRR": pct(e)} for d, c, n, i, p, e in sens]),
                 use_container_width=True, hide_index=True)

# ---------- 5. Inputs & sources ----------
with tabs[4]:
    st.subheader("Every input, with its source")
    st.caption("Edit the Value column. 'sourced' = from a cited report or law. 'assumption' = a judgement to confirm. "
               "'illustrative' = placeholder until real project data is entered. Blank is better than invented.")
    rows = [{"Group": v["group"], "Input": v["label"], "Value": float(st.session_state["values"][k]), "Unit": v["unit"],
             "Flag": v["flag"], "Source": v["source"], "Date": v["date"], "key": k} for k, v in META["inputs"].items()]
    df = pd.DataFrame(rows)
    edited = st.data_editor(df, column_config={"key": None, "Value": st.column_config.NumberColumn(format="%.2f")},
                            disabled=["Group", "Input", "Unit", "Flag", "Source", "Date"], hide_index=True,
                            use_container_width=True, key="editor")
    new_values = {r["key"]: r["Value"] for r in edited.to_dict("records")}
    if new_values != st.session_state["values"]:
        st.session_state["values"] = new_values
        st.rerun()
    if st.button("Reset to the base case"):
        st.session_state["values"] = dict(BASE)
        st.session_state.pop("editor", None)
        st.rerun()

# ---------- 6. Memo ----------
with tabs[5]:
    text = M.memo(inp, META, ev)
    st.caption("Written from the numbers by a fixed template. No AI service is called, so the inputs never leave this computer.")
    st.code(text, language=None)
    st.download_button("Download memo (.txt)", text.encode(), "investment_memo.txt", "text/plain")

# ---------- 7. How it works ----------
with tabs[6]:
    st.markdown("""
### What the tool does, step by step
1. **Areas.** Built-up area = plot × FSI. Saleable area = built-up area × saleable ratio.
2. **Costs.** Land and stamp duty at Q0. Approval fees and premiums spread over the quarters before construction.
   Construction cost escalates each year and is spent along an S-curve (slow, fast, slow). Soft costs, contingency and
   marketing are percentages.
3. **Sales and collections.** A fixed share of the saleable area sells each quarter from launch. Buyers pay the booking
   amount, then in step with construction progress, then the rest at possession.
4. **Delay.** A delay stretches construction and moves possession. RERA Section 18 interest is then owed to buyers.
5. **RERA account.** A set share of collections goes into the separate account. Withdrawals cover only land and
   construction cost already spent, in proportion to completion.
6. **Tax.** Charged on cumulative profit; early losses are carried forward.
   **Rates.** The hurdle rates are effective annual rates (quarterly = (1 + r)^(1/4) − 1). The loan rate is a nominal
   annual rate with interest charged monthly, as banks quote it (quarterly = (1 + r/12)^3 − 1).
7. **Funding.** Each quarter, any shortfall is met by equity first, then the loan, up to their limits. Surplus repays the
   loan first (never from the RERA account), is held until possession, then returned to equity.
8. **Results.** NPV, IRR, payback, profit on cost, peak funding, lender ratios, break-even price and maximum land price.

### Plain meanings
- **NPV (net present value):** all cash in and out, valued today at your hurdle rate. Above zero beats the hurdle.
- **IRR (internal rate of return):** the yearly return the cash flows earn. If the cash flow changes sign more than once there may be several IRRs; then trust NPV and MIRR.
- **MIRR (modified IRR):** an IRR that assumes realistic borrowing and reinvestment rates, so it always has one answer.
- **Hurdle rate:** the minimum yearly return you want before you will do the project.
- **Profit on cost:** profit before tax ÷ total cost including interest.
- **Peak funding:** the most outside money (equity + loan) in the project at one time.
- **DSCR (debt service cover ratio):** cash available ÷ loan payments due. Above 1 means payments are covered.
- **Loan-to-cost:** loan ÷ total project cost.
- **Receivables cover:** (money still due from buyers + value of unsold flats) ÷ loan balance.
- **FSI (floor space index):** built-up area allowed per unit of plot area.

### Course links (CE725)
Effective quarterly rates (Ch 2), present worth / NPV (Ch 5), IRR and incremental analysis (Ch 7), multiple IRRs and
MIRR (Ch 8), escalation and inflation (Ch 9), tax (Ch 11), break-even (Ch 12), payback (Ch 1).

### Limits
One project, one phase. No joint-development or revenue-share deals, although these are common in Indian cities.
GST is passed through to the government, so revenue is shown net of GST. Tax uses a simplified cumulative-profit rule.
The RERA account balance is released at possession. The verdict thresholds are assumptions to confirm with developers.

### Privacy
Run locally, nothing leaves the computer. If you use a hosted copy, the inputs you type are processed on that server.
""")

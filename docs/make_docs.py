"""Build every written deliverable from live model results.

Run from this folder:  python3 make_docs.py
Rerun after changing tool/base_case.json or filling benchmark/benchmark_results.csv, so every number stays in sync.
Needs: python-docx, python-pptx, openpyxl, matplotlib (pip install python-docx python-pptx openpyxl matplotlib).
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tool"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402

import compare as C  # noqa: E402
import model as M  # noqa: E402

DATE = "1 Nov 2026"  # date the documents were regenerated and the checks run
TEAM = [("Ojas Somani", "23B4225", "Project lead and finance modeller"),
        ("Shivam Shankar", "23B1851", "AI and tool developer"),
        ("Mrunal Pachpande", "23B0723", "Validation engineer and data lead")]
TEAL, BRICK, INK, MUTED, GREY = "0E6A5B", "B0532A", "1A2421", "5A6964", "8A9792"
AMBER_BG, TEAL_BG, HEAD_BG = "FFF4D6", "E3F1EE", "0E6A5B"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

# ---------------- live results ----------------
INP, META = M.load_case()
EV = M.evaluate(INP)
RES, MET = EV["result"], EV["result"]["metrics"]
SW = M.so_what(INP, EV)
PRESETS = {n: M.run(M.scenario(INP, **p))["metrics"] for n, p in M.PRESETS.items()}
SENS = M.sensitivity(INP)
BASE_NPV, TORN = M.tornado(INP)
BENCH = C.compare(EV)
BENCH_ENTERED = [r for r in BENCH if r[3] is not None]
ILLUS = M.flagged_inputs(META, ("illustrative",))
ASSUM = M.flagged_inputs(META, ("assumption",))
SOURCED = M.flagged_inputs(META, ("sourced",))
TRAP = M.run({**INP, "sales_pace_pct": 25, "launch_q": 0})
# finance cost if the loan rate were (wrongly) treated as an effective annual rate, as before 27 Oct
OLD_LOAN = M.run({**INP, "loan_rate_pct": 1200 * ((1 + INP["loan_rate_pct"] / 100) ** (1 / 12) - 1)})["metrics"]
DELAY4 = M.run(M.scenario(INP, delay=4))["metrics"]
cr, pct = M.cr, M.pct


def money_psf(x):
    return "n/a" if x is None else f"₹{x:,.0f}/sq ft"


def run_tests():
    import test_api
    import test_model

    class Rec(unittest.TestResult):
        def __init__(self):
            super().__init__()
            self.log = []

        def addSuccess(self, t):
            super().addSuccess(t)
            self.log.append((t, "PASS"))

        def addFailure(self, t, e):
            super().addFailure(t, e)
            self.log.append((t, "FAIL"))

        def addError(self, t, e):
            super().addError(t, e)
            self.log.append((t, "ERROR"))

    rec = Rec()
    loader = unittest.defaultTestLoader
    unittest.TestSuite([loader.loadTestsFromModule(test_model), loader.loadTestsFromModule(test_api)]).run(rec)
    return [(t.__class__.__name__, t._testMethodName, status) for t, status in rec.log]


TEST_TEXT = {
    "test_s_curve_sums_to_one": "S-curve construction shares add up to 1 and match the published 8-quarter values",
    "test_collections_hand_case": "Collections formula matches a hand-worked 4-quarter case",
    "test_tax_carries_losses_forward": "Tax on cumulative profit carries early losses forward",
    "test_buyer_delay_interest": "RERA delay interest to buyers matches a hand calculation",
    "test_payback": "Payback interpolates inside the quarter; returns none if never repaid",
    "test_multiple_irr_course_example": "Detects 3 sign changes and the 5% root in course problem PS2 #15",
    "test_mirr_course_example": "MIRR reproduces 9.27% from course problem PS2 #17",
    "test_everything_sold_and_collected": "All saleable area is sold and every booking is collected",
    "test_escrow_never_negative_and_released": "RERA account never goes negative and is empty at the end",
    "test_loan_within_limit_and_repaid": "Loan stays within its limit and is repaid by the end",
    "test_cash_balances_every_quarter": "Sources equal uses of cash in every quarter",
    "test_npv_is_zero_at_irr": "NPV computed at the IRR is zero",
    "test_npv_moves_the_right_way": "NPV rises with price, falls with cost and with delay",
    "test_breakevens_give_zero_npv": "Break-even price and maximum land price both give NPV = 0",
    "test_no_sales": "Zero sales pace gives a plain warning, not a crash",
    "test_booking_above_rera_cap": "Booking above 10% is flagged against RERA Section 13",
    "test_funding_limits_too_small": "Small equity and loan limits trigger funding-gap warnings",
    "test_delay_costs_buyer_interest": "A delay creates buyer interest and a Section 18 warning",
    "test_negative_npv_flagged": "Negative NPV is flagged in plain language",
    "test_escrow_traps_cash_when_sales_run_ahead": "Fast early sales make the RERA account hold cash, with a warning",
    "test_escrow_share_is_an_input": "The RERA share is an input (0% and 100% both run)",
    "test_evaluate_and_memo_run": "Verdict and template memo are produced",
    "test_downside_not_applied_twice": "The downside case is the same whichever what-if case is selected",
    "test_fractional_quarters_rounded_with_warning": "A fractional quarter (12.7) is rounded to 13 with a plain warning",
    "test_loan_rate_is_nominal_charged_monthly": "Loan interest uses a nominal annual rate charged monthly: (1 + r/12)^3 − 1 a quarter",
    "test_unsold_at_horizon_is_flagged": "A sales pace too slow to sell out is flagged",
    "test_same_numbers_as_the_model": "The website API returns exactly the model's numbers, as valid JSON",
    "test_edited_inputs_are_no_longer_illustrative": "A value the user enters is no longer flagged illustrative",
    "test_bad_inputs_are_rejected_with_plain_messages": "Bad or out-of-range inputs are rejected with a plain message",
    "test_random_inputs_never_crash_and_keep_the_books_balanced": "300 random extreme scenarios: no crash, sources = uses every quarter, RERA balance ≥ 0, loan ≤ limit",
    "test_every_input_has_a_range": "Every input has an allowed range in the API",
}

EDGE_CASES = [
    ("No sales", {"sales_pace_pct": 0}, "Plain warning; model still runs"),
    ("Booking 15% (above the RERA cap)", {"booking_pct": 15}, "Warning citing RERA Section 13"),
    ("Equity and loan limits ₹5 cr each", {"equity_limit_cr": 5, "loan_limit_cr": 5}, "Funding gap and loan-limit warnings"),
    ("4-quarter delay", {"delay_q": 4}, "Buyer interest owed and a Section 18 warning"),
    ("Sale price ₹5,000/sq ft", {"price_psf": 5000}, "Negative NPV flagged"),
    ("Sales 25% a quarter from Q0", {"sales_pace_pct": 25, "launch_q": 0}, "RERA account holds cash; warning"),
    ("RERA share 100%", {"escrow_pct": 100}, "No free cash; model still runs"),
    ("RERA share 0%", {"escrow_pct": 0}, "Nothing goes into the account; model still runs"),
]

# ---------------- figures ----------------
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def fig_cash():
    q = list(range(RES["T"] + 1))
    cum, total = [], 0.0
    for x in RES["project_cf"]:
        total += x
        cum.append(total)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(q, cum, color=f"#{TEAL}", marker="o", ms=3, label="Project cash, cumulative (after tax, before loan)")
    ax.plot(q, [-max(0.0, o) for o in RES["outstanding"]], color=f"#{BRICK}", label="Outside money in the project (shown negative)")
    ax.axhline(0, color="#999", lw=0.8)
    ax.annotate(f"Peak funding {cr(MET['peak_funding'])} in Q{MET['peak_quarter']}",
                (MET["peak_quarter"], -MET["peak_funding"]), xytext=(MET["peak_quarter"] + 1.5, -MET["peak_funding"] * 0.9),
                arrowprops=dict(arrowstyle="->", color="#555"), fontsize=8)
    ax.set_xlabel("Quarter")
    ax.set_ylabel("₹ crore")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "cash.png", dpi=200)
    plt.close(fig)


def fig_tornado():
    rows = TORN[::-1]
    fig, ax = plt.subplots(figsize=(7, 2.8))
    for i, (name, lo, hi) in enumerate(rows):
        ax.barh(i, min(lo, hi) - BASE_NPV, left=BASE_NPV, color=f"#{BRICK}", height=0.55)
        ax.barh(i, max(lo, hi) - BASE_NPV, left=BASE_NPV, color=f"#{TEAL}", height=0.55)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.axvline(BASE_NPV, color="#333", ls=":", lw=1)
    ax.set_xlabel(f"Project NPV (₹ crore); base {cr(BASE_NPV)}")
    fig.tight_layout()
    fig.savefig(FIG / "tornado.png", dpi=200)
    plt.close(fig)


def fig_balances():
    q = list(range(RES["T"] + 1))
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.plot(q, [max(0.0, o) for o in RES["outstanding"]], color=f"#{BRICK}", label="Outside money (equity + loan)")
    ax.plot(q, RES["loan_balance"], color=f"#{GREY}", label="Loan balance")
    ax.plot(q, RES["escrow_balance"], color=f"#{TEAL}", label="RERA account balance")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("₹ crore")
    ax.legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIG / "balances.png", dpi=200)
    plt.close(fig)


def fig_costs():
    names = {"land": "Land", "stamp_duty": "Stamp duty", "approvals": "Approvals", "premiums": "Premiums",
             "construction": "Construction", "soft_costs": "Soft costs", "contingency": "Contingency",
             "marketing": "Marketing", "buyer_delay_interest": "Delay interest"}
    items = [(names[k], sum(v)) for k, v in RES["costs"].items() if sum(v) > 0]
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.barh([n for n, _ in items][::-1], [v for _, v in items][::-1], color=f"#{TEAL}")
    for i, (_, v) in enumerate(items[::-1]):
        ax.text(v, i, f" {v:.1f}", va="center", fontsize=8)
    ax.set_xlabel("₹ crore over the project")
    fig.tight_layout()
    fig.savefig(FIG / "costs.png", dpi=200)
    plt.close(fig)


# ---------------- Word helpers ----------------

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def runs(paragraph, text, size=None, color=None):
    """Add text with **bold** and `code` segments."""
    for part in re.split(r"(\*\*.*?\*\*|`.*?`)", text):
        if not part:
            continue
        code = part.startswith("`")
        r = paragraph.add_run(part.strip("`") if code else part.replace("**", "") if part.startswith("**") else part)
        r.bold = part.startswith("**")
        if code:
            r.font.name = "Consolas"
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
    return paragraph


def new_doc(title, subtitle):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.2))
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    st = doc.styles
    st["Normal"].font.name = "Calibri"
    st["Normal"].font.size = Pt(10.5)
    st["Normal"].paragraph_format.space_after = Pt(5)
    for name, size in (("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11)):
        st[name].font.name = "Cambria"
        st[name].font.size = Pt(size)
        st[name].font.color.rgb = RGBColor.from_string(TEAL)
    st["Title"].font.name = "Cambria"
    st["Title"].font.size = Pt(24)
    st["Title"].font.color.rgb = RGBColor.from_string(INK)
    doc.add_paragraph(title, style="Title")
    runs(doc.add_paragraph(), subtitle, size=10.5, color=MUTED)
    foot = sec.footer.paragraphs[0]
    foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    runs(foot, f"CE725 Topic 2 · {title} · page ", size=8, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    foot._p.append(fld)
    return doc


def h(doc, text, level=1):
    doc.add_heading(text, level)


def para(doc, text, italic=False, color=None, size=None):
    p = runs(doc.add_paragraph(), text, size=size, color=color)
    if italic:
        for r in p.runs:
            r.italic = True
    return p


def bullets(doc, items, style="List Bullet"):
    for it in items:
        runs(doc.add_paragraph(style=style), it)


def table(doc, header, rows, widths, size=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, text in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        runs(c.paragraphs[0], str(text), size=size, color="FFFFFF").runs[0].bold = True
        shade(c, HEAD_BG)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            runs(cells[i].paragraphs[0], "" if val is None else str(val), size=size)
    fix_widths(t, widths)
    doc.add_paragraph()
    return t


def fix_widths(t, widths):
    """Fixed layout with explicit column widths, so Word does not autofit the table."""
    tbl_pr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
        for cell in t.columns[i].cells:
            cell.width = Cm(w)


def box(doc, label, text, fill=AMBER_BG):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    fix_widths(t, [16.6])
    c = t.rows[0].cells[0]
    shade(c, fill)
    c.text = ""
    runs(c.paragraphs[0], f"**{label}** {text}", size=10)
    doc.add_paragraph()


def slot(doc, text):
    box(doc, "TEAM TO COMPLETE:", text)


def figure(doc, name, caption, width=16):
    doc.add_picture(str(FIG / name), width=Cm(width))
    para(doc, caption, italic=True, color=MUTED, size=9)


def inputs_table(doc, keys=None, size=8.5):
    rows = []
    for k, v in META["inputs"].items():
        if keys and k not in keys:
            continue
        val = v["value"]
        rows.append([v["group"], v["label"], f"{val:,}" if isinstance(val, (int, float)) else val, v["unit"], v["flag"]])
    table(doc, ["Group", "Input", "Value", "Unit", "Flag"], rows, [2.6, 5.4, 2.0, 4.6, 2.0], size=size)


def illus_note():
    return (f"{len(ILLUS)} inputs are illustrative placeholders and {len(ASSUM)} are assumptions, so the numbers below "
            "show how the tool works, not a real investment answer. They will update when the team's sample project replaces the placeholders.")


# ---------------- 1. Project charter ----------------

def charter():
    doc = new_doc("Project Charter", f"Annexure B format · CE725 Construction Economics and Finance · {DATE}")
    rows = [
        ["Team number", "Group 30"],
        ["Team members and roles", "; ".join(f"{name} ({roll}): {role}" for name, roll, role in TEAM)
         + ". Documentation and reflection are shared."],
        ["Topic selected", "Topic 2: Real Estate Project Feasibility and Financial Appraisal Tool"],
        ["Problem statement", "Real estate developers in India commit large sums to land, approvals and construction before knowing "
                              "whether a project is viable. Early appraisals often rely on rough spreadsheets that ignore cash-flow timing, "
                              "financing costs and regulatory constraints. This project builds a feasibility and financial appraisal tool "
                              "that models land, construction and approval costs, sales phasing, construction finance, the RERA 70% escrow "
                              "requirement and taxes. It calculates project and equity NPV and IRR, payback period, profit on cost, peak "
                              "funding requirement, lender metrics and break-even selling price. It also produces sensitivity tables and a "
                              "tornado chart, and drafts an investment memo."],
        ["Intended users of the tool", "Primary: small and mid-size residential developers and their finance staff, deciding whether to buy a "
                                       "land parcel and how much money they need until buyer collections catch up. Secondary: construction-finance "
                                       "officers at banks and NBFCs, real estate consultants and valuers, equity investors and JV partners, landowners."],
        ["Method(s) to be applied", "Quarterly discounted cash flow; project and equity NPV and IRR (MIRR and NPV when a cash flow changes sign "
                                    "more than once); payback; profit on cost; peak funding and its quarter; break-even selling price and "
                                    "maximum land price (residual land value) by bisection; RERA separate-account and construction-loan "
                                    "waterfall; one-at-a-time sensitivity with a tornado chart; base, downside and upside cases."],
        ["Data sources", "Knight Frank India Real Estate H1 2026 (prices, sales, unsold stock); ANAROCK construction-cost data 2021–2025 "
                         "and Q3 2026 market update; RBI House Price Index; IGR Maharashtra ready reckoner (eASR); CPWD Plinth Area Rates "
                         "and DSR 2023 (cross-check); MahaRERA project disclosures (Forms 1–3); RERA Act 2016 Sections 4, 13 and 18; "
                         "Income Tax Act Section 115BAA (via the CE725 lecture). Every input records its source, date and a "
                         "sourced/assumption/illustrative flag."],
        ["Build platform", "Python calculation engine; website (HTML/JavaScript) with one Python serverless function, hosted on Vercel; "
                           "Streamlit app for local use; plain Excel (independent benchmark, built without AI); GitHub (versions)."],
        ["Benchmark case for validation", "The team's sample residential project, recomputed independently in plain Excel without AI, "
                                          "plus a 3–4 quarter toy case solved by hand. Agreement target: ±0.1%."],
        ["Key risks to completion", "Short timeline; unreliable or invented market data; errors in escrow and financing logic; IRR not "
                                    "unique for non-simple cash flows; deployment failure on demo day; persona not yet validated by interviews."],
    ]
    table(doc, ["Item", "Details"], rows, [4.2, 12.4], size=9.5)
    doc.save(HERE / "Project_Charter.docx")


# ---------------- 2. User manual ----------------

WARNING_GUIDE = [
    ("Inputs are illustrative placeholders", "Some numbers are not real project data.",
     "Replace every 'illustrative' input in Inputs & sources before deciding."),
    ("Project NPV is negative", "The project does not earn your hurdle rate.",
     "Look at the maximum land price and break-even price; renegotiate land or rethink the product."),
    ("RERA account holds up to ₹X cr", "Buyers' money is locked until construction catches up.",
     "Arrange equity or loan for that period; do not count that cash as available."),
    ("RERA account never builds up", "Spending runs ahead of sales, so every deposit can be withdrawn at once.",
     "Sales pace, not RERA, limits your cash. Test slower sales in What if."),
    ("Equity and loan limits are not enough", "Peak funding is above the equity plus loan you entered.",
     "Raise more equity, negotiate a larger loan, or phase spending."),
    ("Loan limit is fully used", "The loan is drawn to its sanctioned limit.", "Check the quarter it happens and the cushion left."),
    ("Possession is late", "Delay interest is owed to buyers under RERA Section 18.", "See the cost in the Cash flow tab; confirm the rate."),
    ("Booking amount is above 10%", "RERA Section 13 caps the advance before a registered agreement.", "Lower the booking %."),
    ("IRR may not be unique", "The cash flow changes sign more than once.", "Decide on NPV; MIRR is shown as a single-answer return."),
]


def manual():
    doc = new_doc("User Manual", f"Land Deal Feasibility tool · for developers and their finance teams · {DATE}")
    h(doc, "1. What this tool answers")
    para(doc, "You are about to commit crores to a land deal. This tool answers two questions in a few minutes: **should you buy "
              "this land, and how much money do you need to survive until buyer collections catch up?** It also shows the numbers "
              "a lender or investor will ask about, and how the answer changes if prices fall, costs rise, sales slow or the project runs late.")
    para(doc, "It models one residential project, quarter by quarter, from the land purchase (Q0) to the last collection. "
              "Money is in ₹ crore unless a label says otherwise.")
    h(doc, "2. Starting the tool")
    bullets(doc, ["**Website:** open the link the team shares (to be added after deploying on Vercel) and go to the tool page. "
                  "Inputs are sent to a calculation function, used once and not stored; they are kept only in your own browser.",
                  "**Website on your own computer:** in the project folder run `python3 serve_local.py` and open http://localhost:8000. "
                  "Nothing you type leaves your computer.",
                  "**Streamlit version:** in the tool folder run `pip install -r requirements.txt`, then `streamlit run app.py`. "
                  "Same engine, same tabs."])
    h(doc, "3. A five-minute walkthrough")
    h(doc, "Step 1 · Enter your project (Inputs & sources tab)", 2)
    para(doc, "Every input shows its unit, source, date and a flag: **sourced** (from a cited report or law), **assumption** "
              "(a judgement to confirm) or **illustrative** (a placeholder). Replace every illustrative value with your project's numbers; "
              "on the website, a value you enter is flagged **your input**. A blank or clearly labelled guess is better than an invented number. "
              "Quarter inputs are whole numbers. On the website, **Save inputs to a file** keeps a deal you can load again or send to a colleague.")
    h(doc, "Step 2 · Read the Decision tab", 2)
    para(doc, "The top box gives a verdict, **Go**, **Marginal** or **No-go**, and the checks behind it. Below it, each number "
              "has one plain sentence saying what it means for you.")
    table(doc, ["Output", "What it means", "Illustrative base case"], [
        ["Peak funding needed", "The most outside money (equity + loan) in the project at one time, and the quarter it happens",
         f"{cr(MET['peak_funding'])} in Q{MET['peak_quarter']}"],
        ["Net present value (NPV)", "All cash in and out valued today at your hurdle rate. Above zero beats the hurdle.", cr(MET["project_npv"])],
        ["Yearly return (IRR)", "Internal rate of return: the yearly return the cash flows earn", pct(MET["project_irr"])],
        ["Profit on cost", "Profit before tax ÷ total cost including loan interest", pct(MET["profit_on_cost"])],
        ["Break-even sale price", "Launch price at which NPV = 0", money_psf(EV["breakeven_price"])],
        ["Maximum land price", "Land price at which NPV = 0 (residual land value)", cr(EV["breakeven_land"])],
        ["Equity IRR", "Yearly return on your own money, after the loan", pct(MET["equity_irr"])],
        ["Payback", "Years until cumulative project cash turns positive",
         "n/a" if MET["payback_years"] is None else f"{MET['payback_years']:.1f} years"],
    ], [3.6, 8.6, 4.4])
    para(doc, illus_note(), italic=True, color=MUTED, size=9)
    h(doc, "Step 3 · Ask \"what if\" (sidebar and What if tab)", 2)
    para(doc, "Pick **Base case**, **Downside** or **Upside**, or move the sliders: sale price, construction cost, sales pace and extra "
              "delay. Every number updates at once. The What if tab compares the three cases, ranks which input moves NPV most "
              "(tornado chart) and lists a full sensitivity table. The preset shocks are team assumptions, not forecasts.")
    h(doc, "Step 4 · Check the lender view (Funding & RERA account tab)", 2)
    para(doc, "Shows peak loan, loan-to-cost, debt service cover and receivables cover, with the RERA account, loan and outside-money "
              "balances over time. The loan is repaid only from free cash, never from the RERA account.")
    h(doc, "Step 5 · Take the memo (Memo tab)", 2)
    para(doc, "A one-page investment memo written from the results by a fixed template, with the verdict, key numbers, downside case, "
              "warnings and the inputs still to verify. No AI service is called. Download it as a text file. On the website, "
              "**Print summary for a lender** prints the verdict, numbers, warnings, chart and memo as clean pages (or saves them as a PDF).")
    h(doc, "4. Inputs reference")
    inputs_table(doc)
    h(doc, "5. Warnings and what to do")
    table(doc, ["Warning", "What it means", "What to do"], WARNING_GUIDE, [4.4, 6.0, 6.2])
    h(doc, "6. Key assumptions and limits")
    bullets(doc, [
        "One project, one phase, one tower type. Joint development and revenue-share deals are not modelled, although they are common in Indian cities.",
        "Cash flows happen at the end of each quarter. Hurdle rates are effective annual rates, so a quarter's rate is (1 + r)^(1/4) − 1. "
        "The loan rate is a nominal annual rate with interest charged monthly, as banks quote it, so a quarter's rate is (1 + r/12)^3 − 1.",
        "Construction cost is spent along an S-curve and escalates every year; % complete is the share of construction cost spent.",
        "Buyers pay the booking amount, then in step with construction, then the possession amount.",
        "RERA account: a set share of collections goes in; withdrawals cover only land, stamp duty, approvals, premiums and construction "
        "already spent, in proportion to completion. The balance is released at possession (a simplification).",
        "GST is passed through to the government, so revenue is net of GST.",
        "Tax is charged on cumulative profit with losses carried forward (a simplification of actual tax timing). Confirm the rate against the Act.",
        "Debt service cover is defined as cash available ÷ (interest + principal) over the repayment quarters. Confirm with your lender.",
        "The verdict thresholds (hurdle rate, minimum profit on cost) are assumptions to set for your own business.",
    ])
    h(doc, "7. Privacy and accountability")
    para(doc, "Run locally, your project data stays on your computer. On the hosted website, inputs go to a calculation function "
              "on Vercel's servers, are used once and are not stored by the tool; avoid confidential deals there and run it locally instead. "
              "The tool supports a decision; the person who signs the land deal remains responsible for it, "
              "and every input marked assumption or illustrative should be checked first.")
    doc.save(HERE / "User_Manual.docx")


# ---------------- 3. Validation report ----------------

def validation(tests):
    doc = new_doc("Validation Report", f"How we know the tool's numbers are right · {DATE}")
    box(doc, "Status:", "The automated checks below were run on " + DATE + ". The independent Excel benchmark "
             + ("has been entered and compared." if BENCH_ENTERED else "has not been entered yet; section 6 shows the tool's values ready for comparison."),
        fill=TEAL_BG)
    h(doc, "1. Why validation comes first")
    para(doc, "A developer will only trust a number he can trace, and a lender looks for numbers that hold up. The course brief "
              "makes the same point: a tool that runs but has not been checked against a manual benchmark earns limited credit. "
              "So every output is checked three ways:")
    bullets(doc, ["**Automated self-checks** (section 4): invariants and small hand-checkable cases, written with AI assistance and disclosed as such.",
                  "**An independent benchmark** (section 6): the base case recomputed by the team in plain Excel, without AI and without reading the code.",
                  "**A toy case by hand** (section 7): a 3–4 quarter example worked on paper to confirm timing and sign conventions."])
    h(doc, "2. Benchmark case")
    para(doc, f"Project: {META['project_name']}. " + illus_note())
    inputs_table(doc)
    h(doc, "3. Conventions both the tool and the benchmark follow")
    bullets(doc, ["Quarters Q0, Q1, …; every amount at the end of its quarter; land paid in Q0; money in +, money out −; ₹ crore.",
                  f"Hurdle rates are effective annual rates: (1 + r)^(1/4) − 1 a quarter. At a {INP['hurdle_rate_pct']:.0f}% hurdle that is "
                  f"{M.q_rate(INP['hurdle_rate_pct']):.2%} a quarter, not {INP['hurdle_rate_pct'] / 4:.2f}%.",
                  f"The loan rate is nominal annual with interest charged monthly: (1 + r/12)^3 − 1 a quarter. At {INP['loan_rate_pct']:.0f}% "
                  f"that is {M.q_rate_loan(INP['loan_rate_pct']):.2%} a quarter. Interest is charged on the opening loan balance.",
                  "Quarter inputs are whole numbers.",
                  "Construction share in quarter k of n: S(k/n) − S((k−1)/n) with S(x) = 3x² − 2x³.",
                  "Collections: cumulative bookings × [booking% + (1 − booking% − possession%) × % complete + possession% after possession].",
                  "Tolerance for agreement: ±0.1%."])
    h(doc, "4. Automated checks")
    passed = sum(s == "PASS" for _, _, s in tests)
    para(doc, f"**{passed} of {len(tests)} checks pass.** Run them with `python3 -m unittest -v test_model.py test_api.py` in the tool folder.")
    table(doc, ["Group", "What is checked", "Result"],
          [[g.replace("Pieces", "Building blocks").replace("BaseCase", "Base case").replace("EdgeCases", "Edge cases")
             .replace("Fixes", "Regression").replace("Api", "Website API"),
            TEST_TEXT.get(n, n), s] for g, n, s in tests], [2.8, 11.6, 2.2])
    h(doc, "5. Edge cases: warn, don't crash")
    rows = []
    for name, change, expect in EDGE_CASES:
        w = M.run({**INP, **change})["warnings"]
        rows.append([name, expect, (w[0][:150] + ("…" if len(w[0]) > 150 else "")) if w else "Ran; no warning"])
    table(doc, ["Case", "Expected", "What the tool said (first warning)"], rows, [3.6, 4.4, 8.6], size=8.5)
    h(doc, "Sensitivity sanity check", 2)
    para(doc, "NPV must rise with price and fall with construction cost, land price and delay. The tool's results:")
    table(doc, ["Input", "Change", "NPV", "IRR", "Peak funding"],
          [[d, c, cr(n), pct(i), cr(p)] for d, c, n, i, p, _ in SENS], [4.2, 2.6, 3.4, 2.6, 3.8], size=8.5)
    h(doc, "6. Tool vs independent benchmark")
    rows = [[k, u, "" if t is None else f"{t:,.4f}", "" if b is None else f"{b:,.4f}",
             "" if rel is None else f"{rel:.3%}", s] for k, u, t, b, d, rel, s in BENCH]
    table(doc, ["Output", "Unit", "Tool", "Benchmark", "Rel. diff", "Status"], rows, [4.6, 2.2, 2.6, 2.6, 1.8, 2.8], size=8)
    if not BENCH_ENTERED:
        slot(doc, "Build benchmark.xlsx by hand (see benchmark/README.md), enter the results in benchmark/benchmark_results.csv, "
                  "run `python3 compare.py`, then rerun `python3 make_docs.py` to refresh this table.")
    h(doc, "Discrepancies and how they were resolved", 2)
    slot(doc, "For every row marked DIFFERENT: the cause (tool, benchmark or method) and the fix. Keep rows where the benchmark "
              "was wrong too; they show the check worked.")
    h(doc, "7. Toy case by hand")
    slot(doc, "Attach the scan or photo of the hand-worked toy case and note whether the tool matched it.")
    h(doc, "8. Issues found while building the tool")
    para(doc, "These were caught by the checks above or by reading the outputs, before the benchmark comparison:")
    table(doc, ["Issue", "How it was caught", "Fix"], [
        ["A web-search summary gave construction-cost escalation as about 6.9% a year from ANAROCK data.",
         "Recomputing from the two published endpoints: (3,604 / 2,681)^(1/4) − 1 = 7.7% a year.",
         "The input uses 7.7% and records the calculation as its source."],
        ["The break-even price sentence said prices \"can fall\" to a level that was actually above the assumed price.",
         "Reading the Decision page with a negative-NPV base case.", "The sentence now depends on whether break-even is above or below the assumption."],
        ["The RERA warning described normal behaviour (deposits withdrawn at once) as a shortfall in 17 quarters.",
         "The RERA account balance stayed at zero in every quarter.",
         "Two separate messages: cash held in the account, or the account never building up because sales lag spending."],
        ["Negative amounts showed as ₹-6.4 cr with inconsistent rounding.", "Reading the Decision page.", "One formatter: −₹6.35 cr everywhere."],
        ["With the Downside preset selected, the 'downside case' card shocked the deal a second time (−₹31.25 cr instead of −₹18.55 cr), "
         "and the verdict used that number.", "Re-verification on 27 Oct: comparing the card with a direct downside run.",
         "The downside case is always built from the user's inputs before any what-if shocks; a regression check guards it."],
        ["A fractional quarter (e.g. a 12.7-quarter build) was silently cut to 12.", "Re-verification: probing quarter inputs.",
         "Quarters are rounded to the nearest whole number with a plain warning; the website only accepts whole quarters."],
        [f"The loan rate was treated as an effective annual rate, understating interest (finance cost {cr(OLD_LOAN['finance_cost'])}).",
         "Re-verification: Indian construction loans charge interest monthly on a nominal annual rate.",
         f"Quarterly loan rate = (1 + r/12)^3 − 1; finance cost is now {cr(MET['finance_cost'])}."],
        ["On the website every tab's content was shown at once, because a style overrode the hidden attribute.",
         "Re-verification: checking which panels were displayed, not only that each had content.",
         "Hidden content is always hidden; charts are drawn when their tab opens."],
        ["The website kept inputs saved in a browser even after the example project changed.", "Re-verification: reading the save logic.",
         "Saved inputs are tied to the example project; if it changes they are reset with a notice."],
    ], [5.4, 5.6, 5.6], size=8.5)
    h(doc, "9. Conclusion")
    slot(doc, "Summarise whether the tool matched the benchmark within ±0.1%, what the comparison taught you, and what you changed.")
    doc.save(HERE / "Validation_Report.docx")


# ---------------- 4. Reflection report ----------------

def reflection():
    doc = new_doc("Learnings and Reflection Report", f"CE725 Topic 2 · structure as in section 7 of the course brief · {DATE}")
    box(doc, "Disclosure:", "This draft was written with AI assistance (Claude, Anthropic) from the team's tool, results and notes, "
             "and is listed in the AI usage log. Sections 1–4 and 6 must be read, checked against the tool and rewritten in the "
             "team's own words before submission. Section 5 is left for each member to write personally.")
    m, h_rate = MET, INP["hurdle_rate_pct"]
    poc_ok = (m["profit_on_cost"] or 0) >= INP["min_profit_on_cost_pct"] / 100
    h(doc, "1. Subject learnings")
    para(doc, illus_note(), italic=True, color=MUTED, size=9)
    h(doc, "Timing, not just profit, decides a land deal", 2)
    if poc_ok and m["project_npv"] < 0:
        para(doc, f"Our illustrative base case makes a profit on cost of {pct(m['profit_on_cost'])}, above the "
                  f"{INP['min_profit_on_cost_pct']:.0f}% rule of thumb, yet its NPV at a {h_rate:.0f}% hurdle is {cr(m['project_npv'])}. "
                  "The difference is time. Land, stamp duty and premiums are paid at the start, while buyers pay in stages over the "
                  "following years. An undiscounted margin hides that; present worth (Ch 5) does not. This is the clearest lesson "
                  "from the course applied to a real decision.")
    else:
        para(doc, f"Profit on cost is {pct(m['profit_on_cost'])} and NPV at a {h_rate:.0f}% hurdle is {cr(m['project_npv'])}. "
                  "Profit on cost ignores when money moves; NPV (Ch 5) does not. Land, stamp duty and premiums are paid at the start "
                  "while buyers pay in stages, so the two measures can disagree.")
    figure(doc, "costs.png", "Where the money goes over the project (₹ crore).", width=14)
    para(doc, f"Quarterly modelling also needed the effective-rate idea from Ch 2: a {h_rate:.0f}% annual hurdle is "
              f"{M.q_rate(h_rate):.2%} a quarter, not {h_rate / 4:.2f}%. Using the nominal quarter rate would have overstated "
              "the discounting slightly in every period.")
    para(doc, f"The same chapter caught a mistake in our own model. We first treated the {INP['loan_rate_pct']:.0f}% loan rate as an "
              f"effective annual rate ({M.q_rate(INP['loan_rate_pct']):.2%} a quarter). Banks quote a nominal annual rate and charge "
              f"interest monthly, which is {M.q_rate_loan(INP['loan_rate_pct']):.2%} a quarter. Finance cost moved from "
              f"{cr(OLD_LOAN['finance_cost'])} to {cr(MET['finance_cost'])}. Nominal versus effective rates is not a textbook detail: "
              "it changes what a developer pays.")
    h(doc, "Peak funding is the number a developer lives or dies by", 2)
    para(doc, f"The project needs up to {cr(m['peak_funding'])} of outside money, reached in Q{m['peak_quarter']} "
              f"({cr(m['peak_equity'])} equity and {cr(m['peak_loan'])} loan). Profitable developers fail when they cannot fund that "
              "gap, which is why the tool leads with it.")
    figure(doc, "cash.png", "Cumulative project cash and outside money in the project, by quarter.", width=15)
    h(doc, "The RERA account changes when cash is available", 2)
    trap = max(TRAP["escrow_balance"])
    base_trap = max(RES["escrow_balance"])
    para(doc, f"RERA sends {INP['escrow_pct']:.0f}% of collections to a separate account that can be drawn only in step with "
              f"construction. In our base case the account {'never holds cash, because' if base_trap < 0.01 else f'holds up to {cr(base_trap)}, because'} "
              f"{'spending runs ahead of sales and every deposit can be withdrawn at once' if base_trap < 0.01 else 'sales run ahead of construction'}. "
              f"When sales are fast and start before construction (25% of area a quarter from Q0), the account holds up to {cr(trap)} "
              "that the developer cannot touch. Modelling the rule, rather than assuming 30% free cash, showed us that the constraint "
              "depends on the sales pattern.")
    h(doc, "IRR needs care with real estate cash flows (Ch 7–8)", 2)
    para(doc, f"The project IRR is {pct(m['project_irr'])} and the equity IRR {pct(m['equity_irr'])}. The project cash flow changes sign "
              f"{m['sign_changes']} time(s). Development cash flows can change sign more than once (for example a late cost after "
              "sales), and then several IRRs can exist. The tool counts sign changes, warns, and falls back on NPV and MIRR, as in "
              "course problems PS2 #15 and #17, which its automated checks reproduce.")
    h(doc, "Break-even analysis becomes a negotiating number (Ch 12)", 2)
    bl, bp = EV["breakeven_land"], EV["breakeven_price"]
    para(doc, f"Solving NPV = 0 for the land price gives the residual land value: {cr(bl) if bl is not None else 'none'} against "
              f"an assumed {cr(INP['land_price_cr'])}. Solving for the sale price gives {money_psf(bp)}. These two numbers "
              "turn the appraisal into something a developer can take into a land negotiation.")
    h(doc, "Escalation against price growth (Ch 9) and tax (Ch 11)", 2)
    para(doc, f"Construction cost escalates at {INP['cost_escalation_pct']:.1f}% a year in our inputs while prices grow at "
              f"{INP['price_growth_pct']:.1f}%. Every quarter of delay therefore widens the gap: a 4-quarter delay moves NPV from "
              f"{cr(m['project_npv'])} to {cr(DELAY4['project_npv'])}, before counting buyer interest under RERA Section 18. "
              "Tax is modelled on cumulative profit with losses carried forward; loan interest is deductible, which lowers the "
              "effective cost of debt, as in the taxation lecture.")
    figure(doc, "tornado.png", "Project NPV with one input moved ±20% (delay: 0 vs +4 quarters).", width=15)
    h(doc, "2. AI capability assessment")
    para(doc, "**Where AI accelerated the work.** Structuring the model into small testable steps, writing the Streamlit app, the "
              "website and its charts, generating automated checks, searching for market reports, and drafting the documents from live "
              "results. Work that would have taken days took hours.")
    para(doc, "**Where AI was wrong or unreliable (specific examples):**")
    bullets(doc, [
        "**Wrong figure relayed from a summary.** A web-search summary reported ANAROCK construction-cost growth as about 6.9% a year. "
        "Recomputing from the two published values (₹2,681 in 2021, ₹3,604 in 2025) gives 7.7%. The weekend plan page had already "
        "quoted 6.9%; the tool uses 7.7%.",
        "**Conflicting sources presented together.** Search results on Maharashtra ready reckoner rates for 2026-27 included both "
        "\"rates frozen\" (several sources) and \"revised about 5%\" (one article). The AI flagged the conflict, but a careless reader could have used either.",
        "**Unsourced blog figures.** Several construction-cost-per-sq-ft results were marketing blogs with no stated source or scope; they were not used.",
        "**Missing data, correctly left blank.** No current construction-finance interest rate was found, so the loan rate is an "
        "assumption to replace with a term sheet rather than an invented market figure.",
        "**Logic bugs in AI-written code.** The break-even sentence gave the wrong direction when NPV was negative, and a RERA warning "
        "described normal behaviour as a problem. Both were found by reading the outputs, not by the code running without errors.",
        "**Tool limits.** The web fetch tool could not read the Knight Frank PDF (compressed binary); the figures had to be extracted locally and checked page by page.",
        "**A bug that ran without errors.** Choosing the Downside case made the tool shock the deal twice when showing the downside "
        "NPV (−₹31.25 cr instead of −₹18.55 cr), and the verdict used that number. The AI-written code passed every check at the "
        "time; it was found only when we re-verified by comparing the card with a direct calculation.",
        "**Silent assumptions.** The code quietly cut fractional quarters (12.7 became 12) and treated the loan rate as an effective "
        "rate. Neither broke anything visibly; both changed numbers without saying so.",
        "**A website that looked finished.** Every tab's content was being shown at once, because one style rule overrode the hidden "
        "attribute. An earlier check confirmed that each tab had content, but not that the others were hidden: a lesson in checking "
        "what the user actually sees.",
    ])
    slot(doc, "Add your own examples from your AI usage log: prompts where the AI produced a wrong formula, assumption, data point or "
              "code, how you noticed, and what you did.")
    h(doc, "3. Validation insights")
    para(doc, f"The automated checks (sources equal uses of cash every quarter, NPV zero at the IRR, collections equal bookings, "
              "break-evens giving NPV = 0) caught structural errors early. They cannot catch a wrong method that is applied consistently; "
              "only the independent benchmark can.")
    slot(doc, "What the comparison with your hand-built Excel benchmark revealed: which outputs matched, which did not, the causes, "
              "and what you would check first next time.")
    h(doc, "4. Practical relevance")
    para(doc, "**Would a developer use it?** It answers the question a small or mid-size developer asks before a land deal, leads with "
              "peak funding and a maximum land price, and shows every input's source. To be used for real it would need the "
              "developer's own data, joint-development and phased-project structures, an export to the lender's format, and "
              "agreed definitions of the lender ratios.")
    para(doc, "**Would a lender trust it?** The tool shows loan-to-cost, debt service cover and receivables cover with plain definitions, "
              "but lenders usually rebuild numbers in their own templates. The validation report and the audit trail of inputs are what "
              "would earn trust.")
    para(doc, "**Open questions to test with users:** does the developer use residual land value or only profit on cost; which cost line "
              "surprises them most; would a lender accept the tool's ratios; which assumption is hardest to source; what would make them "
              "trust this over their own spreadsheet.")
    slot(doc, "Record the 1–2 interviews or the practitioner test: who (role only), what they said, what you changed. This also earns the brief's bonus credit.")
    h(doc, "5. Individual reflections")
    for name, roll, role in TEAM:
        h(doc, f"{name} ({roll}) · {role}", 3)
        slot(doc, "Half a page in your own words, without AI: your role, what you built or checked, what you learnt about construction "
                  "economics, and one thing you would do differently.")
    h(doc, "6. Ethics and limitations")
    bullets(doc, [
        "**Data reliability.** Every input carries a source, date and flag. Illustrative placeholders are labelled on screen, in the memo and in these documents, so they cannot be mistaken for market data.",
        "**Over-reliance on AI.** AI wrote much of the code and the first drafts. The team's safeguards are the independent benchmark, the automated checks, and the requirement that every member can explain every formula.",
        "**Accountability.** The tool supports a decision; it does not make it. The developer who signs the land deal, and the lender who funds it, remain responsible.",
        "**Privacy.** Run locally, nothing leaves the computer. On the hosted website, inputs go to a calculation function on Vercel's servers and are not stored; a visitor's inputs are kept only in their own browser. The memo is written by a fixed template, not an AI service. Confidential deals should be run locally.",
        "**Model limits.** Single phase; no joint-development deals; simplified tax timing; RERA account released at possession; verdict thresholds that still need validation with developers.",
    ])
    h(doc, "Sources")
    bullets(doc, [
        "Knight Frank, India Real Estate: Residential and Office Market, January–June 2026.",
        "ANAROCK construction-cost data 2021–2025, reported by Free Press Journal, 5 Sep 2026; ANAROCK Q3 2026 residential update (Business Today, 29 Sep 2026).",
        "Reserve Bank of India, House Price Index, Q1 2026-27 release.",
        "IGR Maharashtra, Annual Statement of Rates 2026-27 (eASR).",
        "Real Estate (Regulation and Development) Act 2016, Sections 4(2)(l)(D), 13 and 18.",
        "CE725 lecture notes and practice problem sets (time value of money, PW, IRR, MIRR, inflation, taxation, break-even).",
    ])
    doc.save(HERE / "Reflection_Report.docx")


# ---------------- 5. AI usage log ----------------

AI_LOG = [
    ("Project plan: roles for a 3-person team, scope, day-by-day timeline to 1 Nov", "Shareable plan page with roles, Must/Should/Could scope, timeline, risks", "Check the dates and weights against the course brief"),
    ("Find real construction and housing data reports for the model", "List of reports: Knight Frank H1 2026, ANAROCK Q3 2026 and cost data, RBI HPI, JLL, CPWD, IGR, MahaRERA, listed-developer results, WPI", "Open each original report; note conflicts (ready reckoner freeze vs revision)"),
    ("Extract city figures from the Knight Frank H1 2026 PDF", "Pune ₹10,063/sq ft (+5%), Mumbai ₹14,948/sq ft, quarters-to-sell and unsold stock by city", "Compare against the PDF pages (Pune p88, Mumbai p66)"),
    ("Weekend sprint spec: formulas for model v1", "S-curve, collections formula, metrics definitions, self-checks", "Ojas reviews each formula against the course notes"),
    ("Construction-cost escalation rate", "Search summary gave ~6.9%/yr; recomputed from endpoints as 7.7%/yr", "Recompute (3604/2681)^(1/4) − 1 yourselves"),
    ("Re-centre the design on USER_CONTEXT.md (developer persona)", "Decision-first summary, peak funding quarter, max land price, presets, plain warnings", "Check each feature traces to a stated user need"),
    ("Model architecture: quarterly periods, conventions, pure functions", "tool/model.py structure and conventions", "Team can explain each function and its course chapter"),
    ("RERA separate-account withdrawal rule", "Withdrawals capped by balance, % complete × eligible budget and cost incurred; balance released at possession", "Confirm eligible cost heads against MahaRERA Form 3 and state rules"),
    ("Funding waterfall", "Equity first, then loan; surplus repays loan, held until possession, then to equity", "Benchmark peak funding by hand"),
    ("Tax treatment", "Tax on cumulative profit, losses carried forward, rate as input (25.17% flagged to confirm)", "Confirm rate and timing with the Act / a CA"),
    ("DSCR definition under cash-sweep repayment", "Cash available ÷ (interest + principal) over repayment quarters", "Ask a lender whether this definition is acceptable"),
    ("Delay interest owed to buyers (RERA s.18)", "Quarterly interest on amounts paid, from promised to actual possession; rate as input", "Confirm the rate in the state RERA rules"),
    ("Break-even price and maximum land price", "Bisection on NPV = 0", "Goal Seek in the Excel benchmark"),
    ("Go / Marginal / No-go verdict rule", "NPV ≥ 0, profit on cost ≥ threshold, funding covered, downside NPV ≥ 0", "Validate the rule and thresholds with a developer"),
    ("Illustrative base case values", "Placeholder plot, FSI, land, premiums, timeline, limits, all flagged 'illustrative'", "Replace with the team's sample project"),
    ("Streamlit app design", "Seven tabs, so-what sentences, warnings, inputs table with sources", "Peer test with classmates"),
    ("Automated checks", "22 unittest checks on 23 Oct incl. course problems PS2 #15 and #17 (31 after 27 Oct, 33 after 1 Nov)", "Read each test and run it"),
    ("compare.py and benchmark instructions", "Script that fills the discrepancy table from the team's Excel results", "Use it after building the benchmark by hand"),
    ("Investment memo", "Template-based memo (no AI service called, for privacy)", "Read the memo against the Decision page"),
    ("Project charter rows", "Methods, data sources, platform, benchmark case, risks", "Team edits wording"),
    ("User manual draft", "Walkthrough, inputs reference, warnings guide, limits, privacy", "Have a peer follow it without help"),
    ("Validation report draft", "Automated-check results, edge cases, sensitivity, discrepancy table with team slots", "Fill team slots after the benchmark"),
    ("Reflection report draft", "Sections 1–4 and 6 drafted from results; section 5 left to members", "Rewrite in your own words; add your own AI examples"),
    ("Presentation draft", "13 slides with speaker notes and timings", "Rehearse; every member explains every formula"),
]

# later entries: (date, purpose, output, suggested check)
AI_LOG_LATER = [
    ("25 Oct 2026", "Build a website to host on Vercel", "Landing page and tool page (HTML/JS, Chart.js) calling one Python function that reuses tool/model.py", "Open every tab; compare numbers with the Streamlit app"),
    ("25 Oct 2026", "Input validation for the website's API", "Allowed range for every input, plain error messages, request-size limit", "Try bad inputs (text, huge numbers) and read the messages"),
    ("25 Oct 2026", "Vercel configuration", "vercel.json (static web/ folder, Python function, clean URLs, security headers), .vercelignore", "Deploy a preview; check /tool and /api/evaluate"),
    ("27 Oct 2026", "Re-verify the whole project", "Ran all checks, probed edge cases, re-checked Vercel docs and RERA Sections 13 and 18", "Repeat one probe yourselves"),
    ("27 Oct 2026", "Finding: downside case applied twice when the Downside preset was selected", "Fixed: downside always built from unshocked inputs; regression check added", "Select Downside and compare the card with the Downside column in What if"),
    ("27 Oct 2026", "Finding: loan rate convention", "Changed from effective annual to nominal annual charged monthly; finance cost rises", "Recompute one quarter's interest by hand"),
    ("27 Oct 2026", "Finding: fractional quarters silently truncated", "Now rounded with a warning; website accepts whole quarters only", "Enter 12.7 quarters and read the warning"),
    ("27 Oct 2026", "Finding: website showed every tab at once; saved inputs survived a changed example", "Fixed both; charts drawn when their tab opens; printable lender summary added", "Check on a phone and in print preview"),
    ("1 Nov 2026", "Full review of code, website and documents", "Ran all checks and edge-case probes; list of fixes in CHANGES_REPORT.md", "Read the report; repeat one probe yourselves"),
    ("1 Nov 2026", "Finding: maximum land price said 'even free land fails' for very profitable deals", "Fixed: search range widens until NPV turns negative; regression check added", "Set sale price to ₹60,000/sq ft and land to ₹2 cr; read the Maximum land price card"),
    ("1 Nov 2026", "Finding: 0% profit on cost failed a 0% threshold", "Fixed: explicit check for a missing value instead of treating 0 as missing", "Set the threshold to 0 and check the verdict list"),
    ("1 Nov 2026", "Finding: Streamlit app kept calling edited inputs 'illustrative'", "Fixed: edited inputs are flagged 'your input' in the banner, inputs table and memo", "Edit the land price in the Streamlit app and read the banner"),
    ("1 Nov 2026", "Website redesign (Group 30 branding)", "Cash drawn as a site section with ₹0 datum, stamp-style verdict, lead numbers, drawing title block footer", "Open on a phone, in dark mode and in print preview"),
    ("27 Oct 2026", "Random sweep test", "300 random extreme scenarios: no crash, sources = uses, RERA balance ≥ 0, loan ≤ limit", "Read the test; change the seed and rerun"),
]


def ai_log():
    wb = Workbook()
    ws = wb.active
    ws.title = "AI usage log"
    head = ["No.", "Date", "Tool", "Purpose / Prompt summary", "Output summary", "Decision (Accept / Modify / Reject)",
            "Reason and verification", "Suggested check (delete when done)"]
    ws.append(head)
    entries = [("23 Oct 2026", *e) for e in AI_LOG] + AI_LOG_LATER
    for i, (date, purpose, output, check) in enumerate(entries, 1):
        ws.append([i, date, "Claude (Claude Code)", purpose, output, "", "", check])
    widths = [5, 12, 18, 42, 52, 18, 40, 40]
    for col, w in zip("ABCDEFGH", widths):
        ws.column_dimensions[col].width = w
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for cell in row[5:7]:
            cell.fill = PatternFill("solid", fgColor=AMBER_BG)
    ws.freeze_panes = "A2"
    notes = wb.create_sheet("How to use")
    for line in [
        "Annexure A format from the course brief. Keep adding entries as you work; do not reconstruct the log at the end.",
        f"Rows 1–{len(AI_LOG) + len(AI_LOG_LATER)} list the significant AI contributions made with Claude between 23 Oct and 1 Nov 2026. The amber columns are yours to fill:",
        "Decision = Accept, Modify or Reject; Reason and verification = why, and how you checked it.",
        "Add your own prompts (other AI tools, your own Claude sessions) as new rows. The brief asks for at least 20 significant entries per team.",
        "Rejected and modified entries show critical judgement, which is what this part of the grade rewards.",
    ]:
        notes.append([line])
    notes.column_dimensions["A"].width = 120
    wb.save(HERE / "AI_Usage_Log.xlsx")


if __name__ == "__main__":
    for f in (fig_cash, fig_tornado, fig_balances, fig_costs):
        f()
    tests = run_tests()
    charter()
    manual()
    validation(tests)
    reflection()
    ai_log()
    import make_deck  # noqa: E402

    make_deck.build(EV, PRESETS, TORN, BASE_NPV, tests, BENCH_ENTERED, ILLUS)
    print(f"Done. {sum(s == 'PASS' for *_, s in tests)}/{len(tests)} checks pass. Files in {HERE}")

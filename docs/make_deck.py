"""15-minute presentation built from live model results. Called by make_docs.py."""
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

import model as M

HERE = Path(__file__).parent
TEAL, TEAL_LIGHT, TEAL_MID = RGBColor(0x0E, 0x6A, 0x5B), RGBColor(0xE3, 0xF1, 0xEE), RGBColor(0x5F, 0xA6, 0x96)
BRICK, BRICK_LIGHT = RGBColor(0xB0, 0x53, 0x2A), RGBColor(0xF8, 0xE6, 0xDC)
INK, MUTED, WHITE, LINE = RGBColor(0x1A, 0x24, 0x21), RGBColor(0x5A, 0x69, 0x64), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xD5, 0xDD, 0xD9)
HEAD, BODY = "Cambria", "Calibri"
W, H = 13.333, 7.5
cr, pct = M.cr, M.pct


def text(slide, x, y, w, h, content, size=16, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    """content: a string, or a list of strings / (string, options) for several paragraphs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    items = content if isinstance(content, list) else [content]
    for i, item in enumerate(items):
        txt, opt = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = opt.get("align", align)
        p.space_after = Pt(opt.get("space", 6))
        r = p.add_run()
        r.text = txt
        f = r.font
        f.size = Pt(opt.get("size", size))
        f.bold = opt.get("bold", bold)
        f.color.rgb = opt.get("color", color)
        f.name = opt.get("font", font)
    return tb


def card(slide, x, y, w, h, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def badge(slide, x, y, label, fill=TEAL, size=0.55):
    s = card(slide, x, y, size, size, fill, MSO_SHAPE.OVAL)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(label)
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(16), True, WHITE, BODY
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return s


def title(slide, t, sub=None):
    text(slide, 0.6, 0.45, W - 1.2, 0.9, t, size=34, bold=True, font=HEAD, name="Title")
    if sub:
        text(slide, 0.6, 1.25, W - 1.2, 0.5, sub, size=15, color=MUTED)


def new_slide(prs, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = TEAL if dark else WHITE
    return s


def stat(slide, x, y, w, value, label, color=TEAL, fill=TEAL_LIGHT, h=1.7):
    card(slide, x, y, w, h, fill)
    text(slide, x + 0.2, y + 0.18, w - 0.4, 0.8, value, size=30, bold=True, color=color, font=HEAD)
    text(slide, x + 0.2, y + 0.98, w - 0.4, h - 1.05, label, size=13, color=INK)


def notes(slide, minutes, body):
    slide.notes_slide.notes_text_frame.text = f"[{minutes} min] {body}"


def style_chart(chart, legend=True):
    chart.font.size = Pt(12)
    chart.font.name = BODY
    chart.font.color.rgb = MUTED
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = LINE
    va.format.line.fill.background()
    chart.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW


def build(ev, presets, torn, base_npv, tests, bench_entered, illus):
    m, res, inp = ev["result"]["metrics"], ev["result"], None
    sw_inp, meta = M.load_case()
    inp = sw_inp
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    illus_note = (f"Illustrative base case: {len(illus)} inputs are placeholders until our sample project's numbers are entered."
                  if illus else "Base case: the team's sample project.")

    # 1. title
    s = new_slide(prs, dark=True)
    text(s, 0.8, 2.0, 11.5, 1.4, "Should Rakesh buy this land?", size=48, bold=True, color=WHITE, font=HEAD)
    text(s, 0.8, 3.35, 11.5, 0.9, "A feasibility and appraisal tool for small and mid-size residential developers", size=22, color=WHITE)
    text(s, 0.8, 5.6, 11.5, 0.9, ["CE725 Construction Economics and Finance · Topic 2",
                                  "Ojas Somani · Shivam Shankar · Mrunal Pachpande"], size=15, color=WHITE)
    notes(s, 0.5, "Open with the user's question, not the tool. Introduce the team and roles.")

    # 2. user
    s = new_slide(prs)
    title(s, "We built it for one person and his question", "Composite persona from desk research; to be confirmed in interviews")
    card(s, 0.6, 2.0, 5.4, 4.8)
    text(s, 0.9, 2.2, 4.9, 4.4, [
        ("Rakesh", {"size": 26, "bold": True, "font": HEAD, "color": TEAL}),
        ("Runs a mid-size developer in Mumbai or Pune. Knows construction and his market. Not a finance modeller.", {"size": 16}),
        ("“Should I buy this land, and how much money do I need to survive until collections catch up?”",
         {"size": 18, "bold": True, "color": INK}),
        ("He has to defend the numbers to a lender or investor.", {"size": 16, "color": MUTED}),
    ])
    needs = ["A trustworthy go/no-go, fast", "Peak funding and when it hits", "What-ifs without rebuilding the model",
             "Numbers a lender accepts", "The most he can pay for the land", "A source for every input"]
    text(s, 6.6, 2.0, 6.0, 0.5, "What he needs, in order", size=18, bold=True, color=INK)
    for i, n in enumerate(needs):
        y = 2.65 + i * 0.7
        badge(s, 6.6, y, i + 1)
        text(s, 7.35, y + 0.05, 5.5, 0.5, n, size=17)
    notes(s, 1, "Explain why the tool leads with decisions, not metrics. He distrusts black boxes, invented data and rosy cases.")

    # 3. cash timing
    s = new_slide(prs)
    title(s, "His real risk is running out of cash, not profit")
    steps = [("Land, stamp duty and premiums", "paid up front, before a single flat is sold"),
             ("Buyers pay in stages", "booking, then with construction progress, then at possession"),
             (f"{inp['escrow_pct']:.0f}% goes to the RERA account", "drawn only for land and construction, in step with completion")]
    for i, (a, b) in enumerate(steps):
        x = 0.6 + i * 4.2
        card(s, x, 2.0, 3.7, 2.4)
        text(s, x + 0.25, 2.2, 3.2, 2.1, [(a, {"size": 19, "bold": True, "color": TEAL}), (b, {"size": 15})])
        if i < 2:
            arr = card(s, x + 3.78, 2.95, 0.35, 0.5, TEAL_MID, MSO_SHAPE.RIGHT_ARROW)
            arr.name = f"Arrow {i + 1}"
    stat(s, 0.6, 4.85, 5.6, cr(m["peak_funding"]), f"peak funding needed, in Q{m['peak_quarter']} "
         f"({cr(m['peak_equity'])} equity + {cr(m['peak_loan'])} loan)", color=BRICK, fill=BRICK_LIGHT, h=1.9)
    text(s, 6.6, 4.95, 6.1, 1.8, ["The tool models this quarter by quarter and leads with the funding gap.",
                                  (illus_note, {"size": 12, "color": MUTED})], size=17)
    notes(s, 1.25, "Walk through the cash timing. RERA Section 4(2)(l)(D) sends 70% of collections to a separate account. "
                   "Peak funding is the number a developer lives or dies by.")

    # 4. how it works
    s = new_slide(prs)
    title(s, "Eight steps from land price to verdict", "Each step is one small, tested function linked to a CE725 chapter")
    chain = [("Areas", "plot × FSI → saleable area"), ("Costs", "land, premiums, S-curve construction"),
             ("Sales", "pace and escalating price"), ("Collections", "booking, progress, possession"),
             ("RERA account", "70% in, drawn with completion"), ("Funding", "equity, then loan; repay from free cash"),
             ("Metrics", "NPV, IRR, peak funding (Ch 5, 7)"), ("Break-evens", "max land price, price (Ch 12)")]
    for i, (a, b) in enumerate(chain):
        x, y = 0.6 + (i % 4) * 3.1, 2.1 + (i // 4) * 2.3
        card(s, x, y, 2.85, 2.0)
        badge(s, x + 0.2, y + 0.2, i + 1, size=0.5)
        text(s, x + 0.2, y + 0.8, 2.5, 1.1, [(a, {"size": 18, "bold": True, "color": TEAL}), (b, {"size": 14})])
    text(s, 0.6, 6.75, 12, 0.45, "Then: verdict, plain-language warnings, what-ifs, lender ratios and a template memo.",
         size=14, color=MUTED)
    notes(s, 1.25, "Each member should be able to explain any step. Mention effective quarterly rates (Ch 2), MIRR when IRR is "
                   "not unique (Ch 8), escalation (Ch 9), tax (Ch 11).")

    # 5. demo plan
    s = new_slide(prs)
    title(s, "Live demo: five minutes, one land deal")
    demo = [("Enter the deal", "Inputs & sources: every value has a source and a flag"),
            ("Read the verdict", "Decision tab: Go / Marginal / No-go and why"),
            ("Find the funding gap", "Peak funding and the quarter it hits"),
            ("Add a 2-quarter delay", "Sidebar slider: NPV, funding and buyer interest move"),
            ("Show the lender view", "Loan-to-cost, debt service cover, receivables cover"),
            ("Ask the land question", "Maximum land price vs the asking price; download the memo")]
    for i, (a, b) in enumerate(demo):
        x, y = 0.6 + (i % 2) * 6.2, 1.8 + (i // 2) * 1.75
        card(s, x, y, 5.9, 1.5)
        badge(s, x + 0.25, y + 0.45, i + 1)
        text(s, x + 1.0, y + 0.2, 4.7, 1.2, [(a, {"size": 19, "bold": True, "color": TEAL}), (b, {"size": 15})])
    text(s, 0.6, 6.95, 12, 0.4, "On the website (/tool). Fallback: python3 serve_local.py on a laptop, plus screenshots.", size=13, color=MUTED)
    notes(s, 5, "Demo on the deployed website; keep the local copy and screenshots as fallbacks. Change one input live and narrate the "
                "so-what sentence, not the formula. End by printing the lender summary.")

    # 6. answer
    s = new_slide(prs)
    v = ev["verdict"]
    title(s, f"Base case verdict: {v}", illus_note)
    vals = [(cr(m["peak_funding"]), f"peak funding, Q{m['peak_quarter']}", BRICK, BRICK_LIGHT),
            (cr(m["project_npv"]), f"NPV at a {inp['hurdle_rate_pct']:.0f}% hurdle", BRICK if m["project_npv"] < 0 else TEAL,
             BRICK_LIGHT if m["project_npv"] < 0 else TEAL_LIGHT),
            (pct(m["project_irr"]), "project IRR (yearly return)", TEAL, TEAL_LIGHT),
            (cr(ev["breakeven_land"]) if ev["breakeven_land"] is not None else "n/a",
             f"maximum land price (assumed {cr(inp['land_price_cr'])})", TEAL, TEAL_LIGHT)]
    for i, (val, lab, col, fill) in enumerate(vals):
        stat(s, 0.6 + i * 3.1, 2.1, 2.85, val, lab, col, fill, h=2.0)
    text(s, 0.6, 4.5, 12.1, 2.4, [f"{'✓' if ok else '✗'}  {name}" for name, ok in ev["checks"]], size=17)
    notes(s, 0.5, "Read the checks behind the verdict. Stress that these are illustrative numbers until our project data is in.")

    # 7. cash chart
    s = new_slide(prs)
    title(s, f"Cash is tightest in Q{m['peak_quarter']}")
    cd = CategoryChartData()
    cd.categories = [f"Q{t}" for t in range(res["T"] + 1)]
    cum, total = [], 0.0
    for x in res["project_cf"]:
        total += x
        cum.append(round(total, 2))
    cd.add_series("Project cash, cumulative (₹ cr)", cum)
    cd.add_series("Outside money in the project (₹ cr)", [round(max(0.0, o), 2) for o in res["outstanding"]])
    ch = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.6), Inches(1.5), Inches(8.4), Inches(5.6), cd).chart
    style_chart(ch)
    for ser, col in zip(ch.series, (TEAL, BRICK)):
        ser.format.line.color.rgb = col
        ser.format.line.width = Pt(2.5)
        ser.smooth = False
    text(s, 9.3, 1.8, 3.5, 5, [(cr(m["peak_funding"]), {"size": 30, "bold": True, "color": BRICK, "font": HEAD}),
                               (f"of outside money at the peak, in Q{m['peak_quarter']}", {"size": 15}),
                               ("Payback " + ("n/a" if m["payback_years"] is None else f"{m['payback_years']:.1f} years"),
                                {"size": 18, "bold": True, "color": TEAL}),
                               ("Land is paid at Q0; collections follow construction.", {"size": 14, "color": MUTED})])
    notes(s, 0.75, "The gap between the two lines is what Rakesh must finance.")

    # 8. what-ifs
    s = new_slide(prs)
    title(s, "Sale price and construction cost move the answer most", "Project NPV with one input at −20% and +20% (delay: 0 vs +4 quarters)")
    cd = CategoryChartData()
    rows = torn[::-1]
    cd.categories = [r[0] for r in rows]
    cd.add_series("Input lower / no delay", [round(r[1], 2) for r in rows])
    cd.add_series("Input higher / 4 quarters late", [round(r[2], 2) for r in rows])
    ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.9), Inches(7.6), Inches(5.2), cd).chart
    style_chart(ch)
    for ser, col in zip(ch.series, (TEAL_MID, BRICK)):
        ser.invert_if_negative = False
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col
    tbl = s.shapes.add_table(4, 3, Inches(8.6), Inches(2.1), Inches(4.2), Inches(2.4)).table
    for j, hd in enumerate(["Case", "NPV", "Peak funding"]):
        tbl.cell(0, j).text = hd
    for i, (name, x) in enumerate(presets.items(), 1):
        for j, val in enumerate([name, cr(x["project_npv"]), cr(x["peak_funding"])]):
            tbl.cell(i, j).text = val
    for r in range(4):
        for c in range(3):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL if r == 0 else (TEAL_LIGHT if r % 2 else WHITE)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size, run.font.name = Pt(14), BODY
                    run.font.color.rgb = WHITE if r == 0 else INK
                    run.font.bold = r == 0
    text(s, 8.6, 4.75, 4.2, 2, ["Downside: price −10%, cost +10%, sales 25% slower, 2 quarters late. Upside: price +5%, cost −5%, sales 15% faster.",
                                ("Preset shocks are team assumptions, not forecasts.", {"color": MUTED, "size": 12})], size=13)
    notes(s, 1, "Read the tornado from the top. Lenders want resilience in the downside case, not just the base case.")

    # 9. lender view
    s = new_slide(prs)
    title(s, "What a lender sees", "Defined in plain words on screen; definitions to confirm with a lender")
    lend = [(cr(m["peak_loan_balance"]), "peak loan"), (pct(m["loan_to_cost"]), "loan-to-cost"),
            ("n/a" if m["dscr"] is None else f"{m['dscr']:.2f}x", "debt service cover over the repayment quarters"),
            ("n/a" if m["min_receivables_cover"] is None else f"{m['min_receivables_cover']:.1f}x",
             "lowest receivables cover (money due + unsold stock ÷ loan)")]
    for i, (val, lab) in enumerate(lend):
        stat(s, 0.6 + i * 3.1, 2.1, 2.85, val, lab, h=2.1)
    text(s, 0.6, 4.7, 12, 2, ["The loan is repaid only from free cash, never from the RERA account.",
                              "Equity funds the early gap first; the loan fills the rest up to its sanctioned limit.",
                              ("Next step: ask a construction-finance officer whether they would accept these ratios.",
                               {"color": MUTED})], size=17)
    notes(s, 0.75, "Explain each ratio in one sentence. Be honest that the debt service cover definition is ours.")

    # 10. validation
    s = new_slide(prs)
    title(s, "How we know the numbers are right")
    passed = sum(st == "PASS" for *_, st in tests)
    layers = [(f"{passed}/{len(tests)}", "automated checks pass", "Cash balances every quarter, NPV = 0 at IRR, course problems PS2 #15 and #17"),
              (f"{sum(r[6] == 'match' for r in bench_entered)}/{len(bench_entered)}" if bench_entered else "Pending",
               "outputs match the Excel benchmark", "Built by hand without AI and without reading the code; ±0.1% tolerance"),
              ("Toy case", "worked on paper", "3–4 quarters to confirm timing and sign conventions")]
    for i, (val, lab, det) in enumerate(layers):
        x = 0.6 + i * 4.15
        card(s, x, 1.9, 3.85, 3.6)
        text(s, x + 0.25, 2.1, 3.4, 3.3, [(val, {"size": 34, "bold": True, "color": TEAL, "font": HEAD}),
                                          (lab, {"size": 17, "bold": True}), (det, {"size": 14, "color": MUTED})])
    text(s, 0.6, 5.75, 12, 1.4, "Found by re-checking, not by the code failing: a relayed escalation rate (6.9% → 7.7%), the downside "
                                "case applied twice when the Downside preset was on, fractional quarters silently cut, and a loan rate "
                                "treated as effective instead of nominal-monthly. All fixed, with a regression check for each.", size=15)
    notes(s, 1.25, "Validation is 20% of the marks. Show the discrepancy table from the validation report.")

    # 11. AI
    s = new_slide(prs)
    title(s, "What AI did well, and where it was wrong")
    card(s, 0.6, 1.8, 5.9, 3.6)
    text(s, 0.9, 2.0, 5.4, 3.3, [("Accelerated", {"size": 20, "bold": True, "color": TEAL}),
                                 "Structured the model into testable steps", "Wrote the app, charts and checks",
                                 "Found and summarised market reports", "Drafted documents from live results"], size=16)
    card(s, 6.8, 1.8, 5.9, 3.6, BRICK_LIGHT)
    text(s, 7.1, 2.0, 5.4, 3.3, [("Needed checking", {"size": 20, "bold": True, "color": BRICK}),
                                 "Relayed a wrong escalation rate from a summary", "Mixed conflicting sources on ready reckoner rates",
                                 "Applied the downside shock twice: ran without errors", "Silently cut fractional quarters",
                                 "No current loan rate found: left as an assumption, not invented"],
         size=16)
    notes(s, 1, "Use specific examples from the AI usage log. Every number was verified before use.")

    # 12. limits
    s = new_slide(prs)
    title(s, "Limits and next steps")
    card(s, 0.6, 1.8, 5.9, 3.6)
    text(s, 0.9, 2.0, 5.4, 3.3, [("Limits", {"size": 20, "bold": True, "color": TEAL}), "One project, one phase",
                                 "No joint-development or revenue-share deals", "Simplified tax timing",
                                 "RERA account released at possession", "Verdict thresholds not yet validated"], size=16)
    card(s, 6.8, 1.8, 5.9, 3.6)
    text(s, 7.1, 2.0, 5.4, 3.3, [("Next", {"size": 20, "bold": True, "color": TEAL}), "Interview a developer and a lender",
                                 "Replace placeholders with project data", "Add phasing and JV structures",
                                 "Export in a lender's template", "Host it so a developer can try it"], size=16)
    notes(s, 0.5, "Be upfront about limits; it builds trust.")

    # 13. close
    s = new_slide(prs, dark=True)
    bl = ev["breakeven_land"]
    answer = (f"At {cr(inp['land_price_cr'])} the land {'meets' if m['project_npv'] >= 0 else 'fails'} a "
              f"{inp['hurdle_rate_pct']:.0f}% hurdle. The most to pay is {cr(bl) if bl is not None else 'n/a'}, and "
              f"{cr(m['peak_funding'])} of funding must be in place by Q{m['peak_quarter']}.")
    text(s, 0.8, 1.6, 11.7, 1, "The answer for Rakesh", size=40, bold=True, color=WHITE, font=HEAD)
    text(s, 0.8, 2.9, 11.7, 2, answer, size=24, color=WHITE)
    text(s, 0.8, 5.5, 11.7, 0.8, "Questions", size=28, bold=True, color=WHITE, font=HEAD)
    text(s, 0.8, 6.3, 11.7, 0.6, illus_note, size=13, color=WHITE)
    notes(s, 0.25, "Restate the answer in one breath, then take questions. Any member may be asked about any formula.")

    prs.save(HERE / "Presentation.pptx")

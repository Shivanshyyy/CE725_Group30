"""15-minute presentation built from live model results (CE725 Group 30). Called by make_docs.py.

Design matches the website: ink title/closing slides, drafting-paper content slides, teal = go, brick = money at risk.
Every chart is a native PowerPoint chart built from the model, so it updates when the inputs change.
"""
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.dml import MSO_PATTERN
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

import model as M

HERE = Path(__file__).parent
rgb = RGBColor.from_string
PAPER, INK, MUTED, LINE, WHITE = rgb("F2F4F1"), rgb("14211D"), rgb("53625C"), rgb("CBD4D0"), rgb("FFFFFF")
TEAL, TEAL_SOFT, TEAL_MID = rgb("0B6B5C"), rgb("D9ECE6"), rgb("6FA89B")
BRICK, BRICK_SOFT, BRICK_LIGHT = rgb("A3461F"), rgb("F5E1D6"), rgb("E08A60")
AMBER, GREY = rgb("94660A"), rgb("8A9792")
HEAD, BODY = "Arial Narrow", "Calibri"
W, H = 13.333, 7.5
GROUP = "Group 30"
TEAM = "Ojas Somani · Shivam Shankar · Mrunal Pachpande"
cr, pct = M.cr, M.pct


# ---------- drawing helpers ----------

def text(slide, x, y, w, h, content, size=16, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None, margin=0.0):
    """content: a string, or a list of paragraphs; a paragraph is a string or (string, options)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    for i, item in enumerate(content if isinstance(content, list) else [content]):
        txt, opt = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = opt.get("align", align)
        p.space_after = Pt(opt.get("space", 6))
        r = p.add_run()
        r.text = txt
        f = r.font
        f.size, f.bold, f.name = Pt(opt.get("size", size)), opt.get("bold", bold), opt.get("font", font)
        f.color.rgb = opt.get("color", color)
    return tb


def rect(slide, x, y, w, h, fill=WHITE, line=None, shape=MSO_SHAPE.RECTANGLE, name=None, width=1.0):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(width)
    s.shadow.inherit = False
    style = s._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:  # drop the theme style so no viewer adds a shadow or outline
        s._element.remove(style)
    if name:
        s.name = name
    return s


def hline(slide, x, y, w, color=INK, width=1.5):
    """A hairline rule drawn as a thin filled shape (connectors pick up theme shadows in some viewers)."""
    return rect(slide, x, y - width / 144, w, width / 72, color, name="Rule")


def level_mark(slide, x, y, color=INK, size=0.26):
    """Survey level mark (▽ on a short line): the deck's motif for 'this is the number that matters'."""
    tri = rect(slide, x, y, size, size * 0.8, color, shape=MSO_SHAPE.ISOSCELES_TRIANGLE, name="Level mark")
    tri.rotation = 180
    hline(slide, x - size * 0.6, y, size * 2.2, color, 1.75)


def new_slide(prs, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = INK if dark else PAPER
    return s


def title(slide, t, sub=None):
    text(slide, 0.6, 0.42, W - 1.2, 0.85, t, size=38, bold=True, font=HEAD, name="Title")
    if sub:
        text(slide, 0.6, 1.22, W - 1.2, 0.45, sub, size=15, color=MUTED)


def stat(slide, x, y, w, value, label, color=INK, size=46, mark=False):
    """A big number with a plain label under it."""
    if mark:
        level_mark(slide, x + 0.15, y - 0.12, color)
    text(slide, x, y + (0.12 if mark else 0), w, 0.9, value, size=size, bold=True, color=color, font=HEAD)
    text(slide, x, y + (0.12 if mark else 0) + size / 72 + 0.12, w, 1.0, label, size=15, color=MUTED)


def notes(slide, minutes, body):
    slide.notes_slide.notes_text_frame.text = f"[{minutes} min] {body}"


def title_block(slide, x, y, w, dark=True):
    """Drawing title block with the group number, as on the website footer."""
    rows = [("Project", "Real estate feasibility and appraisal tool"), ("Course", "CE725 Construction Economics and Finance, IIT Bombay"),
            ("Team", TEAM), ("Group", "30")]
    fg = WHITE if dark else INK
    tbl = slide.shapes.add_table(len(rows), 2, Inches(x), Inches(y), Inches(w), Inches(0.36 * len(rows) + 0.2)).table
    tbl.columns[0].width, tbl.columns[1].width = Inches(1.0), Inches(w - 1.0)
    tbl.first_row = False
    for i, (k, v) in enumerate(rows):
        for j, val in enumerate((k, v)):
            cell = tbl.cell(i, j)
            cell.fill.background()
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = val
            big = k == "Group" and j == 1
            r.font.size = Pt(30 if big else (12 if j == 0 else 14))
            r.font.bold = big or j == 1
            r.font.name = HEAD if big else BODY
            r.font.color.rgb = (TEAL_MID if dark else TEAL) if big else (fg if j == 1 else (LINE if dark else MUTED))
            _cell_borders(cell, "FFFFFF" if dark else "14211D")


def _cell_borders(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.SubElement(tcPr, f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag.split(':')[1]}", w="12700")
        fill = etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
        etree.SubElement(fill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr", val=hexcolor)


def cash_profile(slide, outstanding, x, y, w, depth, dark=True, label=None):
    """Outside money drawn as a ground section: ₹0 is the datum, the hole is hatched (same picture as the website hero)."""
    n = len(outstanding) - 1
    k = depth / max(max(outstanding), 1e-9)
    px = lambda t: Inches(x + w * t / n)
    py = lambda v: Inches(y + max(0.0, v) * k)
    fb = slide.shapes.build_freeform(px(0), py(0))
    fb.add_line_segments([(px(t), py(v)) for t, v in enumerate(outstanding)] + [(px(n), py(0))], close=True)
    shp = fb.convert_to_shape()
    shp.name = "Cash section"
    shp.fill.patterned()
    shp.fill.pattern = MSO_PATTERN.WIDE_UPWARD_DIAGONAL
    shp.fill.fore_color.rgb = BRICK if dark else BRICK_LIGHT
    shp.fill.back_color.rgb = INK if dark else PAPER
    shp.line.color.rgb = BRICK_LIGHT if dark else BRICK
    shp.line.width = Pt(2.5)
    hline(slide, x - 0.2, y, w + 0.4, WHITE if dark else INK, 2)
    text(slide, x + w - 3.0, y - 0.42, 3.2, 0.35, "±0 · your own pocket", size=14, bold=True,
         color=WHITE if dark else INK, align=PP_ALIGN.RIGHT)
    tp = max(range(n + 1), key=lambda t: outstanding[t])
    cx, cy = x + w * tp / n, y + outstanding[tp] * k
    level_mark(slide, cx - 0.13, cy + 0.02, WHITE if dark else INK, 0.24)
    if label:
        text(slide, cx - 2.2, cy + 0.12, 4.4, 0.5, label, size=20, bold=True, font=HEAD,
             color=BRICK_LIGHT if dark else BRICK, align=PP_ALIGN.CENTER)


# ---------- chart helpers ----------

def style_chart(chart, legend=True, datum=False):
    chart.has_title = False
    chart.font.size = Pt(13)
    chart.font.name = BODY
    chart.font.color.rgb = MUTED
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(13)
    try:
        va = chart.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = LINE
        va.format.line.fill.background()
        ca = chart.category_axis
        ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
        ca.has_major_gridlines = False
        ca.format.line.color.rgb = INK if datum else LINE  # the ₹0 line is the datum
        ca.format.line.width = Pt(1.75 if datum else 0.75)
    except (ValueError, AttributeError):
        pass  # doughnut charts have no axes


def fill_series(series, color):
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = color
    series.invert_if_negative = False


def set_gap(chart, gap=60, overlap=None):
    plot = chart.plots[0]
    plot.gap_width = gap
    if overlap is not None:
        plot.overlap = overlap


def labels(series_or_plot, fmt='#,##0.0', size=13, color=INK, pos=None):
    dl = series_or_plot.data_labels
    dl.show_value = True
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.font.size = Pt(size)
    dl.font.color.rgb = color
    dl.font.bold = True
    if pos is not None:
        dl.position = pos


def quarters(n):
    return [f"Q{t}" for t in range(n)]


# ---------- the deck ----------

def build(ev, presets, torn, base_npv, tests, bench_entered, illus):
    res, m = ev["result"], ev["result"]["metrics"]
    inp, meta = M.load_case()
    T = res["T"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    illus_note = (f"Illustrative base case: {len(illus)} inputs are placeholders until our sample project's numbers are entered."
                  if illus else "Base case: the team's sample project.")
    outstanding = [max(0.0, o) for o in res["outstanding"]]
    tp = m["peak_quarter"]
    bl = ev["breakeven_land"]

    # 1. title -----------------------------------------------------------
    s = new_slide(prs, dark=True)
    text(s, 0.6, 0.5, 12.1, 1.0, "Should Rakesh buy this land?", size=54, bold=True, color=WHITE, font=HEAD, name="Title")
    text(s, 0.6, 1.5, 12.1, 0.6, "A feasibility and appraisal tool for small and mid-size residential developers in India",
         size=20, color=LINE)
    cash_profile(s, outstanding, 0.8, 3.15, 7.6, 2.75, dark=True,
                 label=f"Peak funding −{cr(m['peak_funding'])[1:]} · Q{tp}")
    title_block(s, 8.95, 4.95, 3.85, dark=True)
    text(s, 8.95, 4.45, 3.85, 0.4, "CE725 · Topic 2 · Nov 2026", size=14, color=LINE)
    notes(s, 0.5, "Open with the user's question, not the tool. The drawing is the funding hole of the example project: "
                  "how deep it goes and when the developer climbs out. Introduce Group 30 and each member's role.")

    # 2. user ------------------------------------------------------------
    s = new_slide(prs)
    title(s, "We built it for one person and his question", "Composite persona from desk research; to be confirmed in interviews")
    text(s, 0.6, 1.9, 5.9, 2.4, "“Should I buy this land, and how much money do I need to survive until collections catch up?”",
         size=28, bold=True, font=HEAD)
    text(s, 0.6, 4.45, 5.7, 2.2, [("Rakesh runs a mid-size developer in Mumbai or Pune.", {"bold": True}),
                                  "He knows construction and his market but is not a finance modeller, and he has to defend "
                                  "the numbers to a lender or investor."], size=17)
    text(s, 7.2, 1.9, 5.5, 0.5, "What he needs, most important first", size=18, bold=True)
    needs = ["A trustworthy go/no-go, fast", "Peak funding and when it hits", "What-ifs without rebuilding the model",
             "Numbers a lender accepts", "The most he can pay for the land", "A source for every input"]
    for i, n in enumerate(needs):
        y = 2.5 + i * 0.68
        hline(s, 7.2, y, 5.5, LINE, 1)
        text(s, 7.2, y + 0.1, 0.6, 0.5, str(i + 1), size=24, bold=True, color=TEAL, font=HEAD)
        text(s, 7.8, y + 0.15, 4.9, 0.5, n, size=18)
    hline(s, 7.2, 2.5 + 6 * 0.68, 5.5, LINE, 1)
    notes(s, 1, "Explain why the tool leads with decisions, not metrics. He distrusts black boxes, invented data and rosy cases.")

    # 3. cash timing chart -----------------------------------------------
    first_in = next((t for t, c in enumerate(res["collections"]) if c > 1e-6), T)
    before = sum(res["total_costs"][:first_in])
    s = new_slide(prs)
    title(s, "His real risk is running out of cash, not profit", "Money paid out and collected from buyers each quarter, ₹ crore")
    cd = CategoryChartData()
    cd.categories = quarters(T + 1)
    cd.add_series("Paid out (all costs)", [round(x, 2) for x in res["total_costs"]])
    cd.add_series("Collected from buyers", [round(x, 2) for x in res["collections"]])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.8), Inches(8.3), Inches(5.0), cd).chart
    style_chart(ch, datum=True)
    set_gap(ch, 50, -5)
    fill_series(ch.series[0], BRICK)
    fill_series(ch.series[1], TEAL)
    stat(s, 9.3, 2.05, 3.5, cr(before), f"goes out in Q0–Q{first_in - 1} before buyers pay anything: land, stamp duty, "
                                         "approvals and premiums", color=BRICK, mark=True)
    text(s, 9.3, 4.55, 3.5, 2.2, [(f"Then {inp['escrow_pct']:.0f}% of every rupee collected is locked in the RERA account",
                                   {"bold": True}),
                                  ("released only as construction is completed, so profit on paper is not cash in hand.",
                                   {"color": MUTED})], size=16)
    notes(s, 1.25, "Point at the brick bars in the first quarters: that is land and premiums, paid before a single flat is sold. "
                   "RERA Section 4(2)(l)(D) sends 70% of collections to a separate account. Peak funding is the number a "
                   "developer lives or dies by.")

    # 4. how it works ----------------------------------------------------
    s = new_slide(prs)
    title(s, "Eight steps from land price to verdict", "Each step is one small, tested function linked to a CE725 chapter")
    chain = [("Areas", "Plot × FSI gives built-up area; a ratio gives saleable area"),
             ("Costs", "Land and premiums up front; construction on an S-curve, escalating (Ch 9)"),
             ("Sales", "A share of the area sells each quarter at a rising price"),
             ("Collections", "Booking, then with construction progress, then at possession"),
             ("RERA account", f"{inp['escrow_pct']:.0f}% of collections in, drawn in step with completion"),
             ("Funding", "Equity first, then the loan; repaid from free cash only"),
             ("Results", "NPV, IRR, payback, profit on cost, peak funding (Ch 1, 5, 7)"),
             ("Break-evens", "Maximum land price and break-even sale price (Ch 12)")]
    for i, (a, b) in enumerate(chain):
        x, y = 0.6 + (i % 4) * 3.1, 2.0 + (i // 4) * 2.45
        hline(s, x, y, 2.85, INK, 2)
        rect(s, x, y - 0.1, 0.03, 0.2, INK, name="Tick")
        text(s, x, y + 0.12, 2.85, 0.4, f"Step {i + 1}", size=14, bold=True, color=TEAL)
        text(s, x, y + 0.5, 2.85, 0.5, a, size=22, bold=True, font=HEAD)
        text(s, x, y + 1.0, 2.75, 1.2, b, size=15, color=MUTED)
    notes(s, 1.25, "Each member should be able to explain any step. Mention effective quarterly rates (Ch 2), MIRR when IRR is "
                   "not unique (Ch 8), escalation (Ch 9), tax (Ch 11).")

    # 5. verdict ---------------------------------------------------------
    v = ev["verdict"]
    vcol = {"Go": TEAL, "Marginal": AMBER, "No-go": BRICK}[v]
    s = new_slide(prs)
    title(s, f"Base case verdict: {v}", illus_note)
    outer = rect(s, 0.75, 2.05, 3.4, 1.55, None, vcol, width=3.5, name="Stamp")
    inner = rect(s, 0.85, 2.15, 3.2, 1.35, None, vcol, width=1.0, name="Stamp inner")
    outer.rotation = inner.rotation = -3
    passed = sum(ok for _, ok in ev["checks"])
    st = text(s, 0.75, 2.12, 3.4, 1.4, [(v.upper(), {"size": 58, "bold": True, "font": HEAD, "color": vcol, "align": PP_ALIGN.CENTER, "space": 0}),
                                        (f"{passed} of {len(ev['checks'])} checks passed", {"size": 14, "bold": True, "color": vcol, "align": PP_ALIGN.CENTER})])
    st.rotation = -3
    for i, (name, ok) in enumerate(ev["checks"]):
        y = 4.15 + i * 0.6
        text(s, 0.75, y, 0.45, 0.45, "✓" if ok else "✗", size=22, bold=True, color=TEAL if ok else BRICK)
        text(s, 1.25, y + 0.04, 4.6, 0.5, name, size=17)
    vals = [(cr(m["peak_funding"]), f"peak funding, needed by Q{tp}", BRICK),
            (cr(m["project_npv"]), f"NPV at a {inp['hurdle_rate_pct']:.0f}% hurdle", BRICK if m["project_npv"] < 0 else TEAL),
            (cr(bl) if bl is not None else "n/a", f"maximum land price (assumed {cr(inp['land_price_cr'])})", TEAL),
            (pct(m["project_irr"]), f"project IRR against a {inp['hurdle_rate_pct']:.0f}% hurdle", INK)]
    for i, (val, lab, col) in enumerate(vals):
        stat(s, 6.6 + (i % 2) * 3.2, 2.0 + (i // 2) * 2.35, 3.0, val, lab, col, size=44)
    notes(s, 0.75, "Read the checks behind the verdict. Stress that these are illustrative numbers until our project data is in.")

    # 6. where the money goes (doughnut) ---------------------------------
    c = res["costs"]
    groups = [("Construction", sum(c["construction"]), TEAL),
              ("Land + stamp duty", sum(c["land"]) + sum(c["stamp_duty"]), BRICK),
              ("Premiums + approvals", sum(c["premiums"]) + sum(c["approvals"]), BRICK_LIGHT),
              ("Soft costs + contingency", sum(c["soft_costs"]) + sum(c["contingency"]), TEAL_MID),
              ("Marketing", sum(c["marketing"]), GREY),
              ("Loan interest + delay interest", m["finance_cost"] + sum(c["buyer_delay_interest"]), AMBER)]
    total = sum(g[1] for g in groups)
    upfront = groups[1][1] + groups[2][1]
    s = new_slide(prs)
    title(s, "Where the money goes", f"Total cost {cr(total)}, including loan interest")
    cd = CategoryChartData()
    cd.categories = [g[0] for g in groups]
    cd.add_series("Cost", [round(g[1], 2) for g in groups])
    gf = s.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.5), Inches(1.75), Inches(5.2), Inches(5.0), cd)
    ch = gf.chart
    style_chart(ch, legend=False)
    hole = ch.plots[0]._element.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}holeSize")
    if hole is not None:
        hole.set("val", "58")
    for i, g in enumerate(groups):
        pt = ch.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = g[2]
        pt.format.line.color.rgb = PAPER
        pt.format.line.width = Pt(2)
    text(s, 1.6, 3.72, 3.0, 1.0, [(cr(total), {"size": 30, "bold": True, "font": HEAD, "align": PP_ALIGN.CENTER, "space": 0}),
                                  ("total cost", {"size": 14, "color": MUTED, "align": PP_ALIGN.CENTER})])
    for i, (name, val, col) in enumerate(groups):
        y = 1.95 + i * 0.56
        rect(s, 6.2, y + 0.1, 0.24, 0.24, col, name="Key")
        text(s, 6.6, y + 0.02, 3.6, 0.45, name, size=17)
        text(s, 10.0, y + 0.02, 1.4, 0.45, f"{val:,.2f}", size=17, bold=True, align=PP_ALIGN.RIGHT)
        text(s, 11.5, y + 0.02, 1.0, 0.45, f"{100 * val / total:.0f}%", size=17, color=MUTED, align=PP_ALIGN.RIGHT)
    text(s, 10.0, 1.55, 2.5, 0.35, "₹ crore    share", size=13, color=MUTED, align=PP_ALIGN.RIGHT)
    hline(s, 6.2, 5.45, 6.3, LINE, 1)
    stat(s, 6.2, 5.6, 6.3, f"{100 * upfront / total:.0f}% up front",
         "Land, stamp duty, premiums and approvals are paid before construction starts", BRICK, size=30)
    notes(s, 1, "Construction is the biggest line, but the brick slices are paid first, with no sales yet. In Mumbai, premiums "
                "can be far larger than here, which is why they are their own input.")

    # 7. cash curve ------------------------------------------------------
    s = new_slide(prs)
    title(s, f"Cash is tightest in Q{tp}", "Cumulative project cash and outside money in the project, ₹ crore")
    cum, run = [], 0.0
    for x in res["project_cf"]:
        run += x
        cum.append(round(run, 2))
    cd = CategoryChartData()
    cd.categories = quarters(T + 1)
    cd.add_series("Project cash, cumulative (after tax, before loan)", cum)
    cd.add_series("Outside money in the project (shown below zero)", [round(-o, 2) for o in outstanding])
    ch = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.5), Inches(1.8), Inches(8.6), Inches(5.0), cd).chart
    style_chart(ch, datum=True)
    for ser, col in zip(ch.series, (TEAL, BRICK)):
        ser.format.line.color.rgb = col
        ser.format.line.width = Pt(3)
        ser.smooth = False
        ser.marker.style = None
        from pptx.enum.chart import XL_MARKER_STYLE
        ser.marker.style = XL_MARKER_STYLE.NONE
    stat(s, 9.5, 2.05, 3.3, cr(m["peak_funding"]), f"outside money at the peak, Q{tp}: "
                                                   f"{cr(m['peak_equity'])} equity + {cr(m['peak_loan'])} loan", BRICK, mark=True)
    pb = "n/a" if m["payback_years"] is None else f"{m['payback_years']:.1f} years"
    stat(s, 9.5, 4.65, 3.3, pb, "payback: when cumulative project cash turns positive", TEAL, size=40)
    notes(s, 0.75, "The brick line is what Rakesh must finance; it bottoms out at the peak funding quarter. The teal line "
                   "crossing zero is payback.")

    # 8. funding + lender view -------------------------------------------
    s = new_slide(prs)
    title(s, "How the gap is funded, and what a lender sees", "Equity and loan in the project each quarter, ₹ crore")
    cd = CategoryChartData()
    cd.categories = quarters(T + 1)
    loan = res["loan_balance"]
    cd.add_series("Equity in the project", [round(max(0.0, o - l), 2) for o, l in zip(res["outstanding"], loan)])
    cd.add_series("Construction loan", [round(l, 2) for l in loan])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(0.5), Inches(1.8), Inches(7.6), Inches(5.0), cd).chart
    style_chart(ch, datum=True)
    set_gap(ch, 40, 100)
    fill_series(ch.series[0], TEAL)
    fill_series(ch.series[1], GREY)
    lend = [(cr(m["peak_loan_balance"]), "peak loan"), (pct(m["loan_to_cost"]), "loan-to-cost"),
            ("n/a" if m["dscr"] is None else f"{m['dscr']:.2f}x", "debt service cover, repayment quarters"),
            ("n/a" if m["min_receivables_cover"] is None else f"{m['min_receivables_cover']:.1f}x", "lowest receivables cover")]
    for i, (val, lab) in enumerate(lend):
        stat(s, 8.6 + (i % 2) * 2.2, 1.95 + (i // 2) * 1.85, 2.1, val, lab, INK, size=34)
    text(s, 8.6, 5.75, 4.2, 1.1, "Equity funds the early gap first. The loan is repaid only from free cash, never from the RERA account.",
         size=15, color=MUTED)
    notes(s, 1, "Equity goes in first, the loan tops up. Explain each ratio in one sentence; be honest that the debt service "
                "cover definition is ours and needs a lender's confirmation.")

    # 9. tornado ---------------------------------------------------------
    s = new_slide(prs)
    rows = torn[::-1]  # bar charts draw the first category at the bottom: biggest swing goes on top
    title(s, f"{torn[0][0].split(' ±')[0]} and {torn[1][0].split(' ±')[0].lower()} move the answer most",
          f"Change in project NPV from the base case ({cr(base_npv)}), one input at a time: ±20%, delay 0 to +4 quarters")
    cd = CategoryChartData()
    cd.categories = [r[0] for r in rows]
    cd.add_series("Worse side", [round(min(lo, hi) - base_npv, 2) for _, lo, hi in rows])
    cd.add_series("Better side", [round(max(lo, hi) - base_npv, 2) for _, lo, hi in rows])
    ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.5), Inches(1.85), Inches(8.6), Inches(5.0), cd).chart
    style_chart(ch, datum=True)
    set_gap(ch, 45, 100)
    fill_series(ch.series[0], BRICK)
    fill_series(ch.series[1], TEAL)
    for ser in ch.series:
        labels(ser, '+#,##0.0;−#,##0.0;""', 13, INK, XL_LABEL_POSITION.OUTSIDE_END)
    ch.value_axis.tick_labels.number_format = '+#,##0;−#,##0;0'
    ch.value_axis.tick_labels.number_format_is_linked = False
    top = torn[0]
    text(s, 9.5, 2.1, 3.3, 4.5, [(f"₹{abs(top[2] - top[1]):,.1f} cr", {"size": 44, "bold": True, "font": HEAD, "color": BRICK, "space": 2}),
                                 (f"NPV swing from {top[0].lower()}", {"size": 15, "color": MUTED, "space": 18}),
                                 ("Read from the top: the longest bars are the inputs to pin down first with real quotes and "
                                  "market data.", {"size": 16})])
    notes(s, 1, "Read the tornado from the top. Lenders want resilience in the downside case, not just the base case.")

    # 10. three cases ----------------------------------------------------
    s = new_slide(prs)
    title(s, "Base, downside and upside side by side", "Downside: price −10%, cost +10%, sales 25% slower, 2 quarters late. "
                                                        "Upside: price +5%, cost −5%, sales 15% faster")
    names = list(presets)
    for j, (key, label, fmt) in enumerate([("project_npv", "Project NPV, ₹ crore", '#,##0.0;−#,##0.0'),
                                           ("peak_funding", "Peak funding, ₹ crore", '#,##0.0')]):
        cd = CategoryChartData()
        cd.categories = names
        cd.add_series(label, [round(presets[n][key], 2) for n in names])
        x = 0.5 + j * 6.3
        text(s, x + 0.1, 1.9, 5.8, 0.45, label, size=18, bold=True)
        ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(2.35), Inches(6.0), Inches(3.9), cd).chart
        style_chart(ch, legend=False, datum=True)
        set_gap(ch, 70)
        ser = ch.series[0]
        fill_series(ser, INK)
        for i, n in enumerate(names):
            val = presets[n][key]
            col = (BRICK if val < 0 else TEAL) if key == "project_npv" else (BRICK if n == "Downside" else GREY)
            pt = ser.points[i]
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = col
        labels(ser, fmt, 15, INK, XL_LABEL_POSITION.OUTSIDE_END)
        ch.value_axis.has_major_gridlines = False
        ch.value_axis.tick_labels.font.color.rgb = PAPER  # values are labelled on the bars
    text(s, 0.6, 6.35, 12.1, 0.5, "Preset shocks are team assumptions, not forecasts. A lender reads the downside column first.",
         size=15, color=MUTED)
    notes(s, 0.75, "Even the upside case is below the hurdle with these placeholder inputs; the downside needs much more funding, later.")

    # 11. validation -----------------------------------------------------
    s = new_slide(prs)
    title(s, "How we know the numbers are right", "Validation is checked three ways, and every bug found got a regression check")
    passed_t = sum(st == "PASS" for *_, st in tests)
    layers = [(f"{passed_t}/{len(tests)}", "automated checks pass",
               "Cash balances every quarter, NPV = 0 at IRR, 300 random scenarios, course problems PS2 #15 and #17", TEAL),
              (f"{sum(r[6] == 'match' for r in bench_entered)}/{len(bench_entered)}" if bench_entered else "Pending",
               "outputs match the Excel benchmark", "Built by hand without AI and without reading the code; ±0.1% tolerance", AMBER),
              ("Q0–Q3", "toy case on paper", "A few quarters by hand to confirm timing and sign conventions", INK)]
    for i, (val, lab, det, col) in enumerate(layers):
        x = 0.6 + i * 4.15
        hline(s, x, 1.95, 3.85, INK, 2)
        text(s, x, 2.1, 3.85, 0.95, val, size=50, bold=True, color=col, font=HEAD)
        text(s, x, 3.1, 3.85, 0.45, lab, size=18, bold=True)
        text(s, x, 3.6, 3.7, 1.2, det, size=15, color=MUTED)
    rect(s, 0.6, 5.1, 12.1, 1.3, WHITE, LINE, name="Found and fixed")
    text(s, 0.85, 5.22, 11.6, 1.1, [("Found by re-checking, not by the code failing", {"bold": True, "size": 16}),
                                    ("Relayed escalation rate (6.9% → 7.7%) · downside shocked twice · fractional quarters cut silently · "
                                     "loan rate convention · maximum land price wrongly reported as none for very profitable deals. "
                                     "All fixed, each with a regression check.", {"size": 15, "color": MUTED})])
    notes(s, 1.25, "Validation is 20% of the marks. Show the discrepancy table from the validation report.")

    # 12. demo -----------------------------------------------------------
    s = new_slide(prs)
    title(s, "Live demo: five minutes, one land deal", "On the website (/tool). Fallback: python3 serve_local.py on a laptop, plus screenshots")
    demo = [("Enter the deal", "Inputs & sources: every value has a source and a flag"),
            ("Read the verdict", "Decision tab: Go / Marginal / No-go and the checks behind it"),
            ("Find the funding gap", "Peak funding, the quarter it hits, and where the money goes"),
            ("Add a 2-quarter delay", "What-if slider: NPV, funding and buyer interest move"),
            ("Show the lender view", "Loan-to-cost, debt service cover, receivables cover"),
            ("Ask the land question", "Maximum land price vs the asking price; print the lender summary")]
    for i, (a, b) in enumerate(demo):
        x, y = 0.6 + (i % 2) * 6.25, 1.95 + (i // 2) * 1.6
        hline(s, x, y, 5.85, LINE, 1)
        text(s, x, y + 0.15, 0.7, 0.8, str(i + 1), size=40, bold=True, color=TEAL, font=HEAD)
        text(s, x + 0.8, y + 0.2, 5.0, 1.3, [(a, {"size": 20, "bold": True, "space": 2}), (b, {"size": 15, "color": MUTED})])
    notes(s, 5, "Demo on the deployed website; keep the local copy and screenshots as fallbacks. Change one input live and narrate "
                "the so-what sentence, not the formula. End by printing the lender summary.")

    # 13. AI -------------------------------------------------------------
    s = new_slide(prs)
    title(s, "What AI did well, and where it was wrong", "Every AI output was checked before use; details in the AI usage log")
    cols = [("✓", "Accelerated", TEAL, ["Structured the model into small, testable steps", "Wrote the app, website, charts and checks",
                                        "Found and summarised market reports", "Drafted documents from live results"]),
            ("✗", "Needed checking", BRICK, ["Relayed a wrong escalation rate from a summary", "Mixed conflicting ready reckoner sources",
                                             "Applied the downside shock twice, with no error shown", "Silently cut fractional quarters",
                                             "Said 'no land price works' for a very good deal"])]
    for i, (glyph, head, col, items) in enumerate(cols):
        x = 0.6 + i * 6.25
        text(s, x, 1.9, 0.8, 0.9, glyph, size=48, bold=True, color=col)
        text(s, x + 0.85, 2.05, 5.0, 0.6, head, size=26, bold=True, color=col, font=HEAD)
        for k, it in enumerate(items):
            y = 2.95 + k * 0.7
            hline(s, x, y, 5.85, LINE, 1)
            text(s, x, y + 0.12, 5.85, 0.55, it, size=17)
    notes(s, 1, "Use specific examples from the AI usage log. Every number was verified before use.")

    # 14. limits ---------------------------------------------------------
    s = new_slide(prs)
    title(s, "Limits and next steps")
    cols = [("Limits", INK, ["One project, one phase", "No joint-development or revenue-share deals", "Simplified tax timing",
                             "RERA account released at possession", "Verdict thresholds not yet validated"]),
            ("Next", TEAL, ["Interview a developer and a lender", "Replace placeholders with project data", "Add phasing and JV structures",
                            "Export in a lender's template", "Host it so a developer can try it"])]
    for i, (head, col, items) in enumerate(cols):
        x = 0.6 + i * 6.25
        text(s, x, 1.65, 5.85, 0.6, head, size=26, bold=True, color=col, font=HEAD)
        for k, it in enumerate(items):
            y = 2.45 + k * 0.8
            hline(s, x, y, 5.85, LINE, 1)
            text(s, x, y + 0.15, 0.5, 0.5, str(k + 1), size=20, bold=True, color=col, font=HEAD)
            text(s, x + 0.55, y + 0.17, 5.3, 0.55, it, size=18)
    notes(s, 0.5, "Be upfront about limits; it builds trust.")

    # 15. close ----------------------------------------------------------
    s = new_slide(prs, dark=True)
    text(s, 0.6, 0.55, 12, 1.0, "The answer for Rakesh", size=48, bold=True, color=WHITE, font=HEAD, name="Title")
    answer = (f"At {cr(inp['land_price_cr'])} the land {'meets' if m['project_npv'] >= 0 else 'fails'} a "
              f"{inp['hurdle_rate_pct']:.0f}% hurdle.")
    text(s, 0.6, 1.55, 12, 0.6, answer, size=24, color=LINE)
    big = [(cr(bl) if bl is not None else "n/a", "the most to pay for the land", TEAL_MID),
           (cr(m["peak_funding"]), f"funding to line up by Q{tp}", BRICK_LIGHT),
           (v.upper(), "the verdict on today's numbers", WHITE)]
    for i, (val, lab, col) in enumerate(big):
        x = 0.6 + i * 4.15
        hline(s, x, 2.75, 3.8, WHITE, 1.5)
        text(s, x, 2.95, 3.9, 1.0, val, size=52, bold=True, color=col, font=HEAD)
        text(s, x, 4.0, 3.8, 0.6, lab, size=17, color=LINE)
    text(s, 0.6, 5.2, 7.5, 0.8, "Questions", size=40, bold=True, color=WHITE, font=HEAD)
    text(s, 0.6, 6.05, 7.5, 0.9, illus_note, size=14, color=LINE)
    title_block(s, 8.95, 5.0, 3.85, dark=True)
    notes(s, 0.25, "Restate the answer in one breath, then take questions. Any member may be asked about any formula.")

    # footer on content slides: course, group and slide number
    n = len(prs.slides)
    for i, sl in enumerate(prs.slides, 1):
        if i in (1, n):
            continue
        text(sl, 0.6, 7.0, 6, 0.3, f"CE725 Construction Economics and Finance · {GROUP}", size=11, color=MUTED, name="Footer")
        text(sl, W - 1.6, 7.0, 1.0, 0.3, f"{i} / {n}", size=11, color=MUTED, align=PP_ALIGN.RIGHT, name="Slide number")

    prs.save(HERE / "Presentation.pptx")

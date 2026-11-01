# Change report: review and redesign (1 Nov 2026)

**Project:** CE725 Topic 2, Real Estate Feasibility and Appraisal Tool  
**Team:** Group 30 (Ojas Somani, Shivam Shankar, Mrunal Pachpande)  
**Reviewer:** Claude (AI), working on the team's request. Log this review in the AI usage log (rows 34–38 were added for it).

## 1. What was checked

- The whole project: calculation engine, Streamlit app, website, API, Vercel setup, tests, benchmark script and the documents.
- All automated checks run before and after the changes. Before: 31/31 passed. After: 33/33 pass.
- The calculation engine was probed with edge cases: very profitable deals, zero sales, zero funding limits, construction starting at Q0 and fractional quarters.
- The website was run locally and checked on desktop, on a phone-sized screen, in dark mode and in print preview.
- The base case numbers did not change: NPV −₹6.35 cr, IRR 8.1%, peak funding ₹36.47 cr in Q8, maximum land price ₹10.80 cr. The Excel benchmark the team is building is still valid.

## 2. Bugs fixed

| # | Where | Problem | Fix | How to check it |
|---|---|---|---|---|
| 1 | `tool/model.py` `breakeven_land` | For a very profitable deal, the maximum land price said *"Even free land would not meet the hurdle"*. That is the opposite of the truth. The search stopped at 10× the land price; if NPV was still positive there, the function returned "none". | The function now checks free land first. If free land fails, the old message is still correct. Otherwise the search range keeps widening until NPV turns negative. | In Inputs, set sale price to 60,000 ₹/sq ft and land price to ₹2 cr. A real maximum land price now appears. New test: `test_max_land_price_found_for_a_very_profitable_deal`. |
| 2 | `tool/model.py` `verdict` | A profit on cost of exactly 0% was treated as "missing" (`0 or -1`), so it failed even a 0% threshold. | The check now tests for a missing value explicitly. | New test: `test_zero_profit_passes_a_zero_threshold`. |
| 3 | `tool/app.py` (Streamlit) | The banner kept saying "12 inputs are illustrative" after you replaced them. The inputs table and memo also kept the old flags. The website already handled this correctly. | Edited inputs are now flagged **your input** in the banner, the inputs table and the memo, the same as on the website. | Edit the land price in the Streamlit app; the count drops to 11. |
| 4 | `web/assets/tool.js` | Printing from the browser menu (Ctrl/Cmd+P) on any tab other than Decision printed that tab, not the lender summary. | The browser's print now always gives the Decision summary plus the memo, then returns to your tab. | Open Cash flow, press Ctrl/Cmd+P. |
| 5 | `web/index.html` | The RERA card said the account is drawn "only for land and construction". The model also counts stamp duty, approvals and premiums as eligible costs. | The text now says withdrawals follow completion and no longer names the cost heads. The model is unchanged; see open item 1. | Read the RERA card on the landing page. |
| 6 | Charter, slides, site | The team number was blank ("Team to fill in"). | Group 30 now appears in the charter, the title slide, the README, both web pages and the Streamlit caption. | Open `docs/Project_Charter.docx`. |

## 3. Redesign of the website

The idea: show money the way a construction drawing shows ground. ₹0 is the datum line, and money the developer has put in sits below it.

- **Landing page hero.** The example project's real funding curve is drawn as a site section, with the area below ₹0 hatched like earth. A level mark (▽) shows peak funding (−₹36.47 cr in Q8). Labels mark land purchase, construction start, possession and the quarter when all outside money is back. This answers the persona's first question ("how much money do I need to survive?") before any text. The line draws in once on page load. That animation is turned off for users who prefer reduced motion.
- **Verdict as a stamp.** GO / MARGINAL / NO-GO is set like an approval stamp, with "x of 4 checks passed" beside the checklist.
- **Lead numbers.** Peak funding, NPV and maximum land price come first, as large figures. The other six numbers sit below in smaller cards.
- **Charts.** On the cash chart, the ₹0 line is drawn as a datum and the outside money is shaded below it.
- **Controls.** The What-if panel is a dark control panel, so it reads apart from the results. Tabs are a solid bar.
- **Title block footer.** The footer is an architectural-drawing title block with project, course, team, **Group 30** and date.
- **Type and colour.** Archivo in narrow widths for headings and figures, Source Sans 3 for text, and mono only inside data tables. Colours: drafting-film grey-green background, survey teal for "go", brick for money below the datum, amber for "marginal".
- **Quality.** Responsive to phone width, dark mode, keyboard focus, and a print layout for lenders on white paper. All element IDs were kept, so the script and the API needed no structural change.

### Second pass on layout and colour (same day)

After reviewing every tab at desktop and phone sizes:

- **Answer first.** The tool's header is compact, and the placeholder warning is one line with a "Show which inputs" link. On phones the What-if panel folds into one bar ("What if? · Base case · Show"), so the verdict sits at the top of the screen.
- **One bold element.** The What-if panel is now light, with an ink top rule. The verdict stamp is the only strong element on the page.
- **Readable cash flow table.** It has section headings (Sales and collections, Costs, Project result, RERA account, Funding), bold key rows, zeros shown as faint dashes, and negatives in brick.
- **New chart, "Where the money goes".** It is a sorted bar of every cost line. Brick bars are paid up front, before sales; teal bars are paid during construction. Bars were chosen over a pie chart because ten slices of very different sizes are hard to compare as angles.
- **Group 30 is visible everywhere.** A badge sits next to the logo on both pages, the landing hero has a credit line, and the footer has the title block.
- **Colours kept, on purpose.** Drafting-paper grey-green, survey teal for "go", brick for money below the datum, and amber for "marginal". Each colour carries a meaning, and the result reads as calm and trustworthy to a lender.

## 4. Presentation rebuilt (`docs/make_deck.py`)

The deck is still generated from the live model, so it updates when you enter the real project. It now has 15 slides in the website's visual identity, with **7 native PowerPoint charts** you can click and edit:

| # | Slide | Visual |
|---|---|---|
| 1 | Should Rakesh buy this land? | The funding hole drawn as a site section (₹0 datum, peak marked), with a Group 30 title block |
| 2 | One person, one question | Big quote and the ranked needs |
| 3 | Risk is cash, not profit | **Column chart:** paid out vs collected each quarter, with the money spent before buyers pay |
| 4 | Eight steps | The process as a chain of steps |
| 5 | Base case verdict | NO-GO stamp, the four checks and four headline numbers |
| 6 | Where the money goes | **Doughnut chart:** six cost groups, total in the centre, share paid up front |
| 7 | Cash is tightest in Q8 | **Line chart:** cumulative cash vs outside money, against the ₹0 line |
| 8 | How the gap is funded | **Stacked columns:** equity vs loan by quarter, plus lender ratios |
| 9 | What moves the answer | **Tornado:** change in NPV from base, largest at top |
| 10 | Three cases | **Two column charts:** NPV and peak funding for base, downside and upside |
| 11 | How we know it's right | 33/33 checks, benchmark (pending), toy case, bugs found |
| 12 | Live demo | Six numbered steps |
| 13 | AI: helped vs needed checking | Two ranked lists |
| 14 | Limits and next steps | Two ranked lists |
| 15 | The answer for Rakesh | Three big numbers and Questions, with the Group 30 title block |

Every slide has the footer "CE725 Construction Economics and Finance · Group 30" and a slide number. Speaker notes with timings are kept. The type is at least 14pt and titles are 38pt, so it reads from the back of a room. The old deck is in `docs/_backup_2026-11-01/`.

## 5. Documents regenerated

`docs/make_docs.py` rebuilt every document with the fixed engine and the date 1 Nov 2026:
Project charter, user manual, validation report (now 33/33 checks), reflection report, presentation and AI usage log.

- **Originals are backed up** in `docs/_backup_2026-11-01/`. They had not been edited by hand since they were generated on 27 Oct, and the AI log's Accept/Modify columns were empty, so no team work was overwritten.
- **AI usage log:** five new rows (34–38) record this review. Fill in the Decision and Reason columns for them like the others.

## 6. Files changed

| File | Change |
|---|---|
| `tool/model.py` | Fixes 1 and 2 |
| `tool/test_model.py` | Two new regression tests (31 → 33) |
| `tool/app.py` | Fix 3; Group 30 in the caption |
| `web/index.html`, `web/tool.html` | Redesign; Group 30 title block; RERA wording (fix 5) |
| `web/assets/site.css` | New visual system (rewritten) |
| `web/assets/tool.js` | Stamp verdict, lead cards, datum chart, cost chart, grouped cash flow table, foldable What-if panel, print fix (fix 4) |
| `docs/make_docs.py` | Group 30, new date, new AI log rows |
| `docs/make_deck.py` | Rewritten: new design, 7 native charts, Group 30 on every slide |
| `docs/*.docx`, `*.pptx`, `*.xlsx` | Regenerated |
| `README.md` | Group 30, 33 checks, team-number task marked done |
| `benchmark/discrepancy_table.csv` | New, written by `compare.py` during the check; it fills in when the benchmark is entered |

## 7. Still open (team decisions, not bugs)

1. **RERA-eligible costs.** The model lets the RERA account pay for land, stamp duty, approvals, premiums and construction. MahaRERA's guidance counts many of these as land cost, but confirm it for your state. Change `ESCROW_ELIGIBLE` in `model.py` if needed, and keep the benchmark the same.
2. **Team-only items in the README are unchanged:** sample project inputs, the hand-built benchmark, the toy case on paper, AI log decisions, the reflection in your own words, user interviews and deploying to Vercel.
3. **Team size.** The course brief says teams of 5; the team PDF lists 3 members. If two members are missing, add them to `TEAM` in `make_docs.py`, to the slide in `make_deck.py` and to both web footers.
4. Streamlit shows harmless deprecation notices for `use_container_width` on recent versions. It still works.

# USER_CONTEXT.md: Who we are building for

Read this before writing or changing any code, UI text or output in this project. When a design choice is unclear, decide by asking: "Would this help the person described below make a better go/no-go decision, and would they trust it?"

Status: desk research (articles, reports, vendor blogs). Not yet confirmed by interviews. Items marked **[VALIDATE]** must be checked with real users and updated here.

---

## 1. The product in one line
A Streamlit tool that appraises the feasibility of a single residential real estate project in India (quarterly cash flow, NPV/IRR, peak funding, break-even, RERA escrow, construction loan, sensitivity). It is validated against an independent Excel benchmark. Course project (CE725), but built as if a real developer will use it.

## 2. Primary user
**A small or mid-size residential developer** (a handful of projects, not a listed company), or the finance person who works for them.

**Secondary users:** construction-finance officers at banks/NBFCs appraising the project; real estate consultants and valuers preparing feasibility reports; equity investors in a project.

### Persona (composite hypothesis, not a real person)
Rakesh runs a mid-size developer in Mumbai/Pune. He is about to commit crores to a land deal. Today he decides on a spreadsheet he or an analyst built, which few others fully trust. He knows construction and the local market well. He is not a finance modeller and has no patience for jargon. He needs to answer one question quickly: **"Should I buy this land, and how much money do I need to survive until collections catch up?"** He will also have to defend the numbers to a lender or investor.

## 3. His situation and pressures
- **Cash timing is the real risk.** RERA requires 70% of buyer collections to go to a construction-only account, so only about 30% is free cash. Land and approvals must be paid upfront while collections come in stages. Smaller developers feel this most. He cares more about *when he runs out of cash* than about the final profit.
- **Costs are volatile.** Construction costs are rising (industry estimates in 2026 range from about 3-5% to 10-15% depending on source and scope). In Mumbai, premiums are a huge cost line. Developers have largely been absorbing increases rather than raising prices.
- **Delays are expensive.** Under RERA, a delayed project owes interest to buyers. Delays also stretch financing costs.
- **Funding is uneven.** Banks and NBFCs have pulled back from mid-stage construction funding. Private credit is filling the gap at different terms.
- **Go/no-go rules of thumb.** Developers commonly use margin on development cost or IRR against a hurdle rate (one source cites 12-18% for residential). Land is often valued by residual land value or DCF. **[VALIDATE]** which one he actually uses.
- **Tools today:** Excel, which is flexible but fragile. Time goes into maintaining the model, and it is hard to trace a number back to its source. Feasibility.pro exists as a paid competitor. **[VALIDATE]** what he dislikes about his current setup.

## 4. What he wants (ranked)
1. **A trustworthy answer fast.** Go/no-go signal within minutes of entering inputs.
2. **Funding clarity.** Peak funding amount and the quarter it hits, plus how much is equity and how much is loan.
3. **"What if" without rebuilding the model.** Price down, cost up, sales slow, project delayed.
4. **Numbers he can defend to a lender.** DSCR, loan-to-cost, receivables cover, equity IRR, and downside cases.
5. **A max land price.** Break-even land cost, as well as break-even selling price.
6. **An audit trail.** Every input shows its source and date, or is labelled an assumption.

## 5. What he fears and distrusts
- A black box. If he cannot see how a number was derived, he will not use it.
- Invented market data. A made-up land rate or interest rate is worse than a blank field.
- Rosy-case-only outputs. Lenders look for resilience under real conditions, not ideal ones.
- Tools that ignore Indian rules, such as RERA escrow, GST, premiums and state differences.
- Being lectured with jargon. NPV, IRR and DSCR are fine, but each needs a one-line plain meaning.

## 6. Design principles
- **Lead with decisions, not metrics.** The Summary page shows: verdict-style headline, peak funding and its quarter, NPV, IRR, profit on cost, break-even price, break-even land price.
- **Every output gets a "so what".** One plain sentence beside each key number, for example "Cash is most negative in Q5 at ₹X; you need this much funding by then."
- **Show assumptions, never hide them.** Inputs table lists value, unit, source, date, and a flag for "assumption" vs "sourced".
- **Never invent defaults silently.** Placeholders must be visibly labelled as illustrative and must not be presented as market data.
- **Warn, don't crash.** Flag edge cases in plain language: loan limit reached, escrow too small for allowed withdrawals, no sales in a quarter, negative NPV, multiple IRRs (then show NPV and MIRR).
- **Stay correct before pretty.** An unvalidated tool earns little credit. Match the Excel benchmark within the agreed tolerance (±0.1%) before adding features.
- **Make formulas explainable.** Each model.py function is small, pure, documented, and maps to a course chapter, because team members are asked to explain any formula in the viva.

## 7. Domain rules the tool must respect
- RERA: 70% of collections go to the separate account. Withdrawals only for land and construction cost, in proportion to % completion. The other 30% is free cash.
- Lenders cannot sweep the 70% account to repay their loan. Loan repayment comes from free cash only.
- The escrow percentage should be an **input**, not a hardcode, since the law lets states vary it. **[VALIDATE]** against the state rules for the chosen project.
- Revenue is modelled net of GST. Tax rates are to be confirmed against the Act before they go in the tool.
- In the delay scenario, include interest payable to buyers under RERA. Confirm the rate in the state rules.
- Premiums (Mumbai especially) are shown as a separate, visible cost line.

## 8. Feature priority, adjusted for user needs
- **Must:** inputs, quarterly cash flow, project NPV/IRR, payback, profit on cost, peak funding (with quarter), break-even price, sensitivity table and tornado.
- **Should:** construction loan, equity cash flow and IRR, RERA escrow, tax, lender metrics, **base/downside/upside presets** (promoted from Could), **break-even land price**, **cost escalation input**, delay interest to buyers.
- **Could:** AI investment memo (behind a toggle; the manual must state that project inputs leave the machine), MIRR alongside IRR.
- **Won't:** multi-tower or phased projects, JV revenue-share structures, GST input-credit detail. State JV exclusion as a limitation, since joint development deals are common in Indian cities.

## 9. Tone of the UI and outputs
Plain, direct, no hype. Write like a sharp colleague, not a textbook. Short labels, units always shown (₹ crore, ₹/sq ft, %, quarters), and no unexplained acronyms on first use.

## 10. Open questions (update after interviews)
- Does he use residual land value, or only profit on cost? **[VALIDATE]**
- Which cost line surprises him most? **[VALIDATE]**
- Would a lender trust a tool's DSCR, or only their own sheet? **[VALIDATE]**
- What assumption is hardest to source, and where does it come from today? **[VALIDATE]**
- What would make him trust this tool over his spreadsheet? **[VALIDATE]**

## 11. Rules for you (the builder LLM)
- Do not fabricate market data, laws, rates or sources. If unknown, leave the field empty or labelled as an assumption and say so.
- Log every significant suggestion you make so the team can record it in the AI usage log, including anything the team later rejects or modifies.
- When your suggestion conflicts with this file, say so and explain why, rather than silently overriding it.

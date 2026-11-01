# Real-world checks (1 Nov 2026)

**What this is:** published Indian residential projects run through the tool's own engine (`tool/model.py`), with the results compared against what was published.
**What it is not:** the team's independent benchmark. The course requires that to be built by hand, without AI. These checks were prepared with AI (Claude) and should be logged in the AI usage log.

Re-run: `cd benchmark && python3 real_world_checks.py`. To see a case in the website, open the tool, go to **Inputs & sources → Load inputs from a file**, and pick a file from `benchmark/real_cases/`.

## Summary

| Check | What is compared | Published | Tool | Result |
|---|---|---|---|---|
| 0 | NPV and IRR maths on a published cash flow | NPV ₹30.49 cr, IRR 42.7% | NPV ₹30.49 cr, IRR 42.7% | **Exact match** |
| 1 | Revenue, cost and return of a real Pune project | Revenue ₹146.54 cr, cost ₹102.73 cr, B/C 1.43 | Revenue ₹146.54 cr, cost ₹102.73 cr, profit on cost 42.7% (= B/C 1.43) | **Exact match** |
| 2 | Revenue of a real Godrej land deal | ₹4,200 cr | ₹4,200.00 cr (at today's price) | **Exact match** |
| 2 | Return of that deal vs the developer's own targets | 20–25% IRR, 25–30% EBITDA margin (Godrej management) | IRR 19.6–25.0%, margin 21.8–27.0% | **In the same range** |
| 2 | Land price paid vs the tool's maximum land price | ~₹800 cr paid (market sources) | Maximum ₹930–1,093 cr | **Consistent:** the price paid is below what the tool says the land can bear |

## Check 0 and 1: Silver Gracia, Ravet, Pune

**Source:** Maske and Gaikwad, "Feasibility Study for a Residential Construction Project: A Case Study", IRJET Vol 8 Issue 5, May 2021 ([PDF](https://www.irjet.net/archives/V8/i5/IRJET-V8I5730.pdf)). The project is on 5 acres, with 4 towers plus a MHADA building, sold at about ₹5,900/sq ft, over 36 months, using a 10% discount rate. Total cost is ₹102.73 cr. The developer receives 60% of the ₹244.24 cr revenue (₹146.54 cr), and the landowner receives 40%.

**Check 0, the maths.** The paper's NPV of ₹30.49 cr and "IRR" of 42.7% come from treating every cost as paid today and all revenue as arriving one year later. Given that same cash flow, the tool's `npv()` and `irr()` reproduce both numbers exactly.

**Check 1, the full model.** Entered quarter by quarter (12 quarters of construction, sales over 36 months, no land cost because the landowner is paid in revenue share), the tool gets revenue, cost and profit on cost exactly right.

| | Paper (one lump sum) | Tool (quarter by quarter) |
|---|---|---|
| NPV at 10% | ₹30.49 cr | ₹32.99 cr |
| IRR | 42.7% | 129.7% a year |
| Peak funding | not given | ₹13.01 cr in Q4 |

**Why the IRR differs, and why that is a finding.** The paper's 42.7% is profit divided by cost over the whole project, not a yearly return. In the real project, buyers pay as construction progresses, so the developer's own money peaks at only ₹13 cr, and there is no land to buy. A small amount of money at risk for a short time gives a very high yearly IRR. This is exactly the timing effect the tool exists to show, and it is a good example for the reflection report: the published NPV is roughly right, but the published "IRR" is not an IRR.

**Simplifications** (needed to match the paper): the joint-development deal is approximated by setting land to zero and using 60% of the price, because the tool does not model revenue shares. Price and costs are held flat, tax is zero, and there are no soft costs. These are the paper's own assumptions.

## Check 2: Godrej Properties, Kharadi–Wagholi, Pune

**Sources:**
- The exchange filing of 2 Jun 2025: 14 acres, about 3.7 million sq ft, estimated revenue ₹4,200 cr ([The Realty Today](https://www.therealtytoday.com/news/news/godrej-properties-acquires-14-acre-land-in-punes-kharadi-wagholi-corridor-for-4200-crore-project/)).
- The land price: Godrej did not disclose it, and market sources put it at about ₹800 cr ([Outlook Business](https://www.outlookbusiness.com/corporate/godrej-properties-buys-14-acre-land-in-pune-for-about-rs-800-crore-to-build-homes)).
- Godrej's targets for new land deals: 20–25%+ IRR and 25–30% EBITDA margins (Q2 FY25 earnings call, [summary](https://alphaspread.com/security/nse/godrejprop/earnings-calls/q2-2025)).

**Inputs:**
- The 3.7 million sq ft is treated as saleable area.
- The price is ₹4,200 cr ÷ 3.7 million sq ft = ₹11,351/sq ft.
- Construction cost, escalation, price growth, tax and stamp duty are the tool's sourced or assumed base-case values.
- Timing: approvals take 3 quarters, construction takes 16 quarters, and 8% of the area sells each quarter.

| | With 5% a year price growth | At today's price |
|---|---|---|
| Revenue | ₹4,510 cr | **₹4,200 cr** (matches the filing) |
| Project IRR | **25.0%** | **19.6%** |
| Margin on revenue | 27.0% | 21.8% |
| NPV at 15% | ₹263.8 cr | ₹117.4 cr |
| Maximum land price | ₹1,093 cr | ₹930 cr |
| Peak funding | ₹903 cr in Q6 | ₹908 cr in Q6 |
| Verdict | Marginal | Marginal |

**Reading:**
- **The returns are where a listed developer says they should be.** The IRR (19.6–25.0%) and margin (21.8–27.0%) sit around Godrej's stated targets.
- **The land price is consistent.** The ~₹800 cr reportedly paid is below the tool's maximum land price, so the tool agrees that a careful developer could buy this land.
- **"Marginal", not "Go", is the right call.** Every base-case check passes. The verdict is Marginal only because the downside case (price −10%, cost +10%, sales 25% slower, 2 quarters late) turns NPV negative. The tool is saying the deal works but leaves little room for things going wrong, which is what a lender would want flagged.
- **The tool's warnings fit a deal this size.** It warns that the RERA account traps up to ₹132 cr of buyers' money, and that the cash flow changes sign more than once (MIRR 21.3%).

**Limits of this check:**
- Premiums and approval fees are not public, so they are set to zero, which makes the result slightly optimistic. The gap between the price paid and the maximum land price (about ₹130–290 cr) is roughly the room left for them.
- A 3.7 million sq ft project would be built in phases, but the tool models it as one phase.
- The land price comes from market sources, not a filing.

## What this shows

1. **The NPV and IRR maths reproduce published figures exactly** (check 0).
2. **Revenue, cost and profit add up exactly** for a real project (check 1) and a real filing (check 2).
3. **On a real deal the tool gives sensible answers.** Its returns land in a listed developer's target range, and it does not reject land that a careful developer actually bought.
4. **It catches a real mistake in a published study:** a "42.7% IRR" that is really total profit over cost.

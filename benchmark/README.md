# Independent benchmark: instructions for the team

The course brief says the base case must be recomputed **by hand or in a plain spreadsheet without AI assistance**.
This folder is where that happens. It is worth 20% of the marks, so keep it independent:

- Build `benchmark.xlsx` yourselves in plain Excel. Do not use AI, and do not open `tool/model.py` until your first comparison is done.
- Work from the method below and the inputs in the app's **Inputs & sources** tab (or `tool/base_case.json`). Type the inputs in yourselves.
- Use Excel's `NPV`, `IRR` and Goal Seek only to check numbers you have also worked out row by row.

## Method (same conventions as the tool)

1. Quarters Q0, Q1, … Every amount happens at the end of its quarter. Land is paid in Q0. Money in +, money out −.
2. Hurdle (discount) rates are effective annual: quarterly rate = (1 + r)^(1/4) − 1. The loan rate is nominal annual with
   interest charged monthly: quarterly rate = (1 + r/12)^3 − 1, charged on the opening loan balance. Quarters are whole numbers.
3. Built-up area = plot × FSI. Saleable area = built-up area × saleable ratio.
4. Stamp duty = rate × the higher of land price and ready reckoner value, paid in Q0.
5. Approval fees and premiums: spread evenly over Q0 up to the quarter before construction starts.
6. Construction: the share spent in the k-th of n construction quarters is S(k/n) − S((k−1)/n), with S(x) = 3x² − 2x³.
   The cost rate in quarter t is today's rate × (1 + escalation)^(t/4). % complete = running total of the shares.
7. Soft costs = % of construction. Contingency = % of (construction + soft). Marketing = % of bookings.
8. Sales: the sales-pace share of saleable area sells each quarter from launch until sold out (the last quarter takes what is left).
   Price in quarter t = launch price × (1 + growth)^((t − launch)/4). Bookings = area sold × price.
9. Collections: by quarter t every buyer has paid the share CE = booking% + (1 − booking% − possession%) × % complete,
   plus possession% once possession is reached (construction start + duration). Cumulative collections = cumulative bookings × CE.
10. RERA account: escrow% of each quarter's collections goes in. Withdrawals are limited to the smallest of (a) the account balance,
    (b) % complete × total (land + stamp duty + approvals + premiums + construction) minus what was already withdrawn, and
    (c) the land + stamp duty + approvals + premiums + construction actually spent so far minus what was already withdrawn.
    At possession the whole balance is released.
11. Tax on the project basis: tax = rate × cumulative (collections − costs), never below what was already paid (losses carry forward, no refunds).
12. Project cash flow = collections − all costs − tax. NPV at the hurdle rate, IRR (annualised), payback, profit on cost.
13. Funding (for peak funding, loan interest and equity IRR): each quarter, cash in = (100% − escrow%) of collections + RERA withdrawals;
    cash out = costs + tax (with loan interest deducted) + interest on the opening loan balance. A shortfall is met by equity up to its
    limit, then the loan up to its limit. A surplus repays the loan first, is held until possession, then returned to equity.
    Peak funding = the highest (equity in − equity returned + loan balance).

## What to fill in

Put your results in `benchmark_results.csv` (column `benchmark_value`), then run:

```bash
cd ../tool && python3 compare.py
```

It writes `discrepancy_table.csv` with the tool's value, yours, the difference and a status (±0.1% tolerance).
For every row marked DIFFERENT, find the cause **before** changing anything. It may be the tool, the benchmark or the
method itself. Record the cause and the fix in the last two columns; that table goes into the validation report.

## Also do by hand

A small toy case solved on paper (for example 3–4 quarters, one quarter of construction, a few sales) to check the timing
and sign conventions. Keep a photo or scan for the validation report.

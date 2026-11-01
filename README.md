# CE725 Topic 2: Real Estate Feasibility and Appraisal Tool (Group 30)

Built for a small or mid-size residential developer deciding **whether to buy a land parcel and how much money he needs
until buyer collections catch up** (see `USER_CONTEXT.md`, which governs every design choice).

## What is here

| Path | What it is |
|---|---|
| `USER_CONTEXT.md` | Who the tool is for, what he needs, rules for anyone (or any AI) changing the project |
| `tool/app.py` | Streamlit app: Decision, Cash flow, Funding & RERA account, What if, Inputs & sources, Memo, How it works |
| `tool/model.py` | The calculation engine: small, documented functions, each linked to a CE725 chapter |
| `tool/base_case.json` | Every input with value, unit, source, date and a sourced / assumption / illustrative flag |
| `tool/test_model.py`, `tool/test_api.py` | 33 automated checks for the engine and the website API, including a 300-scenario random sweep (AI-written, disclosed) |
| `tool/compare.py` | Compares the tool with the team's Excel benchmark (±0.1%) |
| `benchmark/` | Method and template for the independent benchmark the team builds **by hand, without AI** |
| `docs/` | Charter, user manual, validation report, reflection report, AI usage log, presentation, and `make_docs.py` that rebuilds them |

## Run it

```bash
cd tool
pip install -r requirements.txt
streamlit run app.py
```

Checks: `python3 -m unittest -v test_model.py test_api.py` (in `tool/`).
Rebuild every document after changing inputs or the benchmark: `pip install python-docx python-pptx openpyxl matplotlib`, then `python3 make_docs.py` (in `docs/`).

## Website (hosted on Vercel)

| Path | What it is |
|---|---|
| `web/index.html` | Landing page: who it is for, how it works, Indian rules, how the numbers are checked, limits and privacy |
| `web/tool.html`, `web/assets/` | The tool in the browser: same tabs as the Streamlit app, inputs saved in the visitor's own browser, save/load inputs as a file, a printable summary for a lender |
| `api/evaluate.py` | One Python serverless function. It validates the inputs and runs `tool/model.py`, so there is still one engine |
| `vercel.json`, `.vercelignore` | Serve `web/`, deploy the function, keep the reports and PDFs out of the upload |
| `serve_local.py` | Runs the site locally exactly as Vercel will: `python3 serve_local.py`, then open http://localhost:8000 |

**Deploy from GitHub (no install needed):**
1. Put the contents of this `Project` folder in a GitHub repository (this folder is the repository root, where `vercel.json` sits).
2. On vercel.com: **Add New → Project**, import the repository. Framework preset **Other**; leave the build command and
   output directory empty (`vercel.json` sets them). Click **Deploy**.
3. Open the URL Vercel gives you. `/` is the landing page and `/tool` is the tool.

**Or from the command line:** `npm i -g vercel`, then in this folder run `vercel` (preview) and `vercel --prod`.

The function uses only the Python standard library, so there is nothing to install on Vercel. Inputs sent to it are used
once and not stored. Checks for it: `python3 -m unittest -v test_api.py` in `tool/`.

## Hosting the Streamlit app instead (optional)

On Streamlit Community Cloud, create an app with the main file `tool/app.py` (it reads `tool/requirements.txt`).
Inputs typed into a hosted copy are processed on that server; the user manual says so.

## Still to do by the team

The brief requires these to be the team's own work, so they are left as marked slots (amber boxes in the Word files).

1. **Enter the sample project.** Replace every `illustrative` input in `tool/base_case.json` (or in the app's Inputs tab) with the
   sample project's numbers, and confirm the `assumption` ones (stamp duty, tax rate, loan rate, buyer interest rate, hurdle rates).
2. **Build the benchmark by hand.** Follow `benchmark/README.md` in plain Excel, without AI and without reading the code.
   Fill `benchmark/benchmark_results.csv`, run `python3 compare.py`, explain every difference, then run `python3 make_docs.py`.
3. **Solve the toy case on paper** and add it to the validation report.
4. **Review the AI usage log** (`docs/AI_Usage_Log.xlsx`): mark each entry Accept / Modify / Reject with your reason and how you
   checked it, and add your own prompts. At least 20 significant entries.
5. **Rewrite the reflection report** in your own words, add your own AI examples, and write the half-page individual reflections.
6. **Talk to 1–2 users** (a developer, a lender or a CA) about the [VALIDATE] questions in `USER_CONTEXT.md`; record what they said
   (bonus credit) and update `USER_CONTEXT.md`.
7. Team number (Group 30) is filled in the charter. **Rehearse** the presentation twice, and make sure every member can explain every formula.
8. **Deploy the website** on Vercel (steps above) and add the link to the user manual and the slides.

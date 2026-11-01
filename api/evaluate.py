"""Vercel serverless function for the website.

GET  /api/evaluate  -> the base case inputs (value, unit, source, date, flag) and the preset cases
POST /api/evaluate  -> {"inputs": {...}, "shocks": {...}, "edited": [...], "project_name": "..."}  -> full results

All maths lives in tool/model.py (the same engine the Streamlit app and the tests use). Nothing is stored.
"""
import json
import math
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool"))
import model as M  # noqa: E402

BASE, META = M.load_case()
MAX_BODY = 20_000

# Allowed range for every input. Anything outside is rejected with a plain message, never silently changed.
LIMITS = {
    "plot_area_sqft": (100, 5e7), "fsi": (0.1, 20), "saleable_ratio": (0.1, 1.5),
    "land_price_cr": (0, 1e5), "ready_reckoner_cr": (0, 1e5), "stamp_duty_pct": (0, 30),
    "approvals_cr": (0, 1e5), "premiums_cr": (0, 1e5),
    "construction_rate_psf": (100, 1e5), "cost_escalation_pct": (-20, 50), "construction_start_q": (0, 20),
    "construction_quarters": (1, 40), "soft_cost_pct": (0, 100), "contingency_pct": (0, 100),
    "launch_q": (0, 40), "price_psf": (100, 1e6), "price_growth_pct": (-30, 50), "sales_pace_pct": (0, 100),
    "marketing_pct": (0, 50), "booking_pct": (0, 100), "possession_pct": (0, 100),
    "escrow_pct": (0, 100), "delay_q": (0, 20), "buyer_interest_pct": (0, 50), "tax_rate_pct": (0, 60),
    "equity_limit_cr": (0, 1e5), "loan_limit_cr": (0, 1e5), "loan_rate_pct": (0, 50),
    "hurdle_rate_pct": (0, 100), "equity_hurdle_pct": (0, 100), "min_profit_on_cost_pct": (-100, 500),
}
SHOCK_LIMITS = {"price": (-90, 200), "cost": (-90, 200), "pace": (-100, 500), "delay": (0, 20)}
assert set(LIMITS) == set(BASE), "every input needs a range"


def number(value, label, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a number.")
    if not lo <= value <= hi:
        raise ValueError(f"{label} must be between {lo:,g} and {hi:,g}.")
    return float(value)


def clean(payload):
    """Validate the request. Returns (inputs, shocks, edited keys, project name)."""
    if not isinstance(payload, dict):
        raise ValueError("Send a JSON object.")
    raw = payload.get("inputs", {})
    if not isinstance(raw, dict):
        raise ValueError("'inputs' must be an object.")
    unknown = set(raw) - set(BASE)
    if unknown:
        raise ValueError(f"Unknown input(s): {', '.join(sorted(unknown))}.")
    inp = dict(BASE)
    for k, v in raw.items():
        inp[k] = number(v, META["inputs"][k]["label"], *LIMITS[k])
    shocks_raw = payload.get("shocks", {}) or {}
    if not isinstance(shocks_raw, dict) or set(shocks_raw) - set(SHOCK_LIMITS):
        raise ValueError("'shocks' may only contain price, cost, pace and delay.")
    shocks = {k: number(shocks_raw.get(k, 0), f"Shock '{k}'", *lim) for k, lim in SHOCK_LIMITS.items()}
    edited = payload.get("edited", []) or []
    if not isinstance(edited, list) or not all(isinstance(k, str) and k in BASE for k in edited):
        raise ValueError("'edited' must list input names.")
    name = payload.get("project_name") or META["project_name"]
    if not isinstance(name, str):
        raise ValueError("'project_name' must be text.")
    return inp, shocks, set(edited), name.strip()[:120] or META["project_name"]


def finite(x):
    """JSON has no NaN or infinity: replace them with null, recursively."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [finite(v) for v in x]
    return x


def base_case():
    return {"project_name": META["project_name"], "about": META["_about"], "inputs": META["inputs"],
            "presets": M.PRESETS, "preset_note": M.PRESET_NOTE, "limits": LIMITS, "whole": list(M.QUARTER_INPUTS)}


def evaluate(payload):
    inp0, shocks, edited, name = clean(payload)
    meta = {"project_name": name,
            "inputs": {k: {**v, "flag": "your input" if k in edited else v["flag"]} for k, v in META["inputs"].items()}}
    inp = M.scenario(inp0, **shocks)
    ev = M.evaluate(inp, base=inp0)
    res, m = ev["result"], ev["result"]["metrics"]
    cum, total = [], 0.0
    for x in res["project_cf"]:
        total += x
        cum.append(total)
    base_npv, torn = M.tornado(inp0)
    return finite({
        "project_name": name,
        "verdict": ev["verdict"],
        "checks": ev["checks"],
        "metrics": m,
        "breakeven_price": ev["breakeven_price"],
        "breakeven_land": ev["breakeven_land"],
        "downside": ev["downside"]["metrics"],
        "so_what": M.so_what(inp, ev),
        "warnings": res["warnings"],
        "illustrative_left": [v["label"] for v in meta["inputs"].values() if v["flag"] == "illustrative"],
        "timeline": res["timeline"],
        "series": {"cum_project_cash": cum, "outstanding": [max(0.0, o) for o in res["outstanding"]],
                   "escrow_balance": res["escrow_balance"], "loan_balance": res["loan_balance"]},
        "table": [[label, sum(v) if summable else None, v] for label, v, summable in M.cash_flow_rows(res)],
        "presets": {n: M.run(M.scenario(inp0, **p))["metrics"] for n, p in M.PRESETS.items()},
        "sensitivity": M.sensitivity(inp0),
        "tornado": {"base": base_npv, "rows": torn},
        "memo": M.memo(inp, meta, ev),
        "inputs_used": inp,
    })


class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        data = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, base_case())

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._send(413, {"error": "Request too large."})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, evaluate(payload))
        except (ValueError, json.JSONDecodeError) as e:
            self._send(400, {"error": str(e)})

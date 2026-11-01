"""Checks for the website's API (api/evaluate.py). Run: python3 -m unittest -v test_api.py"""
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
import evaluate as api  # noqa: E402

import model as M  # noqa: E402


class Api(unittest.TestCase):
    def test_same_numbers_as_the_model(self):
        inp, _ = M.load_case()
        out = api.evaluate({})
        self.assertAlmostEqual(out["metrics"]["project_npv"], M.run(inp)["metrics"]["project_npv"], places=9)
        json.dumps(out, allow_nan=False)  # valid JSON, no NaN

    def test_edited_inputs_are_no_longer_illustrative(self):
        out = api.evaluate({"inputs": {"land_price_cr": 12}, "edited": ["land_price_cr"]})
        self.assertNotIn("Land price", out["illustrative_left"])

    def test_bad_inputs_are_rejected_with_plain_messages(self):
        for bad in ({"inputs": {"fsi": "two"}}, {"inputs": {"construction_quarters": 500}}, {"inputs": {"x": 1}},
                    {"shocks": {"delay": 99}}, [], {"edited": ["x"]}, {"project_name": 5}):
            with self.assertRaises(ValueError, msg=str(bad)):
                api.evaluate(bad)

    def test_random_inputs_never_crash_and_keep_the_books_balanced(self):
        """Seeded sweep across the allowed ranges: warn, don't crash; cash in = cash out every quarter."""
        rng = random.Random(725)
        whole = set(M.QUARTER_INPUTS)
        for i in range(300):
            inp = {k: (rng.randint(int(lo), int(min(hi, 40))) if k in whole else rng.uniform(lo, hi))
                   for k, (lo, hi) in api.LIMITS.items()}
            r = M.run(inp)
            prev = 0.0
            for t in range(r["T"] + 1):
                sources = r["free_cash"][t] + r["escrow_out"][t] + r["equity_in"][t] + r["extra_equity"][t] + r["loan_draw"][t] + prev
                uses = r["total_costs"][t] + r["tax"][t] + r["interest"][t] + r["loan_repay"][t] + r["distribution"][t] + r["cash_balance"][t]
                self.assertAlmostEqual(sources, uses, delta=1e-6 * max(1.0, abs(uses)), msg=f"case {i} Q{t}")
                prev = r["cash_balance"][t]
            self.assertGreaterEqual(min(r["escrow_balance"]), -1e-6, msg=f"case {i}")
            self.assertLessEqual(max(r["loan_balance"]), inp["loan_limit_cr"] + 1e-6, msg=f"case {i}")
            if i % 10 == 0:  # the full web response for a subset (slower: break-evens and sensitivities)
                json.dumps(api.evaluate({"inputs": inp}), allow_nan=False)

    def test_every_input_has_a_range(self):
        self.assertEqual(set(api.LIMITS), set(M.load_case()[0]))


if __name__ == "__main__":
    unittest.main()

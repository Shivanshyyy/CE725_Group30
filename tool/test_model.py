"""Automated checks for model.py. Run: python3 -m unittest -v test_model.py

These are AI-written self-checks (invariants and small hand-checkable cases). They do NOT replace the
team's independent Excel benchmark; compare.py does that comparison.
"""
import unittest

import model as M

INP, META = M.load_case()


class Pieces(unittest.TestCase):
    def test_s_curve_sums_to_one(self):
        for n in range(1, 25):
            self.assertAlmostEqual(sum(M.s_curve_shares(n)), 1.0, places=12)
        self.assertEqual([round(100 * s, 2) for s in M.s_curve_shares(8)],
                         [4.30, 11.33, 16.02, 18.36, 18.36, 16.02, 11.33, 4.30])

    def test_collections_hand_case(self):
        # booked 100 in Q1; 50% complete in Q1, 100% in Q2; possession Q3; 10% booking, 5% at possession
        out = M.collections([0, 100, 0, 0], [0, 0.5, 1, 1], 3, 0.10, 0.05)
        for got, want in zip(out, [0, 52.5, 42.5, 5.0]):
            self.assertAlmostEqual(got, want)

    def test_tax_carries_losses_forward(self):
        out = M.tax_on_cumulative_profit([-10, 5, 10, -2, 4], 25)
        for got, want in zip(out, [0, 0, 1.25, 0, 0.5]):
            self.assertAlmostEqual(got, want)

    def test_buyer_delay_interest(self):
        out = M.buyer_delay_interest([10] * 5, promised=2, actual=4, annual_pct=11)
        for got, want in zip(out, [0, 0, 0, 30 * 0.0275, 40 * 0.0275]):
            self.assertAlmostEqual(got, want)

    def test_payback(self):
        self.assertAlmostEqual(M.payback_years([-100, 50, 50, 50]), 0.5)
        self.assertIsNone(M.payback_years([-100, 10, 10]))

    def test_multiple_irr_course_example(self):
        # PS2 #15: roots at 5%, 10%, 15%; three sign changes
        cfs = [-100, 330, -362.75, 132.825]
        self.assertEqual(M.sign_changes(cfs), 3)
        self.assertAlmostEqual(M.irr(cfs), 0.05, places=6)

    def test_mirr_course_example(self):
        # PS2 #17: MIRR = 9.27% with finance 8%, reinvest 10%
        cfs = [3000, 0, -10000, 2000, 2000, 2000, 2000]
        self.assertAlmostEqual(M.mirr(cfs, 0.08, 0.10), 0.0927, places=4)


class BaseCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = M.run(INP)

    def test_everything_sold_and_collected(self):
        r = self.r
        self.assertAlmostEqual(sum(r["area_sold"]), r["saleable_sqft"], places=4)
        self.assertAlmostEqual(r["metrics"]["total_collections"], r["metrics"]["total_bookings"], places=9)
        self.assertAlmostEqual(r["pc"][-1], 1.0)

    def test_escrow_never_negative_and_released(self):
        self.assertTrue(all(b >= -1e-9 for b in self.r["escrow_balance"]))
        self.assertAlmostEqual(self.r["escrow_balance"][-1], 0.0, places=9)
        self.assertAlmostEqual(sum(self.r["escrow_in"]), sum(self.r["escrow_out"]), places=9)

    def test_loan_within_limit_and_repaid(self):
        self.assertTrue(all(b <= INP["loan_limit_cr"] + 1e-9 for b in self.r["loan_balance"]))
        self.assertAlmostEqual(self.r["loan_balance"][-1], 0.0, places=9)

    def test_cash_balances_every_quarter(self):
        r, prev_cash = self.r, 0.0
        for t in range(r["T"] + 1):
            inflow = r["free_cash"][t] + r["escrow_out"][t] + r["equity_in"][t] + r["extra_equity"][t] + r["loan_draw"][t] + prev_cash
            outflow = r["total_costs"][t] + r["tax"][t] + r["interest"][t] + r["loan_repay"][t] + r["distribution"][t] + r["cash_balance"][t]
            self.assertAlmostEqual(inflow, outflow, places=9, msg=f"Q{t}")
            prev_cash = r["cash_balance"][t]

    def test_npv_is_zero_at_irr(self):
        cfs = self.r["project_cf"]
        rq = M.irr(cfs)
        self.assertIsNotNone(rq)
        self.assertAlmostEqual(M.npv(rq, cfs), 0.0, places=6)

    def test_npv_moves_the_right_way(self):
        base = self.r["metrics"]["project_npv"]
        self.assertGreater(M.run(M.scenario(INP, price=10))["metrics"]["project_npv"], base)
        self.assertLess(M.run(M.scenario(INP, cost=10))["metrics"]["project_npv"], base)
        self.assertLess(M.run(M.scenario(INP, delay=2))["metrics"]["project_npv"], base)

    def test_breakevens_give_zero_npv(self):
        p = M.breakeven_price(INP)
        self.assertAlmostEqual(M.run({**INP, "price_psf": p})["metrics"]["project_npv"], 0.0, places=4)
        land = M.breakeven_land(INP)
        self.assertAlmostEqual(M.run({**INP, "land_price_cr": land})["metrics"]["project_npv"], 0.0, places=4)


class Fixes(unittest.TestCase):
    """Regression checks for issues found during re-verification (27 Oct)."""

    def test_downside_not_applied_twice(self):
        down_inputs = M.scenario(INP, **M.PRESETS["Downside"])
        ev = M.evaluate(down_inputs, base=INP)
        self.assertAlmostEqual(ev["downside"]["metrics"]["project_npv"], M.run(down_inputs)["metrics"]["project_npv"])

    def test_fractional_quarters_rounded_with_warning(self):
        r = M.run({**INP, "construction_quarters": 12.7})
        self.assertEqual(r["timeline"]["duration"], 13)
        self.assertIn("was rounded to 13", " ".join(r["warnings"]))

    def test_loan_rate_is_nominal_charged_monthly(self):
        self.assertAlmostEqual(M.q_rate_loan(12), 1.01 ** 3 - 1)
        r = M.run(INP)
        t = next(t for t in range(1, r["T"] + 1) if r["loan_balance"][t - 1] > 0)
        self.assertAlmostEqual(r["interest"][t], r["loan_balance"][t - 1] * M.q_rate_loan(INP["loan_rate_pct"]))

    def test_unsold_at_horizon_is_flagged(self):
        self.assertIn("still unsold", " ".join(M.run({**INP, "sales_pace_pct": 0.1})["warnings"]))


class EdgeCases(unittest.TestCase):
    """Bad or extreme inputs must produce plain warnings, never a crash."""

    def warn(self, **change):
        return " ".join(M.run({**INP, **change})["warnings"])

    def test_no_sales(self):
        self.assertIn("Sales pace is zero", self.warn(sales_pace_pct=0))

    def test_booking_above_rera_cap(self):
        self.assertIn("Section 13", self.warn(booking_pct=15))

    def test_funding_limits_too_small(self):
        w = self.warn(equity_limit_cr=5, loan_limit_cr=5)
        self.assertIn("limits are not enough", w)
        self.assertIn("fully used", w)

    def test_delay_costs_buyer_interest(self):
        r = M.run({**INP, "delay_q": 4})
        self.assertGreater(sum(r["costs"]["buyer_delay_interest"]), 0)
        self.assertIn("Section 18", " ".join(r["warnings"]))

    def test_negative_npv_flagged(self):
        self.assertIn("NPV is negative", self.warn(price_psf=5000))

    def test_escrow_traps_cash_when_sales_run_ahead(self):
        r = M.run({**INP, "sales_pace_pct": 25, "launch_q": 0})
        self.assertGreater(max(r["escrow_balance"]), 0)
        self.assertIn("RERA account holds up to", " ".join(r["warnings"]))

    def test_escrow_share_is_an_input(self):
        r100 = M.run({**INP, "escrow_pct": 100})
        self.assertAlmostEqual(sum(r100["free_cash"]), 0.0)
        r0 = M.run({**INP, "escrow_pct": 0})
        self.assertAlmostEqual(sum(r0["escrow_in"]), 0.0)

    def test_evaluate_and_memo_run(self):
        ev = M.evaluate(INP)
        self.assertIn(ev["verdict"], ("Go", "Marginal", "No-go"))
        text = M.memo(INP, META, ev)
        self.assertIn("Recommendation", text)
        self.assertIn("illustrative", text)


if __name__ == "__main__":
    unittest.main()

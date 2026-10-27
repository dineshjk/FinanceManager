# -*- coding: utf-8 -*-
import tkinter as tk
import unittest


class TestDividendCalculation(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_get_num_handles_dot_empty_and_numbers(self):
        fv_var = tk.DoubleVar(self.root, value=10.0)
        pct_var = tk.DoubleVar(self.root, value=0.0)
        qty_var = tk.IntVar(self.root, value=100)
        tds_var = tk.DoubleVar(self.root, value=0.0)

        # Simulation of _get_num
        def _get_num(var, num_type=float, default=0.0):
            try:
                raw = self.root.getvar(var._name)
                if not raw or str(raw).strip() in ("", ".", "-"):
                    return default
                return num_type(str(raw).strip().replace(",", ""))
            except Exception:
                try:
                    return num_type(var.get())
                except Exception:
                    return default

        # 1. When pct_var holds "."
        self.root.setvar(pct_var._name, ".")
        self.assertEqual(_get_num(pct_var, float, 0.0), 0.0)

        # 2. When pct_var holds ""
        self.root.setvar(pct_var._name, "")
        self.assertEqual(_get_num(pct_var, float, 0.0), 0.0)

        # 3. When pct_var holds "15.5"
        self.root.setvar(pct_var._name, "15.5")
        self.assertEqual(_get_num(pct_var, float, 0.0), 15.5)

        # 4. When qty_var holds "" or "."
        self.root.setvar(qty_var._name, "")
        self.assertEqual(_get_num(qty_var, int, 0), 0)
        self.root.setvar(qty_var._name, ".")
        self.assertEqual(_get_num(qty_var, int, 0), 0)

        # 5. Calculation with "." input does not throw TclError
        def _calc():
            fv = _get_num(fv_var, float, 0.0)
            pct = _get_num(pct_var, float, 0.0)
            qty = _get_num(qty_var, int, 0)
            tds = _get_num(tds_var, float, 0.0)
            per_share = round(fv * (pct / 100), 4)
            gross = round(qty * per_share, 2)
            net = round(gross - tds, 2)
            return per_share, gross, net

        self.root.setvar(pct_var._name, ".")
        per_share, gross, net = _calc()
        self.assertEqual(per_share, 0.0)
        self.assertEqual(gross, 0.0)
        self.assertEqual(net, 0.0)

        # 6. Calculation with valid number
        self.root.setvar(pct_var._name, "50")
        self.root.setvar(qty_var._name, "200")
        per_share, gross, net = _calc()
        self.assertEqual(per_share, 5.0)
        self.assertEqual(gross, 1000.0)
        self.assertEqual(net, 1000.0)


if __name__ == "__main__":
    unittest.main()

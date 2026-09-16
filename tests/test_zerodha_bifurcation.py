from pathlib import Path
import sys
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from StockMan.trade_utils import bifurcate_zerodha_levies


def test_bifurcate_single_buy():
    trades = [
        {
            "id_stk": 1,
            "company_name": "Reliance Industries Ltd",
            "trade_type": "BUY",
            "exchange": "NSE",
            "qty": 100,
            "wap": 2500.0,
        }
    ]
    contract_levies = {
        "brok": 0.0,
        "etc": 7.43,
        "clearing": 0.0,
        "cgst": 0.67,
        "sgst": 0.67,
        "igst": 0.0,
        "stt": 250,
        "sebi": 0.25,
        "stamp": 37.50,
    }

    res = bifurcate_zerodha_levies(trades, contract_levies, trd_dt="2026-01-15")
    b_trades = res["bifurcated_trades"]
    c_totals = res["contract_totals"]

    assert len(b_trades) == 1
    t = b_trades[0]
    assert t["qty_trd"] == 100
    assert t["wap_unit_trd"] == 2500.0
    assert t["price_lot_trd"] == 250000.0
    assert t["etc_trd"] == 7.43
    assert t["stt_trd"] == 250
    assert isinstance(t["stt_trd"], int)
    assert t["stamp_trd"] == 37.50
    assert t["gst_trd"] == pytest.approx(1.34, 0.01)
    assert t["tax_trd"] == pytest.approx(1.34 + 37.50 + 250, 0.01)
    assert t["chrg_trd"] == pytest.approx(7.43 + 0.25, 0.01)

    # Generated column validation: error == 0 for BUY: net_amt - price_lot - tax - chrg == 0
    computed_err = t["net_amt_trd"] - t["price_lot_trd"] - t["tax_trd"] - t["chrg_trd"]
    assert abs(computed_err) < 0.0001


def test_bifurcate_mixed_buy_and_sell_with_integer_stt():
    trades = [
        {
            "id_stk": 1,
            "company_name": "Infosys Ltd",
            "trade_type": "BUY",
            "exchange": "NSE",
            "qty": 50,
            "wap": 1500.0,  # 75,000
        },
        {
            "id_stk": 2,
            "company_name": "Tata Consultancy Services",
            "trade_type": "SELL",
            "exchange": "NSE",
            "qty": 20,
            "wap": 3500.0,  # 70,000
            "sell_chrg": 15.93,
        },
        {
            "id_stk": 3,
            "company_name": "HDFC Bank Ltd",
            "trade_type": "BUY",
            "exchange": "BSE",
            "qty": 35,
            "wap": 1600.0,  # 56,000
        },
    ]
    # Total turnover = 75,000 + 70,000 + 56,000 = 201,000
    # Buy turnover = 75,000 + 56,000 = 131,000
    # Sell turnover = 70,000

    contract_levies = {
        "brok": 0.0,
        "etc": 5.97,
        "clearing": 0.0,
        "cgst": 0.55,
        "sgst": 0.55,
        "igst": 0.0,
        "stt": 201,      # odd number to test integer allocation
        "sebi": 0.20,
        "stamp": 19.65,  # must only go to BUY trades
        "sell_chrg": 15.93,
    }

    res = bifurcate_zerodha_levies(trades, contract_levies, trd_dt="2026-01-15")
    b_trades = res["bifurcated_trades"]
    c_totals = res["contract_totals"]

    assert len(b_trades) == 3

    # Check that STT sum matches contract note exactly and every single trade STT is an int
    assert sum(t["stt_trd"] for t in b_trades) == 201
    for t in b_trades:
        assert isinstance(t["stt_trd"], int)

    # Check Stamp duty: only BUY trades have stamp duty > 0
    t_infy, t_tcs, t_hdfc = b_trades[0], b_trades[1], b_trades[2]
    assert t_infy["stamp_trd"] > 0
    assert t_hdfc["stamp_trd"] > 0
    assert t_tcs["stamp_trd"] == 0.0
    assert pytest.approx(t_infy["stamp_trd"] + t_hdfc["stamp_trd"], 0.01) == 19.65

    # Check Sell charges: only SELL trade has sell_chrg > 0
    assert t_infy["sell_chrg_trd"] == 0.0
    assert t_hdfc["sell_chrg_trd"] == 0.0
    assert t_tcs["sell_chrg_trd"] == 15.93

    # Check error formula for each trade
    for t in b_trades:
        if t["trade_type_trd"] == "BUY":
            err = t["net_amt_trd"] - t["price_lot_trd"] - t["tax_trd"] - t["chrg_trd"]
        else:
            err = t["net_amt_trd"] - t["price_lot_trd"] + t["tax_trd"] + t["chrg_trd"]
        assert abs(err) < 0.0001

    # Check contract totals
    assert c_totals["total_turnover"] == 201000.0
    assert c_totals["buy_turnover"] == 131000.0
    assert c_totals["sell_turnover"] == 70000.0
    assert c_totals["payin_payout_obligation"] == 61000.0
    assert c_totals["stt_cont"] == 201


def test_bifurcate_validation_errors():
    with pytest.raises(ValueError, match="At least one trade is required"):
        bifurcate_zerodha_levies([], {})

    with pytest.raises(ValueError, match="invalid quantity"):
        bifurcate_zerodha_levies([{"company_name": "ABC", "qty": 0, "wap": 100}], {})

    with pytest.raises(ValueError, match="invalid trade type"):
        bifurcate_zerodha_levies([{"company_name": "ABC", "qty": 10, "wap": 100, "trade_type": "INVALID"}], {})


def test_zerodha_window_launch_and_close():
    import tkinter as tk
    from unittest.mock import patch
    from StockMan.trade_add_zerodha import add_trade_zerodha

    root = tk.Tk()
    root.withdraw()
    try:
        def _check_win(win):
            assert win.minsize() == (1080, 720)
            
            # Find main_frame
            frames = [w for w in win.winfo_children() if isinstance(w, tk.Frame)]
            assert len(frames) >= 2

            # Find all LabelFrames across the window
            label_frames = []
            for f in win.winfo_children():
                for cf in f.winfo_children():
                    if isinstance(cf, tk.LabelFrame):
                        label_frames.append(cf)
            
            assert len(label_frames) == 3
            titles = [lf["text"].strip() for lf in label_frames]
            assert "Contract Note Header" in titles
            assert "Trades in this Contract (One row per ISIN)" in titles
            assert "Statutory Levies & Charges (Contract Note Footer)" in titles

            for lf in label_frames:
                assert lf.pack_info()["fill"] == "x"

            # Verify no (m), (n), (o) enumerations in any label
            all_labels = []
            def _collect_labels(widget):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        all_labels.append(child.cget("text"))
                    _collect_labels(child)
            _collect_labels(win)

            for txt in all_labels:
                assert not txt.startswith("(m)")
                assert not txt.startswith("(n)")
                assert not txt.startswith("(o)")
                assert not txt.startswith("(p)")
                assert not txt.startswith("(w)")

        with patch.object(root, "wait_window", side_effect=_check_win), \
             patch("Shared.modal_utils.disable_parent", return_value="modal_1"), \
             patch("Shared.window_manager.push_window"), \
             patch("Shared.window_manager.safe_close_modal"):
            add_trade_zerodha(root)
    finally:
        root.destroy()


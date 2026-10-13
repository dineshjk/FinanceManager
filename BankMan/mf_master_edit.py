# -*- coding: utf-8 -*-
# BankMan/mf_master_edit.py

"""
Edit form for the ``mf_master`` table.
Presents a list of MF accounts in a Treeview and lets the user edit or delete them.
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    MF_MASTER_ADD_UI_THEME as _T,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info, show_colorful_yesno
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from .bank_db_utils import get_all_accounts
from Shared.globals import logger, get_db_connection, BANK_DB_PATH

# ---------------------------------------------------------------------------

def edit_mf_master(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    preselect_id: int | None = None,
) -> None:
    """Open a modal two-panel window for editing mf_master records.

    Parameters
    ----------
    parent:
        Owning window.
    calling_button:
        The button that opened this modal.
    """
    # ── Lookup data fetched once at open ─────────────────────────────────
    accounts = get_all_accounts()
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Mutual Fund Master  ✏️")
    win.geometry("950x660")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip
    tooltip_var = setup_footer_tooltip(win, bg_color=_T["header_bg"], fg_color=_T.get("header_fg", "white"))

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def show_help(win: tk.Toplevel) -> None:
        guide_lines = [
            "This screen allows you to modify the structural details of your registered Mutual Funds.",
            "",
            "• Selection: Click any row in the top grid to load its details into the editable form below.",
            "• Fields: You can modify the Linked Account, AMC, Scheme, Folio, and RTA.",
            "• Active: Uncheck for fully closed folios.",
            "",
            "Hotkeys:",
            "• Escape: Cancel and Close",
            "• Ctrl+Enter: Save Changes"
        ]
        faq_data = [
            (
                "Q: Can I delete a fund here?",
                "A: Yes, using 'Delete Selected'. It will be blocked if there are existing MF transactions linked to this fund."
            )
        ]
        show_standard_help(
            parent=win,
            title="Mutual Fund Master Edit Help",
            guide_lines=guide_lines,
            faq_data=faq_data
        )

    # Header
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit Mutual Fund Master   ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T.get("header_fg", "white"),
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # Instruction row
    instr_frame = tk.Frame(win, bg=_T["header_bg"])
    instr_frame.pack(fill="x", padx=5, pady=(0, 2))

    tk.Label(
        instr_frame,
        text="Click a Mutual Fund row below to load it into the edit form.",
        font=("Helvetica", 11, "italic"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # Treeview
    tree_frame = tk.Frame(win, bg=_T["main_bg"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "MFEdit.Treeview",
        background="#002626",
        foreground="white",
        fieldbackground="#002626",
        rowheight=26,
        font=("Helvetica", 11),
    )
    style.configure(
        "MFEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground=_T.get("header_fg", "white"),
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "MFEdit.Treeview",
        background=[("selected", "#005959")],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "AMC Name", "Scheme Name", "Folio Number", "RTA", "Bank", "Active")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="MFEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "AMC Name": (140, tk.NO, "w"),
        "Scheme Name": (200, tk.YES, "w"),
        "Folio Number": (140, tk.NO, "w"),
        "RTA": (80, tk.NO, "center"),
        "Bank": (160, tk.YES, "w"),
        "Active": (80, tk.NO, "center"),
    }
    for col, (width, stretch, anchor) in col_setup.items():
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        tree.column(col, width=width, stretch=stretch, anchor=anchor)

    tree.pack(fill="both", expand=True)

    # Data load
    def load_accounts() -> None:
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  mm.mf_master_id,
                            mm.amc_name,
                            mm.scheme_name,
                            mm.folio_number,
                            mm.rta_name,
                            b.name,
                            mm.is_active,
                            mm.account_id,
                            a.ac_number
                    FROM    mf_master mm
                    JOIN    accounts a ON a.ac_id = mm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY mm.amc_name, mm.scheme_name
                """)
                for row in cursor.fetchall():
                    is_active_str = "Yes" if row[6] else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ID
                            row[1],  # AMC Name
                            row[2],  # Scheme Name
                            row[3],  # Folio Number
                            row[4],  # RTA Name
                            row[5],  # Bank Name
                            is_active_str,
                            row[7],  # account_id
                            row[8],  # ac_number
                        ),
                    )
        except sqlite3.Error as exc:
            logger.error("edit_mf_master: failed to load accounts: %s", exc)

    load_accounts()
    


    # Divider and "selected" status label
    divider_frame = tk.Frame(win, height=2, bg=_T["header_bg"])
    divider_frame.pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(win, bg=_T["header_bg"])
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No fund selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 11, "bold"),
        bg=_T["header_bg"],
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # Edit form
    selected_id = {"mf_master_id": None}

    form_frame = tk.Frame(win, bg=_T["main_bg"])
    form_frame.pack(fill="x", padx=10, pady=4)

    # Row 0: Linked Account
    tk.Label(
        form_frame,
        text="Linked Account:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=0, column=0, sticky="w", padx=5, pady=4)
    
    account_combo = ttk.Combobox(
        form_frame,
        width=62,
        font=("Helvetica", 13, "bold"),
        state="disabled",
    )
    account_combo.grid(row=0, column=1, sticky="w", padx=5, pady=4)
    account_combo["values"] = list(account_map.keys())
    apply_entry_theme(account_combo)
    bind_tooltip(
        account_combo,
        tooltip_var,
        "Bank account to which this Mutual Fund is linked.",
    )

    # Row 1: AMC Name
    tk.Label(
        form_frame,
        text="AMC Name:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=4)
    
    amc_var = tk.StringVar()
    amc_entry = tk.Entry(form_frame, width=65, textvariable=amc_var, font=("Helvetica", 13, "bold"))
    amc_entry.grid(row=1, column=1, sticky="w", padx=5, pady=4)
    amc_entry.config(state="disabled")
    apply_entry_theme(amc_entry)
    bind_tooltip(amc_entry, tooltip_var, "Name of the Asset Management Company.")

    # Row 2: RTA Name
    tk.Label(
        form_frame,
        text="RTA (CAMS/KFintech):",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=4)
    
    rta_var = tk.StringVar()
    rta_entry = tk.Entry(form_frame, width=65, textvariable=rta_var, font=("Helvetica", 13, "bold"))
    rta_entry.grid(row=2, column=1, sticky="w", padx=5, pady=4)
    rta_entry.config(state="disabled")
    apply_entry_theme(rta_entry)
    bind_tooltip(rta_entry, tooltip_var, "Registrar and Transfer Agent.")

    # Row 3: Folio Number
    tk.Label(
        form_frame,
        text="Folio Number:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=3, column=0, sticky="w", padx=5, pady=4)
    
    folio_var = tk.StringVar()
    folio_entry = tk.Entry(form_frame, width=65, textvariable=folio_var, font=("Helvetica", 13, "bold"))
    folio_entry.grid(row=3, column=1, sticky="w", padx=5, pady=4)
    folio_entry.config(state="disabled")
    apply_entry_theme(folio_entry)
    bind_tooltip(folio_entry, tooltip_var, "Mutual Fund Folio Number.")

    # Row 4: Scheme Name
    tk.Label(
        form_frame,
        text="Scheme Name:",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).grid(row=4, column=0, sticky="w", padx=5, pady=4)
    
    scheme_var = tk.StringVar()
    scheme_entry = tk.Entry(form_frame, width=65, textvariable=scheme_var, font=("Helvetica", 13, "bold"))
    scheme_entry.grid(row=4, column=1, sticky="w", padx=5, pady=4)
    scheme_entry.config(state="disabled")
    apply_entry_theme(scheme_entry)
    bind_tooltip(scheme_entry, tooltip_var, "Name of the Mutual Fund Scheme.")

    # Row 5: Active
    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        form_frame,
        variable=is_active_var,
        text="Active",
        font=("Helvetica", 13),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
        selectcolor="#002626",
        activebackground=_T["main_bg"],
        activeforeground=_T["label_fg"],
        cursor="hand2",
        state="disabled",
    )
    is_active_chk.grid(row=5, column=1, sticky="w", padx=5, pady=4)

    # Treeview selection
    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        mf_id = vals[0]
        amc = vals[1]
        scheme = vals[2]
        folio = vals[3]
        rta = vals[4]
        bank_name = vals[5]
        is_active = True if vals[6] == "Yes" else False
        ac_number = vals[8]

        selected_id["mf_master_id"] = mf_id
        
        account_label = f"{bank_name} : [{ac_number}]"
        if account_label in account_map:
            account_combo.set(account_label)
        else:
            account_combo.set("")

        amc_var.set(amc)
        scheme_var.set(scheme)
        folio_var.set(folio)
        rta_var.set(rta)
        is_active_var.set(is_active)
        
        account_combo.config(state="readonly")
        amc_entry.config(state="normal")
        scheme_entry.config(state="normal")
        folio_entry.config(state="normal")
        rta_entry.config(state="normal")
        is_active_chk.config(state="normal")
        
        save_btn.config(state="normal")
        delete_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {amc} - {scheme}")
        amc_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    # Tab-order
    account_combo.bind("<Return>", lambda _e: amc_entry.focus_set())
    amc_entry.bind("<Return>", lambda _e: rta_entry.focus_set())
    rta_entry.bind("<Return>", lambda _e: folio_entry.focus_set())
    folio_entry.bind("<Return>", lambda _e: scheme_entry.focus_set())
    scheme_entry.bind("<Return>", lambda _e: save_btn.focus_set())

    # Save
    def on_save(_event=None) -> None:
        mf_id = selected_id["mf_master_id"]
        if mf_id is None:
            show_colorful_error(win, "No Selection", "Please select a fund first.")
            return

        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(win, "Validation Error", "Please select a valid linked bank account.")
            flash_error(account_combo)
            return
        account_id = account_map[account_label]

        amc = amc_var.get().strip()
        if not amc:
            show_colorful_error(win, "Validation Error", "AMC Name is required.")
            flash_error(amc_entry)
            return

        rta = rta_var.get().strip()

        folio = folio_var.get().strip()
        if not folio:
            show_colorful_error(win, "Validation Error", "Folio Number is required.")
            flash_error(folio_entry)
            return

        scheme = scheme_var.get().strip()
        if not scheme:
            show_colorful_error(win, "Validation Error", "Scheme Name is required.")
            flash_error(scheme_entry)
            return

        is_active = 1 if is_active_var.get() else 0

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE mf_master
                    SET    account_id = ?,
                           amc_name = ?,
                           rta_name = ?,
                           folio_number = ?,
                           scheme_name = ?,
                           is_active = ?
                    WHERE  mf_master_id = ?
                """, (account_id, amc, rta, folio, scheme, is_active, mf_id))
                conn.commit()

            show_colorful_info(win, "Success", f"Fund '{scheme}' updated.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Saved — select another fund or close.")
        except sqlite3.IntegrityError as exc:
            show_colorful_error(win, "Integrity Error", f"Must be unique.\nDetail: {exc}")
        except Exception as exc:
            show_colorful_error(win, "Error", f"Failed to update:\n{exc}")
            logger.exception("edit_mf_master: UPDATE failed for mf_master_id=%s", mf_id)

    # Delete
    def on_delete(_event=None) -> None:
        mf_id = selected_id["mf_master_id"]
        if mf_id is None:
            return

        scheme = scheme_var.get().strip()
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM mf_transactions WHERE mf_master_id = ?", (mf_id,))
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(win, "Error", f"Could not check linked transactions: {e}")
            return

        if tx_count > 0:
            show_colorful_error(win, "Cannot Delete", f"Fund has {tx_count} transaction(s).")
            return

        confirm = show_colorful_yesno(win, "Confirm Delete", f"Delete fund:\n{scheme}\n?")
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute("DELETE FROM mf_master WHERE mf_master_id = ?", (mf_id,))
                conn.commit()

            show_colorful_info(win, "Success", f"Deleted '{scheme}'.")
            load_accounts()
            _reset_form()
            sel_status_var.set("Deleted — select another fund or close.")
        except sqlite3.Error as e:
            show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    def _reset_form() -> None:
        selected_id["mf_master_id"] = None
        account_combo.set("")
        amc_var.set("")
        rta_var.set("")
        folio_var.set("")
        scheme_var.set("")
        is_active_var.set(True)

        account_combo.config(state="disabled")
        amc_entry.config(state="disabled")
        rta_entry.config(state="disabled")
        folio_entry.config(state="disabled")
        scheme_entry.config(state="disabled")
        is_active_chk.config(state="disabled")

        save_btn.config(state="disabled")
        delete_btn.config(state="disabled")

    save_btn: tk.Button
    delete_btn: tk.Button

    # Button frame
    btn_frame = tk.Frame(win, bg=_T["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=10, pady=(4, 6))

    delete_btn = tk.Button(
        btn_frame,
        text="🗑️  DELETE SELECTED  🗑️",
        command=on_delete,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    delete_btn.pack(side="left", padx=8)

    save_btn = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T.get("submit_bg", "#22c55e"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    save_btn.pack(side="right", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(delete_btn, _T.get("cancel_bg", "#ef4444"), _T.get("cancel_hover_bg", "#991b1b"))
    apply_button_animations(save_btn, _T.get("submit_bg", "#22c55e"), _T.get("submit_hover_bg", "#16a34a"))
    apply_button_animations(cancel_btn, _T.get("cancel_bg", "#ef4444"), _T.get("cancel_hover_bg", "#991b1b"))

    # Window-level bindings
    win.bind("<Control-Return>", lambda e: save_btn.invoke())
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)
    win.bind("<F1>", lambda e: None if (getattr(e, "state", 0) & 0x0004) else (show_help(win)))

    if preselect_id is not None:
        for item in tree.get_children():
            if tree.item(item)["values"][0] == preselect_id:
                tree.selection_set(item)
                on_tree_select()
                break
        
        # Hide the list components to make it a pure edit window
        instr_frame.pack_forget()
        tree_frame.pack_forget()
        sel_label_frame.pack_forget()
        try:
            divider_frame.pack_forget()
        except NameError:
            pass
            
        # Resize window smaller since tree is hidden
        win.geometry("950x400")
        
    parent.wait_window(win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except Exception:
        pass

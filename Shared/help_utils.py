# -*- coding: utf-8 -*-
# Shared/help_utils.py

import tkinter as tk
from tkinter import ttk
from Shared.gui_utils import apply_button_animations

STANDARD_HELP_THEME = {
    "help_bg": "#f8fafc",
    "help_header_bg": "#0f172a",
    "help_btn_bg": "#475569",
    "hover_bg": "#334155",
    "help_tab_bg": "#0284c7"
}

def show_standard_help(
    parent, 
    title: str, 
    guide_lines: list, 
    faq_data: list, 
    extra_tabs_callback=None
):
    """
    Generate a standardized tabbed Help window.
    
    :param parent: The parent Tkinter widget.
    :param title: Window title and header text.
    :param guide_lines: List of strings for the General Guide tab.
    :param faq_data: List of tuples (Question, Answer) for the FAQ tab.
    :param extra_tabs_callback: Optional function `func(notebook)` to inject extra tabs.
    """
    original_focus = None
    try:
        if parent:
            original_focus = parent.focus_get()
    except Exception:
        pass
        
    help_win = tk.Toplevel(parent)
    try:
        help_win.transient(parent)
    except Exception:
        pass
    help_win.title(f"{title} \u2014 Universal Finance Manager")
    help_win.configure(bg=STANDARD_HELP_THEME["help_bg"])
    help_win.geometry("850x700")
    help_win.resizable(True, True)
    help_win.attributes("-topmost", True)
    help_win.focus_force()
    try:
        help_win.grab_set()
    except Exception:
        pass

    tk.Label(
        help_win,
        text=title,
        font=("Helvetica", 16, "bold"),
        bg=STANDARD_HELP_THEME["help_header_bg"],
        fg="white",
        pady=8,
    ).pack(fill="x")

    style = ttk.Style(help_win)
        
    style.configure("TNotebook", background=STANDARD_HELP_THEME["help_bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=("Helvetica", 12, "bold"),
        padding=[10, 5],
        background="#e0e0e0",
        foreground="#333",
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", STANDARD_HELP_THEME["help_tab_bg"])],
        foreground=[("selected", "white")],
    )

    notebook = ttk.Notebook(help_win)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # === TAB 1: GUIDE ===
    if guide_lines:
        tab_general = tk.Frame(notebook, bg=STANDARD_HELP_THEME["help_bg"], padx=12, pady=12)
        notebook.add(tab_general, text="General Guide")
        gen_text = tk.Text(
            tab_general, wrap="word", bg=STANDARD_HELP_THEME["help_bg"],
            bd=0, padx=6, pady=6, font=("Helvetica", 12)
        )
        gen_text.pack(fill="both", expand=True)
        gen_text.insert("1.0", "\n".join(guide_lines))
        gen_text.config(state="disabled")

    # === CUSTOM TABS ===
    if extra_tabs_callback:
        extra_tabs_callback(notebook)

    # === TAB 2: FAQ ===
    if faq_data:
        tab_faq = tk.Frame(notebook, bg=STANDARD_HELP_THEME["help_bg"], padx=12, pady=12)
        notebook.add(tab_faq, text="FAQ")
        
        faq_idx = {"i": 0}
        nav_frame = tk.Frame(tab_faq, bg=STANDARD_HELP_THEME["help_bg"])
        nav_frame.pack(fill="x", pady=(0, 10))

        left_btn = tk.Button(nav_frame, text="<", width=3, font=("Helvetica", 11, "bold"))
        left_btn.pack(side="left", padx=(0, 10))

        right_btn = tk.Button(nav_frame, text=">", width=3, font=("Helvetica", 11, "bold"))
        right_btn.pack(side="right", padx=(10, 0))

        faq_counter_var = tk.StringVar()
        faq_counter_lbl = tk.Label(nav_frame, textvariable=faq_counter_var, bg=STANDARD_HELP_THEME["help_bg"], font=("Helvetica", 11))
        faq_counter_lbl.pack(side="left", padx=(10, 0))

        faq_jump_combo = ttk.Combobox(nav_frame, state="readonly", width=65, font=("Helvetica", 11))
        faq_jump_combo["values"] = [f"{idx+1}. {q}" for idx, (q, _) in enumerate(faq_data)]
        faq_jump_combo.pack(side="left", expand=True, padx=(10, 10))

        faq_text = tk.Text(tab_faq, wrap="word", bg=STANDARD_HELP_THEME["help_bg"], bd=0, padx=6, pady=6)
        faq_text.pack(fill="both", expand=True)
        
        # Standardized styling: Bold Red for Questions, standard for answers
        faq_text.tag_configure("question", font=("Helvetica", 13, "bold"), foreground="#dc2626")
        faq_text.tag_configure("answer", font=("Helvetica", 12), foreground="#334155")
        faq_text.config(state="disabled")

        def update_faq_view():
            i = faq_idx["i"]
            q, a = faq_data[i]
            
            faq_counter_var.set(f"Question {i+1} of {len(faq_data)}")
            faq_jump_combo.current(i)
            
            faq_text.config(state="normal")
            faq_text.delete("1.0", "end")
            faq_text.insert("end", f"{q}\n\n", "question")
            faq_text.insert("end", a, "answer")
            faq_text.config(state="disabled")

            # Disable navigation buttons at the ends intelligently
            left_btn.config(state="disabled" if i == 0 else "normal")
            right_btn.config(state="disabled" if i >= len(faq_data) - 1 else "normal")

        def _on_jump_selected(event):
            faq_idx["i"] = faq_jump_combo.current()
            update_faq_view()

        def go_prev_faq(_event=None):
            if faq_idx["i"] > 0:
                faq_idx["i"] -= 1
                update_faq_view()

        def go_next_faq(_event=None):
            if faq_idx["i"] < len(faq_data) - 1:
                faq_idx["i"] += 1
                update_faq_view()

        faq_jump_combo.bind("<<ComboboxSelected>>", _on_jump_selected)
        left_btn.config(command=go_prev_faq)
        right_btn.config(command=go_next_faq)
        help_win.bind("<Left>", go_prev_faq, add="+")
        help_win.bind("<Right>", go_next_faq, add="+")

        update_faq_view()

    # === CLOSE LOGISTICS ===
    def close_help(_e=None):
        if hasattr(parent, "_global_help_open"):
            parent._global_help_open = False
        # Defer destruction to safely return 'break' without bubbling the Escape event.
        # After destruction, explicitly restore the modal grab to the top of the window stack
        # because destroying a grab_set() window often fails to return the grab to its parent.
        def _destroy_and_restore():
            if help_win.winfo_exists():
                help_win.destroy()
            from Shared.window_manager import activate_previous_window
            activate_previous_window()
            
            if original_focus and original_focus.winfo_exists():
                try:
                    original_focus.focus_set()
                except Exception:
                    pass
        
        help_win.after(1, _destroy_and_restore)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    close_help_btn = tk.Button(
        help_win, text="Close", command=close_help, font=("Helvetica", 11, "bold"),
        bg=STANDARD_HELP_THEME["help_btn_bg"], fg="white", padx=12, pady=6, cursor="hand2"
    )
    close_help_btn.pack(side="bottom", pady=10)
    apply_button_animations(close_help_btn, STANDARD_HELP_THEME["help_btn_bg"], STANDARD_HELP_THEME["hover_bg"])

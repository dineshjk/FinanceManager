# -*- coding: utf-8 -*-
# Shared/__init__.py
# Shared package initialization
"""
Shared Infrastructure & Cross-Cutting Utilities Package.

This package contains foundational modules, UI components, themes, dialog factories,
cloud synchronization adapters, and window lifecycle managers utilized across both
the StockMan (Equity Portfolio) and BankMan (Banking & Cash Flow) subsystems.

Package Architecture & Components:
    • UI Framework & Styling:
        - `Shared.style_utils`: Centralized ttk style presets and widget configuration.
        - `Shared.gui_utils`: Visual animations, hover effects, date spinners, tree sorting.
        - `Shared.gui_progressive`: Autocomplete / live-search combobox helpers.
        - `Shared.menu_factory`: Declarative menu window generator.
    • Window & Dialog Management:
        - `Shared.modal_utils`: Parent disablement, grab management, focus unwinding.
        - `Shared.window_manager`: LIFO window hierarchy stack and escape-key shielding.
        - `Shared.dialog_sizing`: Dynamic geometry calculator for content-aware dialogs.
        - `Shared.dialog_utils`: Styled alert, error, and confirmation modal dialogs.
    • Help & Documentation:
        - `Shared.help_utils`: Reusable multi-tab help window builder with FAQ viewer.
        - `Shared.global_help`: Master Global Help Center (Ctrl+F1) and module directory.
    • System & Network Infrastructure:
        - `Shared.globals`: Application-wide constants, color themes, paths, error strings.
        - `Shared.network_utils`: IPv4 prioritization eliminating Windows DNS timeout stalls.
        - `Shared.google_drive_sync`: Cross-module Google Drive cloud synchronization adapter.
        - `Shared.validation_utils`: Input validation routines for financial data entry.
"""


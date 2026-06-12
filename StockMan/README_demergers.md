Demerger schema and examples
This file was added in error and has been removed. Please ignore.

This document explains the `demerger` and `demerger_allocations` schema
added to the project and shows example mappings of demerger events to the
new tables and how they would map into `transactions` (where applicable).

Schema summary
--------------

1) Table: demerger
   - id_demerger (INTEGER PK AUTOINCREMENT)
   - occurred_on (TEXT ISO date)  -- date when demerger was recorded
   - id_stk_existing (INTEGER)   -- FK into `stocks.id_stk` (old company)
   - description (TEXT)          -- human text describing the event
   - refund_per_old_share (REAL) -- cash refund paid per old share
   - created_by (TEXT)
   - created_at (TEXT)           -- timestamp when row created

2) Table: demerger_allocations
   - id_alloc (INTEGER PK AUTOINCREMENT)
   - id_demerger (INTEGER)      -- FK into `demerger.id_demerger`
   - id_stk_new (INTEGER NULL)  -- FK into `stocks.id_stk` (new company)
   - new_shares_per_old (REAL)  -- entitlement: how many new shares per old share
   - cash_per_old (REAL)        -- extra cash per old share (in addition to refund)
   - notes (TEXT)

Trigger behaviour (conservative)
--------------------------------
- A lightweight trigger `trg_demerger_auto_alloc` inserts a default
  allocation row when a `demerger` row is created. The default gives 1 new
  share per old share and copies `refund_per_old_share` into the
  `cash_per_old` column of the allocation row.
- If `refund_per_old_share` is greater than 0, the trigger also inserts a
  minimal `transactions` row with trade_type_trd='REFUND' to record a cash
  refund event. This is a convenience only and is intentionally small — the
  application should normally create more detailed transaction rows.

Why two tables?
----------------
- A single demerger event can map to multiple allocation entries (e.g., some
  fractional entitlements, multiple new symbols, cash + shares). Normalizing
  allocations into a separate table keeps the model flexible and auditable.

Examples
--------
Below are three example demerger events. For each, the left side shows the
input data you might have, and the right side shows the rows that should be
inserted into `demerger` and `demerger_allocations` (and the `transactions`
row that the trigger will create where applicable).

Example A (user-provided, 4 entries compressed into one event)
--------------------------------------------------------------
Input (conceptual):
- Date: 2024-06-01
- Old stock id (id_stk_existing): 10  -- example id
- Description: "Demerger of division X; new company Y allotment"
- Refund per old share: 2.50
- Allocation: 1 new share of id_stk_new=20 for each 1 old share

Rows to insert (application):
1) Into `demerger`:
   - occurred_on = '2024-06-01'
   - id_stk_existing = 10
   - description = 'Demerger of division X; new company Y allotment'
   - refund_per_old_share = 2.50

2) Into `demerger_allocations`:
   - id_demerger = <id returned from demerger insert>
   - id_stk_new = 20
   - new_shares_per_old = 1.0
   - cash_per_old = 0.0

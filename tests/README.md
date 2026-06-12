# Scripts

This folder contains small utilities used during development. The primary
script is `run_black_recent.py` which runs Black on recently modified
Python files inside the `StockMan` package.

Usage
-----

- Dry-run (check + diff) for files changed in the last 60 minutes:

```sh
python scripts/run_black_recent.py --minutes 60
```

- Apply formatting in-place for files changed in the last 30 minutes:

```sh
python scripts/run_black_recent.py --minutes 30 --apply
```

Options
-------
- `--minutes, -m` : lookback window in minutes (default 10)
- `--line-length, -l` : Black line-length (default 79)
- `--apply, -a` : format files in-place (default is check+diff)

VS Code integration
-------------------

Two workspace tasks were added under `.vscode/tasks.json`:

- "Black Recent (check+diff)" — runs the script in check mode for 60 minutes.
- "Black Recent (apply)" — runs the script with `--apply` and is the default
  build task. Run via Command Palette → Tasks: Run Task.

Best practices
--------------

- Keep `pyproject.toml` in the repository (already present) to define the
  project's Black/Ruff settings so formatting is consistent for everyone.
- Consider a Git pre-commit hook or using the `pre-commit` framework to
  enforce formatting on commit.

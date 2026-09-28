# MIKA Competitive Intelligence (Phase 1)

Standalone project. SQLite database in `data/`, collection scripts in `scripts/`,
shared code in `app/`, with `reports/`, `logs/` and `tests/` alongside.

## Set up in VS Code
1. File > Open Folder... and choose this `mika_ci` folder.
2. Open a terminal (Terminal > New Terminal) and run:
   - `python -m venv .venv`
   - Windows: `.venv\Scripts\activate`   Mac/Linux: `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. In VS Code choose the interpreter: Ctrl+Shift+P > Python: Select Interpreter > `.venv`.

## Step 1: see what Hotpoint's pages deliver
`python scripts/inspect_hotpoint.py`

Send back the printed output (or `data/raw/inspect_report.json`).
That tells us which collection method to build.

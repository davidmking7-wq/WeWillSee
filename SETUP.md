# Stock Scout — setup

Two pieces: the **skill** (instructions Claude reads, already in this repo
at `.claude/skills/stock-scout/SKILL.md`) and the **engine** (the `scout/`
Python package). The skill is picked up automatically when you open this
repo in Claude Code.

## 1. Python environment

Python 3.11+ required. From the repo root:

    python -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt      # Windows: .venv\Scripts\python

## 2. API keys

The engine reads free market data from Alpaca. Copy `.env.example` to
`.env` in the repo root and paste in your own keys from
https://alpaca.markets (free paper account, data-only use here):

    ALPACA_API_KEY=PK...
    ALPACA_SECRET_KEY=...
    ALPACA_PAPER=true

Never commit `.env` or paste keys into a chat — `.gitignore` already
excludes it.

## 3. First run

In Claude Code, type:

    /stock-scout

The first run builds the history tables from scratch (a few minutes — it
downloads 10 years of prices and calibrates the v3 engine). Later runs are
quick and only refresh that monthly. `scout/calibration.json` is generated,
engine-tagged, and deliberately not committed: any engine change forces an
automatic rebuild.

## What's in the repo

    .claude/skills/stock-scout/SKILL.md   the skill
    scout/                                the engine code (v3 signals)
    scout/universe.csv                    cached S&P 500 list
    picks.xlsx                            the scorecard (existing picks are v1)
    requirements.txt
    .env.example                          template for your keys
    README.md                             what the tool does
    SCOUT-DESIGN.md                       the method, lineage and honest limits

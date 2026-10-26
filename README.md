# UK stock market agent

A small Python agent that tracks the UK stock market every trading day and writes a Markdown report.

Each run:

1. Downloads a year of daily prices from Yahoo Finance (via `yfinance`) for the
   - indices: FTSE 100, FTSE 250 and FTSE All-Share
   - currencies and commodities: GBP/USD, GBP/EUR, Brent crude and gold
   - every FTSE 100 constituent listed in `uk_market_agent/ftse100.txt`
2. Works out the 1-day, 5-day and 1-year moves, the distance from the 52-week high, the FTSE 100 breadth and the top risers and fallers.
3. If `ANTHROPIC_API_KEY` is set, asks Claude to search the web for why the market and the biggest movers moved, and to write a short market wrap with sources.
4. Saves `reports/<date>.md` and `reports/latest.md`, and adds the day's closes to `reports/history.csv`.

If a report for the latest trading session already exists, the run does nothing, so weekends and bank holidays are handled for you.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m uk_market_agent              # with a Claude market wrap if ANTHROPIC_API_KEY is set
python -m uk_market_agent --no-claude  # data only
python -m uk_market_agent --force      # rebuild today's report
pytest -q
```

## Run it every day on GitHub

`.github/workflows/daily-uk-market.yml` runs the agent at 17:12 UTC, Monday to Friday, after the London close. It commits the new report to the repository and also shows it on the workflow run's summary page.

1. Push this repository to GitHub. Scheduled workflows only run on the default branch.
2. Optional: to get the Claude market wrap, add an `ANTHROPIC_API_KEY` secret under **Settings → Secrets and variables → Actions**.
3. To run it straight away, open **Actions → Daily UK market report → Run workflow**.

## Customising

- **What to track:** edit `INDICES` and `MACRO` in `uk_market_agent/config.py`. Any Yahoo Finance ticker works.
- **FTSE 100 membership:** the index changes every quarter, so keep `uk_market_agent/ftse100.txt` up to date. Tickers that fail to download are listed at the bottom of the report.
- **Commentary:** the prompt is in `uk_market_agent/commentary.py`, and the model is set by `CLAUDE_MODEL` in `config.py`.

Yahoo Finance data is unofficial and can be delayed or have gaps. This tool is for information only and is not investment advice.

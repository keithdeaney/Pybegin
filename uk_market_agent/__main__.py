"""Daily UK stock market tracker.

    python -m uk_market_agent               # fetch data, write reports/<date>.md
    python -m uk_market_agent --no-claude   # skip the Claude market wrap
"""

import argparse
import logging
import sys

from . import config
from .commentary import write_commentary
from .data import breadth, fetch_closes, last_session, summarise
from .report import append_history, build_report

log = logging.getLogger("uk_market_agent")


def claude_prompt(session, indices, macro, stocks, stats, top_n) -> str:
    by_move = sorted(stocks, key=lambda q: q.change_1d, reverse=True)
    fmt = lambda q: f"{q.name} ({q.ticker}): {q.close:,.2f}, {q.change_1d:+.2f}% today"
    return "\n".join(
        [
            f"UK market close for {session:%A %d %B %Y}.",
            "",
            "Indices:", *map(fmt, indices),
            "",
            "FX and commodities:", *map(fmt, macro),
            "",
            f"FTSE 100 breadth: {stats['advancers']} up, {stats['decliners']} down.",
            "",
            "Biggest FTSE 100 risers:", *map(fmt, by_move[:top_n]),
            "",
            "Biggest FTSE 100 fallers:", *map(fmt, reversed(by_move[-top_n:])),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily UK stock market report")
    parser.add_argument("--no-claude", action="store_true", help="skip the Claude market wrap")
    parser.add_argument("--force", action="store_true", help="rewrite today's report if it exists")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    constituents = config.load_constituents()
    tickers = [*config.INDICES, *config.MACRO, *constituents]
    log.info("Downloading %d tickers", len(tickers))
    closes = fetch_closes(tickers)

    if "^FTSE" not in closes or closes["^FTSE"].dropna().empty:
        log.error("No FTSE 100 data returned - aborting")
        return 1
    session = last_session(closes[["^FTSE"]]).date()

    report_path = config.REPORTS_DIR / f"{session.isoformat()}.md"
    if report_path.exists() and not args.force:
        log.info("Report for %s already exists (market closed today?) - nothing to do", session)
        return 0

    indices, _ = summarise(closes[[t for t in config.INDICES if t in closes]], config.INDICES)
    macro, _ = summarise(closes[[t for t in config.MACRO if t in closes]], config.MACRO)
    stocks, missing = summarise(closes[[t for t in constituents if t in closes]])
    missing += [t for t in constituents if t not in closes]
    stats = breadth(stocks)

    commentary = None
    if not args.no_claude:
        prompt = claude_prompt(session, indices, macro, stocks, stats, config.TOP_MOVERS)
        commentary = write_commentary(prompt, config.CLAUDE_MODEL)

    report = build_report(session, indices, macro, stocks, stats, missing, config.TOP_MOVERS, commentary)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    (config.REPORTS_DIR / "latest.md").write_text(report)
    append_history(config.HISTORY_FILE, session, indices + macro + stocks)

    log.info("Wrote %s", report_path)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

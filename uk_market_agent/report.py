"""Render the daily Markdown report and keep a running history."""

import csv
from datetime import date
from pathlib import Path

from .data import Quote


def _row(q: Quote) -> str:
    return (
        f"| {q.name} | {q.close:,.2f} | {q.change_1d:+.2f}% | {q.change_5d:+.2f}% "
        f"| {q.change_1y:+.2f}% | {q.off_high:+.1f}% |"
    )


def _table(quotes: list[Quote]) -> list[str]:
    return [
        "| Name | Close | 1D | 5D | 1Y | vs 52w high |",
        "|---|---:|---:|---:|---:|---:|",
        *(_row(q) for q in quotes),
    ]


def build_report(
    session: date,
    indices: list[Quote],
    macro: list[Quote],
    stocks: list[Quote],
    stats: dict[str, int],
    missing: list[str],
    top_n: int = 5,
    commentary: str | None = None,
) -> str:
    by_move = sorted(stocks, key=lambda q: q.change_1d, reverse=True)
    lines = [f"# UK market report - {session:%A %d %B %Y}", ""]

    if commentary:
        lines += ["## Market wrap", "", commentary.strip(), ""]

    lines += ["## Indices", "", *_table(indices), ""]
    lines += ["## Currencies & commodities", "", *_table(macro), ""]

    lines += [
        "## FTSE 100 breadth",
        "",
        f"- Advancers: **{stats['advancers']}** / Decliners: **{stats['decliners']}**"
        f" / Unchanged: {stats['unchanged']}",
        f"- At 52-week high: {stats['new_52w_highs']} / At 52-week low: {stats['new_52w_lows']}",
        "",
    ]
    lines += ["## Top risers", "", *_table(by_move[:top_n]), ""]
    lines += ["## Top fallers", "", *_table(list(reversed(by_move[-top_n:]))), ""]

    if missing:
        lines += [f"_No data for: {', '.join(sorted(missing))}_", ""]
    lines += ["_Data: Yahoo Finance via yfinance. Not investment advice._", ""]
    return "\n".join(lines)


HISTORY_FIELDS = ["date", "ticker", "name", "close", "change_1d"]


def append_history(path: Path, session: date, quotes: list[Quote]) -> None:
    """Append one row per instrument, skipping the date if it is already recorded."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open(newline="") as f:
            if any(row["date"] == session.isoformat() for row in csv.DictReader(f)):
                return
    is_new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if is_new:
            writer.writeheader()
        for q in quotes:
            writer.writerow(
                {
                    "date": session.isoformat(),
                    "ticker": q.ticker,
                    "name": q.name,
                    "close": round(q.close, 4),
                    "change_1d": round(q.change_1d, 4),
                }
            )

import csv
from datetime import date

import numpy as np
import pandas as pd
import pytest

from uk_market_agent import __main__ as agent
from uk_market_agent import config
from uk_market_agent.data import breadth, summarise
from uk_market_agent.report import append_history, build_report


def make_closes() -> pd.DataFrame:
    days = pd.bdate_range("2026-01-01", periods=30)
    rising = np.linspace(100, 130, 30)
    falling = np.linspace(200, 150, 30)
    gappy = np.full(30, np.nan)
    gappy[-1] = 50.0  # only one data point -> unusable
    return pd.DataFrame(
        {"^FTSE": np.linspace(8000, 8300, 30), "AZN.L": rising, "BP.L": falling, "NEW.L": gappy},
        index=days,
    )


def test_summarise_computes_changes():
    quotes, missing = summarise(make_closes(), {"^FTSE": "FTSE 100"})
    by_ticker = {q.ticker: q for q in quotes}

    assert missing == ["NEW.L"]
    assert by_ticker["^FTSE"].name == "FTSE 100"
    assert by_ticker["AZN.L"].name == "AZN"
    azn = by_ticker["AZN.L"]
    assert azn.change_1d == pytest.approx((130 / (130 - 30 / 29) - 1) * 100)
    assert azn.change_1y == pytest.approx(30.0)
    assert azn.off_high == pytest.approx(0.0)
    assert by_ticker["BP.L"].change_1d < 0


def test_breadth_counts():
    quotes, _ = summarise(make_closes()[["AZN.L", "BP.L"]])
    stats = breadth(quotes)
    assert stats["advancers"] == 1
    assert stats["decliners"] == 1
    assert stats["new_52w_highs"] == 1
    assert stats["new_52w_lows"] == 1


def test_report_orders_movers_and_lists_missing():
    closes = make_closes()
    indices, _ = summarise(closes[["^FTSE"]], {"^FTSE": "FTSE 100"})
    stocks, missing = summarise(closes[["AZN.L", "BP.L", "NEW.L"]])
    text = build_report(date(2026, 2, 11), indices, [], stocks, breadth(stocks), missing, top_n=1,
                        commentary="Shares rose.")

    risers = text.split("## Top risers")[1].split("## Top fallers")[0]
    fallers = text.split("## Top fallers")[1]
    assert "AZN" in risers and "BP" not in risers
    assert "BP" in fallers
    assert "## Market wrap" in text and "Shares rose." in text
    assert "No data for: NEW.L" in text


def test_history_is_not_duplicated(tmp_path):
    quotes, _ = summarise(make_closes()[["AZN.L", "BP.L"]])
    path = tmp_path / "history.csv"
    append_history(path, date(2026, 2, 11), quotes)
    append_history(path, date(2026, 2, 11), quotes)
    append_history(path, date(2026, 2, 12), quotes)

    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 4
    assert {r["date"] for r in rows} == {"2026-02-11", "2026-02-12"}


def test_main_writes_report_and_skips_rerun(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(config, "HISTORY_FILE", tmp_path / "history.csv")
    monkeypatch.setattr(config, "load_constituents", lambda: ["AZN.L", "BP.L", "GONE.L"])
    monkeypatch.setattr(agent, "fetch_closes", lambda tickers: make_closes())

    assert agent.main(["--no-claude"]) == 0
    session = make_closes().index[-1].date().isoformat()
    report = (tmp_path / f"{session}.md").read_text()
    assert "FTSE 100" in report
    assert "GONE.L" in report
    assert (tmp_path / "latest.md").read_text() == report

    # A second run for the same session (e.g. a bank holiday) leaves it alone.
    (tmp_path / f"{session}.md").write_text("kept")
    assert agent.main(["--no-claude"]) == 0
    assert (tmp_path / f"{session}.md").read_text() == "kept"


def test_commentary_skipped_without_api_key(monkeypatch):
    from uk_market_agent.commentary import write_commentary

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert write_commentary("data", config.CLAUDE_MODEL) is None

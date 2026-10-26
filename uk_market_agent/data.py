"""Download prices and turn them into daily statistics."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class Quote:
    ticker: str
    name: str
    close: float
    change_1d: float  # percent
    change_5d: float  # percent
    change_1y: float  # percent
    high_52w: float
    low_52w: float

    @property
    def off_high(self) -> float:
        """Percent below the 52-week high (0 means at the high)."""
        return (self.close / self.high_52w - 1) * 100


def fetch_closes(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Daily closing prices, one column per ticker, indexed by date."""
    import yfinance as yf

    raw = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw.empty:
        return pd.DataFrame()
    closes = raw["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(tickers[0])
    return closes.dropna(how="all")


def _pct(new: float, old: float) -> float:
    return (new / old - 1) * 100


def summarise(closes: pd.DataFrame, names: dict[str, str] | None = None) -> tuple[list[Quote], list[str]]:
    """Build a Quote per ticker. Returns (quotes, tickers with no usable data)."""
    names = names or {}
    quotes, missing = [], []
    for ticker in closes.columns:
        series = closes[ticker].dropna()
        if len(series) < 2:
            missing.append(ticker)
            continue
        close = float(series.iloc[-1])
        quotes.append(
            Quote(
                ticker=ticker,
                name=names.get(ticker, ticker.removesuffix(".L")),
                close=close,
                change_1d=_pct(close, series.iloc[-2]),
                change_5d=_pct(close, series.iloc[-6] if len(series) > 5 else series.iloc[0]),
                change_1y=_pct(close, series.iloc[0]),
                high_52w=float(series.max()),
                low_52w=float(series.min()),
            )
        )
    return quotes, missing


def last_session(closes: pd.DataFrame) -> pd.Timestamp | None:
    """Date of the most recent trading session in the data."""
    valid = closes.dropna(how="all")
    return None if valid.empty else valid.index[-1]


def breadth(quotes: list[Quote]) -> dict[str, int]:
    return {
        "advancers": sum(q.change_1d > 0 for q in quotes),
        "decliners": sum(q.change_1d < 0 for q in quotes),
        "unchanged": sum(q.change_1d == 0 for q in quotes),
        "new_52w_highs": sum(q.close >= q.high_52w for q in quotes),
        "new_52w_lows": sum(q.close <= q.low_52w for q in quotes),
    }

"""What the agent tracks. Edit these to change the daily report."""

from pathlib import Path

# Headline instruments: Yahoo Finance ticker -> display name.
INDICES = {
    "^FTSE": "FTSE 100",
    "^FTMC": "FTSE 250",
    "^FTAS": "FTSE All-Share",
}

MACRO = {
    "GBPUSD=X": "GBP/USD",
    "GBPEUR=X": "GBP/EUR",
    "BZ=F": "Brent crude ($)",
    "GC=F": "Gold ($)",
}

CONSTITUENTS_FILE = Path(__file__).with_name("ftse100.txt")

# How many FTSE 100 risers/fallers to list.
TOP_MOVERS = 5

# Where reports and the running history CSV are written.
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
HISTORY_FILE = REPORTS_DIR / "history.csv"

# Claude commentary (only used when ANTHROPIC_API_KEY is set).
CLAUDE_MODEL = "claude-opus-5-5"


def load_constituents(path: Path = CONSTITUENTS_FILE) -> list[str]:
    lines = path.read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]

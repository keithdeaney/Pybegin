"""Optional market wrap written by Claude, which searches the web for the news
behind the day's moves. Skipped when ANTHROPIC_API_KEY is not set."""

import logging
import os

log = logging.getLogger(__name__)

SYSTEM = """You are a UK equity market analyst writing the daily close summary for a \
private investor. You get the day's index levels, FX and commodity moves, FTSE 100 \
breadth and the biggest FTSE 100 risers and fallers.

Use web search to find out why the market and the biggest movers moved today \
(results, trading updates, broker rating changes, macro data, Bank of England, \
gilt yields, sterling). Then write a market wrap of 150-250 words in plain prose: \
the overall tone, the main drivers, and a short explanation for each notable mover. \
Name the source of each explanation in brackets, e.g. (Reuters). If you cannot find \
a reason for a move, say so rather than guessing. Do not give investment advice. \
Return only the wrap, without a heading."""

MAX_CONTINUATIONS = 5


def write_commentary(data_summary: str, model: str) -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.info("ANTHROPIC_API_KEY not set - skipping Claude commentary")
        return None

    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": data_summary}]
    try:
        for _ in range(MAX_CONTINUATIONS):
            response = client.beta.messages.create(
                model=model,
                max_tokens=16000,
                system=SYSTEM,
                output_config={"effort": "medium"},
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8,
                        "user_location": {"type": "approximate", "country": "GB"}}],
                # If a safety classifier declines, re-run on Anthropic's recommended model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=messages,
            )
            if response.stop_reason == "pause_turn":
                # Long web-search turn: send it back so the server can continue it.
                messages = [*messages, {"role": "assistant", "content": response.content}]
                continue
            break
    except anthropic.APIStatusError as e:
        log.warning("Claude API error %s - report will have no commentary: %s", e.status_code, e)
        return None
    except anthropic.APIConnectionError as e:
        log.warning("Could not reach the Claude API - report will have no commentary: %s", e)
        return None

    if response.stop_reason == "refusal":
        log.warning("Claude declined to write commentary")
        return None
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None

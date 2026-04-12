"""
AI research layer — queries an OpenAI-compatible endpoint for recent
company developments and a qualitative lean. Additive to the TA score;
never replaces it.

Env vars:
    OPENAI_API_KEY    (required when --ai is used)
    OPENAI_BASE_URL   default: https://api.openai.com/v1
    OPENAI_MODEL      default: gpt-4o-mini

For actually-recent news, point OPENAI_BASE_URL at a provider with
browsing (Perplexity, OpenRouter browsing models, etc.). Plain chat
completions are bounded by the model's training cutoff.
"""

import json
import os


SYSTEM_PROMPT = """You are an equity research assistant. Given a company
ticker and name, summarize what the company has been up to recently:
earnings results, product launches, management changes, regulatory or
legal events, sector/macro headwinds or tailwinds, and notable analyst
or insider activity. Be specific — cite dates and concrete facts when
you can. If you do not have recent information, say so explicitly
rather than guessing.

Technical analysis is being handled separately. Focus on FUNDAMENTALS
and RECENT NEWS, not chart patterns.

Finish with a qualitative lean: bullish, neutral, or bearish, based on
the news and fundamentals you described.

Respond in JSON with this exact shape:
{
  "summary": "<3-8 sentences of recent developments>",
  "sentiment": "bullish" | "neutral" | "bearish",
  "key_points": ["short bullet 1", "short bullet 2", ...]
}
"""


def research(ta_result: dict) -> dict:
    """Call the configured OpenAI-compatible endpoint. Returns a dict
    with keys: summary, sentiment, key_points, model. Raises on failure."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key, base_url=base_url)

    ticker = ta_result.get("ticker", "")
    name   = ta_result.get("name") or ticker
    date   = ta_result.get("date", "")

    user_msg = (
        f"Company: {name}\n"
        f"Ticker: {ticker}\n"
        f"Today's date: {date}\n\n"
        f"Summarize recent developments and give a fundamentals-based lean."
    )

    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.3,
    )

    # Try JSON mode; fall back to plain text if the endpoint rejects it.
    try:
        resp = client.chat.completions.create(
            response_format={"type": "json_object"}, **kwargs
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)

    content = resp.choices[0].message.content or ""

    parsed = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Some providers (e.g. browsing models) may return prose. Keep it.
        parsed = {"summary": content.strip(), "sentiment": "neutral", "key_points": []}

    return {
        "summary":    parsed.get("summary", "").strip(),
        "sentiment":  parsed.get("sentiment", "neutral"),
        "key_points": parsed.get("key_points", []) or [],
        "model":      model,
    }


def format_ai_section(ai: dict) -> str:
    """Render the AI research dict as a text section to append to the report."""
    emoji = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}.get(ai.get("sentiment"), "⚪")
    lines = []
    lines.append("")
    lines.append(f"━━ AI Research ({ai.get('model', 'unknown')}) ━━")
    lines.append(f"Fundamental lean: {emoji} {ai.get('sentiment', 'neutral').upper()}")
    lines.append("")
    summary = ai.get("summary", "").strip()
    if summary:
        lines.append(summary)
        lines.append("")
    for kp in ai.get("key_points", []):
        lines.append(f"  • {kp}")
    if ai.get("key_points"):
        lines.append("")
    lines.append("⚠️ AI-generated; may be incomplete or out of date. Verify before acting.")
    return "\n".join(lines)

"""Discord webhook sender. Splits long messages at the 2000-char limit."""

import requests


MAX_CHARS = 1900  # leave headroom for code fences


def _chunk(text: str, limit: int = MAX_CHARS):
    """Split text into chunks ≤ limit chars, preferring blank-line boundaries."""
    if len(text) <= limit:
        return [text]

    chunks = []
    buf = ""
    for para in text.split("\n\n"):
        # Paragraph alone exceeds limit → hard-split on newlines.
        if len(para) > limit:
            if buf:
                chunks.append(buf)
                buf = ""
            for line in para.split("\n"):
                if len(line) > limit:
                    for i in range(0, len(line), limit):
                        chunks.append(line[i:i + limit])
                elif len(buf) + len(line) + 1 > limit:
                    chunks.append(buf)
                    buf = line
                else:
                    buf = line if not buf else buf + "\n" + line
            continue

        sep = "\n\n" if buf else ""
        if len(buf) + len(sep) + len(para) > limit:
            chunks.append(buf)
            buf = para
        else:
            buf = buf + sep + para

    if buf:
        chunks.append(buf)
    return chunks


def send(text: str, webhook_url: str) -> None:
    """POST text to a Discord webhook, splitting if needed. Raises on HTTP error."""
    for chunk in _chunk(text):
        body = f"```\n{chunk}\n```"
        r = requests.post(webhook_url, json={"content": body}, timeout=15)
        r.raise_for_status()

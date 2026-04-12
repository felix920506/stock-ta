#!/usr/bin/env python3
"""
Stock Technical Analysis — standalone CLI.

Usage:
    python analyze.py <TICKER> [--period 6mo] [--interval 1d]
                               [--format text|json]
                               [--ai] [--discord] [--discord-url URL]
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import ta_core
import ai_research
import discord_post


def main():
    parser = argparse.ArgumentParser(description="Stock Technical Analysis")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL, TSLA, 2330.TW)")
    parser.add_argument("--period",   default="6mo", help="Data period: 1mo 3mo 6mo 1y 2y (default: 6mo)")
    parser.add_argument("--interval", default="1d",  help="Bar interval: 1d 1wk 1mo (default: 1d)")
    parser.add_argument("--format",   default="text", choices=["json", "text"],
                        help="Output format (default: text)")
    parser.add_argument("--ai", action="store_true",
                        help="Append AI-generated company research")
    parser.add_argument("--discord", action="store_true",
                        help="Post result to Discord webhook (URL from .env or --discord-url)")
    parser.add_argument("--discord-url", default=None,
                        help="Override DISCORD_WEBHOOK_URL from .env")
    args = parser.parse_args()

    result = ta_core.analyze(args.ticker, args.period, args.interval)

    if "error" in result:
        print(json.dumps(result) if args.format == "json" else ta_core.format_report(result),
              file=sys.stderr)
        sys.exit(1)

    if args.ai:
        try:
            result["ai_research"] = ai_research.research(result)
        except Exception as e:
            print(f"[ai] research failed: {e}", file=sys.stderr)

    if args.format == "json":
        output = json.dumps(result, indent=2)
    else:
        output = ta_core.format_report(result)
        if "ai_research" in result:
            output += "\n" + ai_research.format_ai_section(result["ai_research"])

    print(output)

    if args.discord:
        webhook = args.discord_url or os.environ.get("DISCORD_WEBHOOK_URL")
        if not webhook:
            print("[discord] no webhook URL set (DISCORD_WEBHOOK_URL or --discord-url)",
                  file=sys.stderr)
            sys.exit(2)
        try:
            discord_post.send(output, webhook)
        except Exception as e:
            print(f"[discord] post failed: {e}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()

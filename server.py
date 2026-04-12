"""
Basic HTTP API for stock-ta, using Bottle.

Endpoints
    POST|GET /analyze    Run TA. Params from JSON body or query string.
                         `format=true` returns text/plain; otherwise JSON.
    POST     /format     Render a previously-captured result dict as text.
                         Accepts JSON body only.

Run:
    python server.py --host 0.0.0.0 --port 8000
    # or, after pip install:
    stock-ta-server --port 8000
"""

import argparse

from bottle import Bottle, request, response

import ta_core
import report


app = Bottle()


_TRUTHY = {"1", "true", "yes", "on", "y", "t"}


def _coerce_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in _TRUTHY


def _error(status: int, message: str):
    response.status = status
    response.content_type = "application/json"
    return {"error": message}


@app.route("/analyze", method=["GET", "POST"])
def analyze_endpoint():
    # JSON body takes precedence; fall back to query string.
    params = None
    try:
        params = request.json  # None if body is empty or not JSON
    except Exception:
        return _error(400, "Malformed JSON body")

    if not params:
        params = {k: request.query.getunicode(k) for k in request.query.keys()}

    ticker = params.get("ticker")
    if not ticker or not isinstance(ticker, str):
        return _error(400, "`ticker` is required")

    period   = params.get("period", "6mo") or "6mo"
    interval = params.get("interval", "1d") or "1d"
    as_text  = _coerce_bool(params.get("format"), default=False)

    result = ta_core.analyze(ticker, period, interval)
    if "error" in result:
        return _error(404, result["error"])

    if as_text:
        response.content_type = "text/plain; charset=utf-8"
        return report.format_report(result)

    response.content_type = "application/json"
    return result


@app.route("/format", method="POST")
def format_endpoint():
    try:
        body = request.json
    except Exception:
        return _error(400, "Malformed JSON body")

    if body is None:
        return _error(415, "Request body must be JSON (Content-Type: application/json)")
    if not isinstance(body, dict):
        return _error(422, "JSON body must be an object")

    try:
        text = report.format_report(body)
    except (KeyError, TypeError) as e:
        return _error(422, f"Malformed result dict: {e}")

    response.content_type = "text/plain; charset=utf-8"
    return text


@app.route("/health", method="GET")
def health():
    response.content_type = "application/json"
    return {"status": "ok"}


def main():
    parser = argparse.ArgumentParser(description="stock-ta HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    app.run(host=args.host, port=args.port, debug=args.debug, quiet=not args.debug)


if __name__ == "__main__":
    main()

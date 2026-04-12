FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyze.py ta_core.py report.py ai_research.py discord_post.py server.py log_config.py ./

ENV STOCK_TA_CACHE_DIR=/data/yfinance-cache \
    STOCK_TA_LOG_LEVEL=INFO \
    STOCK_TA_LOG_FILE=- \
    PYTHONUNBUFFERED=1

EXPOSE 8000
VOLUME ["/data"]

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude unnecessary files)
COPY main.py .
COPY api/ api/
COPY services/ services/
COPY infrastructure/ infrastructure/
COPY agents/ agents/
COPY data_sources/ data_sources/
COPY protocols/ protocols/
COPY config/ config/
COPY data/ data/
COPY security/ security/
COPY integrations/ integrations/
COPY revenue/ revenue/
COPY migrations/ migrations/
COPY artisan/ artisan/
COPY tg_handlers/ tg_handlers/
COPY x402/ x402/
COPY scripts/ scripts/
COPY sentry_config.py .
COPY agent_wallet.py .

# Copy .env if exists (for env vars not set via Cloud Run)
COPY .env* ./

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

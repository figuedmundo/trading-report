FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY templates ./templates

# Create non-root user
RUN useradd -m -u 1000 notif && chown -R notif:notif /app
USER notif

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${SERVICE_PORT:-8004}/health || exit 1

# Run application - pass PORT from environment or default to 8004
CMD sh -c 'exec uvicorn src.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8004}'

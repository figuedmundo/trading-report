# ===== Stage 1: Builder =====
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential python3-dev curl gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /venv

COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt


# ===== Stage 2: Final =====
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango1.0-0 libasound2 \
    libpangocairo-1.0-0 libxss1 libxcb1 libxshmfence1 fonts-liberation libglib2.0-0 libgtk-3-0 wget \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH=0

WORKDIR /app
COPY . .

RUN playwright install chromium

EXPOSE 8000

CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:8000"]

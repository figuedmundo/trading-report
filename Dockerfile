# ===== Stage 1: Builder =====
FROM python:3.13-slim AS builder

# Install build tools (for Python deps that need compiling)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
WORKDIR /app
RUN python -m venv /venv

# Copy requirements and install Python deps
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt


# ===== Stage 2: Final =====
FROM python:3.13-slim

# Install system libs for Playwright Chromium
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango1.0-0 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxss1 \
    libxcb1 \
    libxshmfence1 \
    fonts-liberation \
    libglib2.0-0 \
    libgtk-3-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required by Playwright)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and Chromium
RUN npm install -g playwright \
    && playwright install chromium

# Copy Python venv from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy the rest of the application
COPY . .

# Expose your app port
EXPOSE 5000

# Start app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

# Use official Python slim image
FROM python:3.13-slim

# Install dependencies for Playwright Chromium
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

# Install playwright CLI & browsers
RUN npm install -g playwright \
    && playwright install chromium

# Set working directory
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the code
COPY . .

# Expose port
EXPOSE 5000

# Entrypoint
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:5000", "--workers", "2"]

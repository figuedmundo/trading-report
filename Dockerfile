# Use official Playwright image with Chromium and dependencies preinstalled
FROM mcr.microsoft.com/playwright:v1.50.0-noble

# Install Python 3.12 and venv tools (if not included)
RUN apt-get update && apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create and activate virtual environment
RUN python3.12 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app code
COPY . .

# Expose port for your app
EXPOSE 8000

# Start Gunicorn server (adjust app module as needed)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

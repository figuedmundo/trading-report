#!/bin/bash

# Market Report AI Deployment Script for PythonAnywhere

echo "🚀 Starting deployment of Market Report AI..."

# Update system packages
echo "📦 Installing system dependencies..."
pip3.13 install --user -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python3.13 -m playwright install chromium

# If you get permission issues, try:
# python3 -m playwright install --with-deps chromium

# Set up environment
echo "🔧 Setting up environment..."
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cp .env.example .env
    echo "Please edit .env file with your actual credentials"
fi

# Create logs directory
mkdir -p logs

# Set permissions
chmod +x run.py

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Configure WSGI in PythonAnywhere web tab"
echo "3. Set source code path to: /home/yourusername/market_report_ai"
echo "4. Set WSGI configuration file to: /home/yourusername/market_report_ai/wsgi.py"
echo "5. Test endpoints using /api/health"
echo ""
echo "🔗 Test endpoints:"
echo "- Health check: https://yourusername.pythonanywhere.com/api/health"
echo "- Process report: https://yourusername.pythonanywhere.com/api/webhook/process-report"
import os
import asyncio

from app import create_app


# ✅ Runtime Chromium Installer
async def ensure_chromium_installed():
    chromium_path = "/opt/render/.cache/ms-playwright/chromium_headless_shell-1181/chrome-linux/headless_shell"
    if not os.path.exists(chromium_path):
        print("Chromium not found. Installing using Playwright...")
        from playwright.__main__ import main as playwright_main
        await asyncio.to_thread(playwright_main, ["install", "chromium"])
    else:
        print("Chromium already installed. Skipping install.")


# ✅ Install Chromium before app starts
asyncio.run(ensure_chromium_installed())

# ✅ Create your Flask app
app = create_app()

if __name__ == "__main__":
    # Used when running directly (e.g. python run.py)
    app.run(host='0.0.0.0', port=5000)
    
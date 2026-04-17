#!/bin/bash
# Setup script for Teams Web Automation environment

echo "Setting up Teams Web environment..."

# Ensure playwright is installed
if ! command -v playwright &> /dev/null
then
    echo "Playwright not found, installing via pip..."
    pip install playwright
fi

# Install browsers
echo "Installing Chromium for Playwright..."
python3 -m playwright install chromium

# Check if chromium is available
echo "Verifying Chromium installation..."
python3 << EOF
import sys
from playwright.sync_api import sync_playwright

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        print(f"Chromium version: {browser.version}")
        browser.close()
    print("Playwright setup verified successfully.")
except Exception as e:
    print(f"Error during verification: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo "Installation (Echtbetrieb) environment ready."
else
    echo "Setup failed."
    exit 1
fi

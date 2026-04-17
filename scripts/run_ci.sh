#!/bin/bash
# scripts/run_ci.sh
# Wrapper script for HID compliance verification in CI/CD environments.

set -e

echo "Starting HID Compliance Verification Environment..."

# 1. Initialize Xvfb if not already running
if [ -z "$DISPLAY" ]; then
    echo "Initializing virtual framebuffer (Xvfb)..."
    # Clean up any existing Xvfb locks
    rm -f /tmp/.X99-lock
    Xvfb :99 -screen 0 1280x1024x24 &
    export DISPLAY=:99
    # Ensure .Xauthority exists
    touch ~/.Xauthority
    sleep 2
else
    echo "Using existing DISPLAY: $DISPLAY"
fi

# 2. Run the verification script
echo "Running hid_verify.py..."
python3 scripts/hid_verify.py

echo "Verification completed successfully."

#!/bin/bash
# scripts/run_ci.sh
# Wrapper script for HID compliance verification in CI/CD environments.

set -e

echo "Starting HID Compliance Verification Environment..."

# 0. Ensure environment is ready
mkdir -p screenshots
echo "Ensuring test account credentials..."
python3 scripts/manage_test_account.py

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

# 2. Launch Mock Teams UI in the background
echo "Launching Mock Teams UI..."
python3 scripts/mock_teams_ui.py > mock_ui.log 2>&1 &
MOCK_PID=$!

# Wait for UI to initialize
sleep 5

# 3. Run the verification scripts
echo "Running hid_verify.py (Desktop Mock)..."
set +e
python3 scripts/hid_verify.py
RESULT_DESKTOP=$?

echo "Running teams_web_automation.py (Web Mock)..."
python3 scripts/teams_web_automation.py
RESULT_WEB=$?

echo "Running real_teams_web_automation.py (Real Teams Web)..."
# We expect TEAMS_MEETING_URL to be set if we want to run against a specific meeting,
# otherwise it defaults to the Teams portal to ensure the real Microsoft UI is tested.
python3 scripts/real_teams_web_automation.py "$TEAMS_MEETING_URL"
RESULT_REAL=$?
set -e

# Calculate overall result
if [ $RESULT_DESKTOP -eq 0 ] && [ $RESULT_WEB -eq 0 ] && [ $RESULT_REAL -eq 0 ]; then
    RESULT=0
else
    RESULT=1
fi

# 4. Cleanup
echo "Cleaning up Mock UI (PID: $MOCK_PID)..."
kill $MOCK_PID || true

echo "--- Mock UI Log ---"
cat mock_ui.log
echo "-------------------"

if [ $RESULT -eq 0 ]; then
    echo "Verification completed successfully."
else
    echo "Verification failed with exit code $RESULT."
    exit $RESULT
fi

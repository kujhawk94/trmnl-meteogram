#!/bin/bash
set -e

# Ensure running as root
if [ "$EUID" -ne 0 ]; then
  echo "Re-running with sudo..."
  exec sudo "$0" "$@"
fi

# ===== Configuration: adjust these paths if your setup differs =====
BASE_DIR="/opt/trmnl-meteogram"
CRON_IDENTIFIER="run_forecast.sh"

echo "=== Removing cron job from root's crontab ==="
# Remove any lines containing the wrapper identifier
(crontab -u root -l 2>/dev/null | grep -v "${CRON_IDENTIFIER}") | crontab -u root -

echo "=== Deleting folder at $BASEIDR  ==="
rm -rf "$BASE_DIR"

echo "=== Cleanup complete ==="

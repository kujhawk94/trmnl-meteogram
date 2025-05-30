#!/bin/bash
set -e

# Ensure running as root
if [ "$EUID" -ne 0 ]; then
  echo "Re-running with sudo..."
  exec sudo "$0" "$@"
fi

# ===== Configuration: adjust these paths if your setup differs =====
BASE_DIR="/opt/trmnl-meteogram"

echo "=== Removing hourly anacron job ==="
rm -f /etc/cron.hourly/meteogram

echo "=== Deleting folder at $BASE_DIR  ==="
rm -rf "$BASE_DIR"

echo "=== Cleanup complete ==="

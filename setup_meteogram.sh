#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root. Re-running with sudo..."
  exec sudo "$0" "$@"
fi

TEST_MODE=false
if [ "$1" == "--test" ]; then
  TEST_MODE=true
  echo "Running in TEST MODE: will install/upgrade venv but NOT create crontab entry."
fi

BASE_DIR="/opt/termnl-meteogram"
VENV_PATH="$BASE_DIR/venv"
CONFIG_FILE="$BASE_DIR/config.ini"
SCRIPT_DEST="$BASE_DIR/gen_meteogram.py"
SCRIPT_PARAMS="--config $CONFIG_FILE"
WRAPPER="$BASE_DIR/run_forecast.sh"
LOGFILE="/var/log/trmnl-meteogram.log"
CRON_SCHEDULE="*/30 * * * *"

mkdir "$(dirname "$BASE_DIR")"

echo "=== Creating virtual environment at $VENV_PATH ==="
mkdir -p "$(dirname "$VENV_PATH")"
python3 -m venv "$VENV_PATH"

echo "=== Activating venv and installing packages ==="
source "$VENV_PATH/bin/activate"
pip install --upgrade pip

# Install Python dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "Error: requirements.txt not found in the current directory."
  exit 1
fi

echo "=== Installing forecast script to $SCRIPT_DEST ==="
cp gen_meteogram.py "$SCRIPT_DEST"
sed -i "1s|^.*$|#!$VENV_PATH/bin/python|" "$SCRIPT_DEST"
chmod +x "$SCRIPT_DEST"

echo "=== Creating wrapper script at $WRAPPER ==="
cat > "$WRAPPER" <<EOF
#!/bin/bash
source "$VENV_PATH/bin/activate"
"$SCRIPT_DEST" $SCRIPT_PARAMS
EOF

chmod +x "$WRAPPER"

echo "=== Setting up log file at $LOGFILE ==="
touch "$LOGFILE"
chown $(whoami):$(whoami) "$LOGFILE"
chmod 644 "$LOGFILE"

if [ "$TEST_MODE" = false ]; then
  echo "=== Registering cron job for root ==="
CRON_JOB="$CRON_SCHEDULE $WRAPPER >> $LOGFILE 2>&1"
( crontab -u root -l 2>/dev/null | grep -v "$WRAPPER" ; echo "$CRON_JOB" ) | crontab -u root -

echo "✅ Forecast script installed and scheduled."
  echo "Output will be updated every 30 minutes and logged to $LOGFILE"
fi
if [ "$TEST_MODE" = true ]; then
  echo "=== Running the forecast generator once in test mode ==="
  "$WRAPPER"
fi

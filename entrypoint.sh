#!/bin/bash
set -e

# Start a background process that waits for MAX_UPTIME_SECONDS, 
# then sends a SIGTERM signal to PID 1 (the main app process).
# Default MAX_UPTIME_SECONDS is 1 day, can be changed in bandsos.env
MAX_UPTIME="${MAX_UPTIME_SECONDS:-86400}"
(
    echo "Uptime monitor initiated. Container will self-restart in $MAX_UPTIME seconds."
    sleep "$MAX_UPTIME"
    echo "Max uptime reached. Sending SIGTERM to main process..."
    kill -15 1
) &

# 1. Initialize Conda for this shell session
# This mimics 'conda activate base' without requiring an interactive shell
source /opt/conda/etc/profile.d/conda.sh
conda activate base

# 2. Execute the command passed to 'docker run'
# 'exec' replaces the shell process with the command (e.g., /bin/bash or your script)
# "$@" preserves all arguments passed to the container
exec "$@"

#!/bin/bash
set -e

# 1. Initialize Conda for this shell session
# This mimics 'conda activate base' without requiring an interactive shell
source /opt/conda/etc/profile.d/conda.sh
conda activate base

# 2. Execute the command passed to 'docker run'
# 'exec' replaces the shell process with the command (e.g., /bin/bash or your script)
# "$@" preserves all arguments passed to the container
exec "$@"
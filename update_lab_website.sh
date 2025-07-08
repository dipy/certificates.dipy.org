#!/bin/bash

# ---
# Configuration
# ---

# Load MAILTO from .env file
if [ -f .env ]; then
    export $(grep -E '^MAILTO=' .env | xargs)
fi

# ---
# Helper Function
# ---

# Function to check the last command's exit status and send an email on failure
check_status_and_notify() {
    local exit_code=$?
    local step_name="$1"

    if [ $exit_code -ne 0 ]; then
        local error_message="Lab website update script FAILED at $(date): $step_name failed (exit code $exit_code)."
        echo "$error_message"

        if [ -n "$MAILTO" ]; then
            echo "$error_message" | mail -s "[ALERT] Lab website update script failed" $(echo "$MAILTO" | tr ',' ' ')
        fi
        exit 1 # Exit the script immediately on failure
    fi
}

# ---
# Script Execution
# ---

echo "========== Lab website update script triggered at $(date) ==========="

# Conda initialization and activation
source /home/dipy/miniforge3/etc/profile.d/conda.sh
check_status_and_notify "Sourcing conda profile"

conda activate base
check_status_and_notify "Activating base conda environment"

conda activate grgweb
check_status_and_notify "Activating grgweb conda environment"

# Navigate to the project directory
cd /home/dipy/grg-web
check_status_and_notify "Changing directory to /home/dipy/grg-web"

# Git operations
git pull
check_status_and_notify "Git pull"

# Build and deploy website
make -C . html
check_status_and_notify "Make HTML"

cp -R _build/* www
check_status_and_notify "Copying built files to www"

echo "=============== Lab website update completed ==================="
echo ""
exit 0

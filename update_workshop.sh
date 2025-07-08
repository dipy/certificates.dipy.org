#!/bin/bash

# ---
# Configuration
# ---

# Load MAILTO from .env file if it exists.
# This ensures MAILTO is set from your environment configuration.
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
        local error_message="Workshop update script FAILED at $(date): $step_name failed (exit code $exit_code)."
        echo "$error_message" >&2 # Print to stderr for better logging

        if [ -n "$MAILTO" ]; then
            echo "$error_message" | mail -s "[ALERT] Workshop update script failed" $(echo "$MAILTO" | tr ',' ' ')
        fi
        exit 1 # Exit the script immediately on failure
    fi
}

# ---
# Script Execution
# ---

echo "======= Workshop update script triggered at $(date) ======="

# Conda initialization and activation
# Ensure conda.sh is sourced correctly
source /home/dipy/miniforge3/etc/profile.d/conda.sh
check_status_and_notify "Sourcing conda profile"

# Activate base environment first, then the specific one
conda activate base
check_status_and_notify "Activating base conda environment"

conda activate workshop-env
check_status_and_notify "Activating workshop-env conda environment"

# Navigate to the project directory
cd /home/dipy/workshop.dipy.org
check_status_and_notify "Changing directory to /home/dipy/workshop.dipy.org"

# Git operations
git pull
check_status_and_notify "Git pull"

# Build and deploy workshop materials
make -C . html
check_status_and_notify "Make HTML for workshop"

cp -R _build/html/* www
check_status_and_notify "Copying built workshop files to www"

echo "========= Workshop update completed ==============="
echo ""
exit 0
#!/bin/bash

# Load MAILTO from .env file
if [ -f .env ]; then
    export $(grep -E '^MAILTO=' .env | xargs)
fi

# Script to update the lab website
{
    echo "========== Lab website update script triggered at $(date) ==========="
    # conda init bash
    source /home/dipy/miniforge3/etc/profile.d/conda.sh
    conda activate base
    conda activate grgweb
    cd /home/dipy/grg-web
    git pull
    make -C . html
    cp -R _build/* www
    echo "=============== Lab website update completed ==================="
    echo ""
    exit 0
} || {
    if [ -n "$MAILTO" ]; then
        echo "Lab website update script FAILED at $(date)" | mail -s "[ALERT] Lab website update script failed" $(echo "$MAILTO" | tr ',' ' ')
    fi
    exit 1
}

#!/bin/bash

# Load MAILTO from .env file
if [ -f .env ]; then
    export $(grep -E '^MAILTO=' .env | xargs)
fi

# Script to update the workshop materials
{
    echo "======= Workshop update script triggered at $(date) ======="
    # conda init bash
    source /home/dipy/miniforge3/etc/profile.d/conda.sh
    conda activate base
    conda activate workshop-env
    cd /home/dipy/workshop.dipy.org
    git pull
    make -C . html
    cp -R _build/html/* www
    echo "========= Workshop update completed ==============="
    echo ""
    exit 0
} || {
    if [ -n "$MAILTO" ]; then
        echo "Workshop update script FAILED at $(date)" | mail -s "[ALERT] Workshop update script failed" $(echo "$MAILTO" | tr ',' ' ')
    fi
    exit 1
}

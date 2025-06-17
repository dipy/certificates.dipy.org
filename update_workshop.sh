#!/bin/bash

# Script to update the workshop materials
echo "Workshop update script triggered at $(date)"

# Log the event
LOG_FILE="workshop_webhook_updates.log"
echo "==== Update triggered at $(date) ====" >> $LOG_FILE

# Update the Workshop website
# conda init bash
source /home/dipy/miniforge3/etc/profile.d/conda.sh
conda activate base
conda activate workshop-env
cd /home/dipy/workshop.dipy.org
git pull
make -C . html
cp -R _build/html/* www

echo "Update completed" >> $LOG_FILE
echo "Workshop update completed"

exit 0

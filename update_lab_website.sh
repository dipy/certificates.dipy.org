#!/bin/bash

# Script to update the lab website
echo "Lab website update script triggered at $(date)"

# Log the event
LOG_FILE="lab_webhook_updates.log"
echo "==== Update triggered at $(date) ====" >> $LOG_FILE

# Update the Lab website
# conda init bash
source /home/dipy/miniforge3/etc/profile.d/conda.sh
conda activate base
conda activate grgweb
cd /home/dipy/grg-web
git pull
make -C . html
cp -R _build/* www

echo "Update completed" >> $LOG_FILE
echo "Lab website update completed"

exit 0

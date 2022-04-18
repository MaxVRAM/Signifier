#!/bin/bash

echo
echo -------------------------------------------------
echo STOPPING SIGNIFIER AND RESETTING TO LATEST CONFIG
echo -------------------------------------------------
echo

sudo systemctl stop signifier
git pull
source restore-defaults.sh
source update-arduino.sh
source update-monitoring.sh

echo
echo "All done. Please reboot the Signifier to restart the application."
echo
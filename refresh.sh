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

echo All done. Please reboot the Signifier or run `sudo systemctl start signifier` to restart the application.
echo
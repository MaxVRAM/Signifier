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
sudo systemctl start signifier

echo All done. Signifier should be back up shortly...
echo
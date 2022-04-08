#!/bin/bash

echo
echo -------------------------------------------------
echo STOPPING SIGNIFIER AND RESETTING TO LATEST CONFIG
echo -------------------------------------------------
echo

sudo systemctl stop signifier
git pull
restore-defaults.sh
update-arduino.sh
sudo systemctl start signifier

echo All done. Signifier should be back up shortly...
echo
#!/bin/bash

echo
echo "--------------------------------------------------------"
echo "UPDATING OS/SIGNIFIER, RESETTING DEFAULTS, AND REBOOTING"
echo "--------------------------------------------------------"
echo

sudo systemctl stop signifier
git pull
sudo apt update -y
sudo apt upgrade -y
source restore-defaults.sh
source update-arduino.sh
source update-monitoring.sh
sudo /sbin/reboot
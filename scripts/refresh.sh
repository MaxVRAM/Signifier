#!/bin/bash

echo
echo "----------------------------------------------------------"
echo " UPDATING OS/SIGNIFIER, RESETTING DEFAULTS, AND REBOOTING "
echo "----------------------------------------------------------"
echo

if [[ ! -z "${SIG_PATH}" ]]; then
  SIG=$SIG_PATH
else
  if [[ ! -z "${SIGNIFIER}" ]]; then
    SIG=$SIGNIFIER
  else
    SIG="$HOME/Signifier"
  fi
fi

sudo systemctl stop signifier
sudo apt update -y
sudo apt upgrade -y
echo
echo "System up to date."
echo
echo
source $SIG/scripts/update-app.sh
source $SIG/scripts/update-arduino.sh
source $SIG/scripts/restore-defaults.sh
source $SIG/scripts/reboot.sh
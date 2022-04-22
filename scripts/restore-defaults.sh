#!/bin/bash

echo
echo "------------------------------------------------"
echo " UPDATING SIGNIFIER CODE AND RESTORING DEFAULTS "
echo "------------------------------------------------"
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
cp $SIG/sys/config_defaults/* $SIG/cfg/
sudo rm ~/.asoundrc
cp $SIG/sys/.asoundrc ~/
sudo systemctl enable signifier

echo
echo "Signifier settings restored to default."
echo
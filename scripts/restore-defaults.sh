#!/bin/bash

echo
echo ----------------------------------------------
echo "UPDATING SIGNIFIER CODE AND RESTORING DEFAULTS"
echo ----------------------------------------------
echo
sudo systemctl stop signifier
cp sys/config_defaults/* cfg/
sudo rm ~/.asoundrc
cp sys/.asoundrc ~/
sudo systemctl enable signifier
echo
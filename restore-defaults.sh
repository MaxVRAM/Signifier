#!/bin/bash

echo
echo "Updating Signifier code, Arduino, and restoring default settings..."
echo
sudo systemctl stop signifier
cp sys/config_defaults/* cfg/
cp sys/.asoundrc ~/
sudo systemctl enable signifier
echo
echo "Signifier refresh is complete. Please restart Raspberry Pi to complete the update."
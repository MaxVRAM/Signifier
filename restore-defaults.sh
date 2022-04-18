#!/bin/bash

echo
echo "Updating Signifier code and restoring default settings..."
echo
sudo systemctl stop signifier
cp sys/config_defaults/* cfg/
sudo rm ~/.asoundrc
cp sys/.asoundrc ~/
sudo systemctl enable signifier
echo
echo "Signifier refresh is complete. Please restart Raspberry Pi to complete the update."
echo
#!/bin/bash

echo
read -p "WARNING - This will restore Signifier defaults and restart the app. Are you sure? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl stop signifier
    cp sys/config_defaults/* cfg/
    cp sys/.asoundrc ~/
    sudo systemctl enable signifier
    echo
    echo "Signifier refresh is complete. Please restart Raspberry Pi to complete the update."
fi
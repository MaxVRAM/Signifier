#!/bin/bash

echo
read -p "WARNING - This will restore Signifier defaults and restart the app. Are you sure? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp sys/config_defaults/* cfg/
    sudo systemctl restart signifier
fi
echo
#!/bin/bash

echo
echo "--------------------------------------------"
echo " POWERING OFF THE SIGNIFIER/PI IN 5 SECONDS "
echo "--------------------------------------------"
echo

sudo systemctl stop signifier
sleep 5
sudo /sbin/poweroff

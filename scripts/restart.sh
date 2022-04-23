#!/bin/bash

echo
echo "-------------------------------------------"
echo " RESTARTING SIGNIFIER SERVICE IN 5 SECONDS "
echo "-------------------------------------------"
echo

sleep 5
sudo systemctl restart signifier

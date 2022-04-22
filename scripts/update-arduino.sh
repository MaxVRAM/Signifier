#!/bin/bash

echo
echo "-------------------------------------------------------"
echo "COMPILING LATEST ARDUINO CODE AND PUSHING TO ARDUINO..."
echo "-------------------------------------------------------"
echo


source ~/.profile
SKETCH="$SIGNIFIER/src/sig_led"
sudo systemctl stop signifier
arduino-cli compile -b arduino:megaavr:nona4809 $SKETCH
arduino-cli upload -p /dev/ttyACM0 -b arduino:megaavr:nona4809 -v $SKETCH
if [ $? -eq 0 ]
then 
  echo "Arduino now up to date!"
  echo
  exit 0
else 
  echo "Could not upload sketch. Try again with Arduino connected"
  echo
  exit 1
fi

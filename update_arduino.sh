#!/bin/bash

echo
echo -------------------------------------------------------
echo     Compiling Arduino sketch and pushing to Arudino
echo -------------------------------------------------------
echo
shopt -s expand_aliases
source ~/.aliases
SKETCH="$SIGNIFIER/src/sig_led"
acompile $SKETCH
aupload $SKETCH -v
if [ $? -eq 0 ]
then 
  echo "Arduino now up to date!" 
else 
  echo "Could not upload sketch. Try again with Arduino connected"
fi
echo
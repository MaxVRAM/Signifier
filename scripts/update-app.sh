#!/bin/bash

echo
echo "-------------------------------"
echo " PULLING LATEST SIGNIFIER CODE "
echo "-------------------------------"
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

echo "Pulling latest Signifier code into $SIG"
echo
git -C $SIG pull
echo
echo "Signifier up to date!"
echo
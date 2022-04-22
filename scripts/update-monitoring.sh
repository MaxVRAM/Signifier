#!/bin/bash

echo
echo "---------------------------------------"
echo " MANUALLY BRINING UP DOCKER CONTAINERS "
echo "---------------------------------------"
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

BASE_PATH="$SIG/docker"
docker compose -f "$BASE_PATH/portainer/docker-compose.yaml" up -d
docker compose -f "$BASE_PATH/metrics/docker-compose.yaml" up -d
if [ $? -eq 0 ]
then 
  echo "Docker management and monitoring containers now online!"
  echo
  exit 0
else 
  echo "Could not bring up Docker containers. Please restart and run '$SIG/scripts/update-monitoring.sh'."
  echo
  exit 1
fi

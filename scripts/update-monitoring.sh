#!/bin/bash

echo
echo -------------------------------------------------------
echo         Manually bringing Docker containers up
echo -------------------------------------------------------
echo
shopt -s expand_aliases
source ~/.aliases
BASE_PATH="$SIGNIFIER/docker"
docker compose -f "$BASE_PATH/portainer/docker-compose.yaml" up -d
docker compose -f "$BASE_PATH/metrics/docker-compose.yaml" up -d
if [ $? -eq 0 ]
then 
  echo "Docker management and monitoring containers now online!"
  echo
  exit 0
else 
  echo "Could not bring up Docker containers. Please restart and run '$SIGNIFIER/scripts/update-monitoring.sh'."
  echo
  exit 1
fi
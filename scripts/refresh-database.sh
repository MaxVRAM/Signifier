#!/bin/bash

echo
echo "-------------------------------------------------------"
echo " PRUNING EXISTING METRICS AND RESTARTING METRICS STACK "
echo "-------------------------------------------------------"
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
docker compose -f "$BASE_PATH/metrics/docker-compose.yaml" down
docker volume prune -f
docker compose -f "$BASE_PATH/metrics/docker-compose.yaml" up -d

echo
echo "Done."
echo
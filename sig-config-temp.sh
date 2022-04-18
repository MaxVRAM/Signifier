#!/bin/bash

echo
echo Updating Sig-Config Interface service...
CUSTOM_ENV=$HOME/.signifier
SERVICE_TEMP=$HOME/sig-config.service
cp "$SIGNIFIER/sys/sig-config.service" $SERVICE_TEMP
FLASK_EXEC="ExecStart=/home/pi/.local/bin/flask run --host=0.0.0.0"
sed -i "/ExecStart=/c\\$FLASK_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIGNIFIER" $SERVICE_TEMP
sed -i "/EnvironmentFile=/c\\EnvironmentFile=$CUSTOM_ENV" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/sig-config.service
rm $SERVICE_TEMP
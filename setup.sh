#!/bin/bash

echo
echo -------------------------------------------------------
echo            Starting Signifier installation
echo -------------------------------------------------------
echo
echo "Before we start. Make sure you have:"
echo " 1. Copied `/sig-content` folder to the SD card's boot drive."
echo " 2. The Signifier Arduino is connected (if you want to update it)."
echo " 3. This device has internet access."
echo
echo "Abort the process using [CTRL-C]. It may bugger up installation."
echo
read -p "Ready to roll? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    exit 0
fi

sudo systemctl stop signifier
sudo systemctl stop sig-config
export HOSTNAME
SIG_PATH="$PWD"
SCRIPT_PATH=$SIG_PATH/scripts
MEDIA_DIR=$SIG_PATH/media/audio
BOOT_DIR="/boot/sig-content"
echo Installing Signifier from [$SIG_PATH] on [$HOSTNAME]...
echo

OPTION_SIG_SERVICE=true
OPTION_WEB_SERVICE=true
OPTION_VPN_SERVICE=true
OPTION_DL_VPN_CRED=true
OPTION_DL_WIFI_CFG=true
OPTION_DL_AUDIO=true
OPTION_UPDATE_ARDUINO=true
OPTION_REBOOT=true

if [ ! -d "$MEDIA_DIR" ]; then
    mkdir -p $MEDIA_DIR
fi

echo
echo "Checking if $BOOT_DIR directory exists..."
if [ ! -d "$BOOT_DIR" ]; then
    echo "Cannot find $BOOT_DIR, make sure to copy the content when you burn the Signifier image."
    echo
else
    echo "Grabbing VPN and WiFi config from /boot/sig-content directory..."
    echo
    sudo cp -r /boot/sig-content ~/
    sudo chown -R pi:pi ~/sig-content
    sudo chmod -x ~/sig-content/*
    sudo cp ~/sig-content/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
    sudo cp $SIG_PATH/sys/config.txt /boot/config.txt
fi

read -p "Download Signifier audio library? (you need connection to the Sig-Net VPN) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    OPTION_DL_AUDIO=true
else
    OPTION_DL_AUDIO=false
fi


# Clean up existing system services and permissions
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python`)
echo

echo Applying environment variables...

# Apply aliases for easy development
FILE=$HOME/.aliases
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
else
    touch $FILE
fi
LINE=$'\n# SIGNIFIER ALIASES'
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE="alias amonitor=\"arduino-cli monitor -p /dev/ttyACM0 -b arduino:megaavr:nona4809 -c baudrate=38400\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE="alias acompile=\"arduino-cli compile -b arduino:megaavr:nona4809\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE="alias aupload=\"arduino-cli upload -p /dev/ttyACM0 -b arduino:megaavr:nona4809\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"


# Apply environment variables to user's .profile for interactive sessions
# Also apply the environment variables to a .signifier.env file for non-interactive sessions
FILE=$HOME/.profile
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
else
    touch $FILE
fi

LINE='# SIGNIFIER ENVIRONMENT VARIABLES'
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

LINE="export PATH=\"\$HOME/.local/bin:\$PATH\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE="export PATH=\"\$HOME/Arduino:\$PATH\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

CUSTOM_ENV=$HOME/.signifier
rm $CUSTOM_ENV
touch $CUSTOM_ENV

LINE=$"HOST=\"$HOSTNAME\""
echo "$LINE" >> "$CUSTOM_ENV"
grep -qF -- "export $LINE" "$FILE" || echo "export $LINE" >> "$FILE"

LINE=$"SIGNIFIER=\"$SIG_PATH\""
echo "$LINE" >> "$CUSTOM_ENV"
grep -qF -- "export $LINE" "$FILE" || echo "export $LINE" >> "$FILE"

LINE=$"FLASK_APP=\"$SIG_PATH/site/app.py\""
echo "$LINE" >> "$CUSTOM_ENV"
grep -qF -- "export $LINE" "$FILE" || echo "export $LINE" >> "$FILE"

LINE=$"FLASK_ENV=\"development\""
echo "$LINE" >> "$CUSTOM_ENV"
grep -qF -- "export $LINE" "$FILE" || echo "export $LINE" >> "$FILE"

LINE=$"source $HOME/.aliases"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

source ~/.profile
echo

# Allow install user to run "sudo reboot" without password
FILE=/etc/sudoers
if [ -f "$FILE" ]; then
    sudo tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="$USER ALL=NOPASSWD: /sbin/reboot /sbin/poweroff"
sudo grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"


# Create Signifier config JSON files from defaults if they don't exist
CONFIG_PATH=$SIG_PATH/cfg
DEFAULTS_PATH=$SIG_PATH/sys/config_defaults

echo "Creating/overwriting default files"
if [ ! -d "$CONFIG_PATH" ]; then
    mkdir -p $CONFIG_PATH
fi
cp sys/config_defaults/* cfg/

echo
echo Updating Signifier startup service...
SERVICE_TEMP=$HOME/signifier.service
cp "$SIG_PATH/sys/signifier.service" $SERVICE_TEMP
PYTHON_EXEC="ExecStart=/usr/bin/python $SIG_PATH/signifier.py"
sed -i "/ExecStart=/c\\$PYTHON_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIG_PATH" $SERVICE_TEMP
sed -i "/EnvironmentFile=/c\\EnvironmentFile=$CUSTOM_ENV" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/signifier.service
rm $SERVICE_TEMP

echo
echo Updating Sig-Config Interface service...
SERVICE_TEMP=$HOME/sig-config.service
cp "$SIG_PATH/sys/sig-config.service" $SERVICE_TEMP
FLASK_EXEC="ExecStart=/home/pi/.local/bin/flask run --host=0.0.0.0"
sed -i "/ExecStart=/c\\$FLASK_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIG_PATH" $SERVICE_TEMP
sed -i "/EnvironmentFile=/c\\EnvironmentFile=$CUSTOM_ENV" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/sig-config.service
rm $SERVICE_TEMP

echo
sudo systemctl enable signifier
sudo systemctl enable sig-config

echo
echo Updating system...
sudo apt update
sudo apt upgrade -y

echo
echo Installing system packages...
sudo apt install -y ufw python3-pip alsa-utils libasound2-dev

echo
echo Configuring firewall...
sudo ufw allow 22,80,443,9001,9090,9091,9092,9100,5000,3000/tcp
sudo ufw --force enable

echo
echo Installing Python modules...
python -m pip install -U --no-input -r requirements.txt

echo
echo Setting up audio environment...
sudo rm ~/.asoundrc
cp $SIG_PATH/sys/.asoundrc ~/
sudo modprobe snd-aloop
sudo dtc -I dts -O dtb -o /boot/overlays/disable_hdmi_audio.dtbo $SIG_PATH/sys/disable_hdmi_audio.dts

echo
FILE=/boot/config.txt
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || sudo echo >> $FILE
fi
LINE="dtoverlay=disable_hdmi_audio"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"

FILE=/etc/modules-load.d/modules.conf
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || sudo echo >> $FILE
fi
LINE="snd_aloop"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"

FILE=/etc/modprobe.d/alsa-base.conf
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || sudo echo >> $FILE
fi
LINE="options snd_bcm2835 index=0"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
LINE="options snd_aloop index=1"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
echo


if ! command -v openvpn &> /dev/null
then
    echo "Installing OpenVPN client..."
    sudo apt install openvpn -y
else
    echo "OpenVPN already installed, skipping."
fi

echo
VPN_PATH=/etc/openvpn
if [ ! -d "$VPN_PATH" ]; then
    sudo mkdir -p $VPN_PATH
    sudo chown root:root $VPN_PATH
    sudo chmod 700 $VPN_PATH
fi

echo
VPN_FILE=$(find $HOME -name "$HOSTNAME.ovpn" | sed -n 1p)
if [ -f "$VPN_FILE" ]; then
    echo "Found VPN credentials: $VPN_FILE. Adding to OpenVPN..."
    sudo chmod 700 $VPN_FILE
    sudo mv $VPN_FILE $VPN_PATH/client.conf
    #sudo rm $VPN_FILE
else
    if [ ! -f $VPN_PATH/client.conf ]; then
        echo "VPN credentials not found! Add manually after installation and run setup script again."
    fi
fi
echo

echo
echo "Enabling VPN service and attempting to establish connection..."
if [[ $OPTION_VPN_SERVICE != "false" ]]; then
   sudo systemctl enable openvpn@client.service
   sudo systemctl start openvpn@client.service
fi

echo
if [[ $OPTION_DL_AUDIO != "false" ]]; then
    echo "Sleeping for 5 seconds before attempting to download content via VPN..."
    sleep 5
    echo "Downloading audio library from Sig-Net VPN server..."
    scp -r -P 14444 signifier@192.168.30.10:~/sig-sounds/* $MEDIA_DIR
    echo
fi

echo
if ! command -v arduino-cli &> /dev/null
then
    echo "Installing Arduino-CLI in ${ARDUINO_PATH}..."
    ARDUINO_PATH="$HOME/Arduino"
    mkdir $ARDUINO_PATH
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=$ARDUINO_PATH sh
else
    echo "Arduino-CLI already installed, skipping."
fi
arduino-cli core download arduino:megaavr
arduino-cli core install arduino:megaavr
arduino-cli lib install FastLED
arduino-cli lib install SerialTransfer

echo
if [[ $OPTION_UPDATE_ARDUINO != "false" ]]; then
    source $SCRIPT_PATH/update-arduino.sh
fi

echo
if ! command -v docker &> /dev/null
then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o $SIG_PATH/get-docker.sh
    chmod +x $SIG_PATH/get-docker.sh
    sudo $SIG_PATH/get-docker.sh sh
    sudo usermod -aG docker $USER
else
    echo "Docker already installed, skipping."
fi

echo
FILE=$HOME/.docker/cli-plugins/docker-compose
if [ ! -f "$FILE" ]; then
    echo "Installing Docker Compose..."
    curl -sL https://github.com/docker/compose/releases/download/v2.2.3/docker-compose-linux-aarch64 -o $FILE --create-dirs
    chmod 755 $FILE
    docker compose version
else
    echo "Docker Compose already installed, skipping."
fi
echo

echo
source $SCRIPT_PATH/update-monitoring.sh

FILE=$SIG_PATH/get-docker.sh
if [ -f "$FILE" ]; then
    rm $FILE
fi

echo
if [ ! -d "$MEDIA_DIR" ]; then
    echo "Audio directory not found! Add audio assets into $MEDIA_DIR after installation."
    mkdir -p $MEDIA_DIR
else
    COLL_COUNT=$(find $MEDIA_DIR -maxdepth 1 -type d | wc -l)
    CLIP_COUNT=$(find $MEDIA_DIR -maxdepth 2 -name '*.wav' | wc -l)

    if [[ "$COLL_COUNT" -eq 1 ]]
    then
        echo "No audio collection found!"
        echo "Add audio assets into $MEDIA_DIR after installation."
    else
        if [[ "$COLL_COUNT" > 0 ]]
        then
            echo "[$COLL_COUNT] audio collections found with $CLIP_COUNT audio file(s)."
        else
            echo "No audio files found!"
            echo "Add audio assets into $MEDIA_DIR after installation."
        fi
    fi
fi

echo
if [ -d "~/sig-content" ]; then
    sudo rm -fr ~/sig-content
fi

echo
if [[ $OPTION_REBOOT != "false" ]]; then
    echo "Done! Rebooting in 5 seconds..."
    sleep 5
    sudo reboot
fi

echo
echo -------------------------------------------------------
echo Done! Please reboot to complete Signifier installation.
echo -------------------------------------------------------
echo

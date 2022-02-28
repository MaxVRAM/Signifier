#!/bin/bash

echo
echo -------------------------------------------------------
echo            Starting Signifier installation
echo -------------------------------------------------------
export HOSTNAME
SIG_PATH="$PWD"
MEDIA_DIR=$SIG_PATH/media/audio
echo Installing Signifier from [$SIG_PATH] on [$HOSTNAME]...
echo

OPTION_SIG_SERVICE=true
OPTION_WEB_SERVICE=true
OPTION_DL_VPN_CRED=true
OPTION_DL_WIFI_CFG=true
OPTION_DL_AUDIO=true
OPTION_UPDATE_ARDUINO=true
OPTION_ENABLE_VPN=true
OPTION_REBOOT=true

read -p "Enable Signifier auto-start on boot? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_SIG_SERVICE=false
fi
read -p "Enable Signifier configuration web-app auto-start on boot? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_WEB_SERVICE=false
fi
read -p "Download new VPN credentials from server? (requires password) [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_DL_VPN_CRED=false
fi
read -p "Download new WiFi credentials from server? (requires password) [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_DL_WIFI_CFG=false
fi
read -p "Download latest audio library from server? (requires password) [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_DL_AUDIO=false
fi
read -p "Compile and push latest LED code to Arduino (Arduino must be connected)? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_UPDATE_ARDUINO=false
fi
read -p "Enable VPN connection auto-start on boot? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_ENABLE_VPN=false
fi
read -p "The Signifier must reboot before running. Should it reboot immediately after setup? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]
then
    OPTION_REBOOT=false
fi



sudo systemctl stop signifier
sudo systemctl disable signifier
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python`)
echo

echo Applying environment variables...
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
LINE=$"export HOST=\"$HOSTNAME\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE=$"export SIGNIFIER=\"$SIG_PATH\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE=$"export FLASK_APP=\"$SIG_PATH/site/app.py\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE=$"export FLASK_ENV=\"development\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

LINE=$"source $HOME/.aliases"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

source ~/.profile
echo


FILE=/etc/sudoers
if [ -f "$FILE" ]; then
    sudo tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="$USER ALL=NOPASSWD: /sbin/reboot"
sudo grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"



CONFIG_PATH=$SIG_PATH/cfg
DEFAULTS_PATH=$SIG_PATH/sys/config_defaults
if [ ! -d "$CONFIG_PATH" ]; then
    mkdir -p $CONFIG_PATH
fi
FILE="config.json"
if [ ! -f "$CONFIG_PATH/$FILE" ]; then
    echo "Creating default $FILE"
    cp $DEFAULTS_PATH/$FILE $CONFIG_PATH/$FILE
fi
FILE="values.json"
if [ ! -f "$CONFIG_PATH/$FILE" ]; then
    echo "Creating default $FILE"
    cp $DEFAULTS_PATH/$FILE $CONFIG_PATH/$FILE
fi
FILE="rules.json"
if [ ! -f "$CONFIG_PATH/$FILE" ]; then
    echo "Creating default $FILE"
    cp $DEFAULTS_PATH/$FILE $CONFIG_PATH/$FILE
fi

echo
echo Updating Signifier startup service...
SERVICE_TEMP=$HOME/signifier.service
cp "$SIG_PATH/sys/signifier.service" $SERVICE_TEMP
PYTHON_EXEC="ExecStart=/usr/bin/python $SIG_PATH/signifier.py"
sed -i "/ExecStart=/c\\$PYTHON_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIG_PATH" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/signifier.service
rm $SERVICE_TEMP

echo
echo Updating Sig-Config Interface service...
SERVICE_TEMP=$HOME/sig-config.service
cp "$SIG_PATH/sys/sig-config.service" $SERVICE_TEMP
EXEC_COMMAND="ExecStart=flask run"
sed -i "/ExecStart=/c\\$PYTHON_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIG_PATH" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/sig-config.service
rm $SERVICE_TEMP


if [[ $OPTION_SIG_SERVICE = "true" ]]; then
    sudo systemctl enable signifier
fi
if [[ $OPTION_WEB_SERVICE = "true" ]]; then
    sudo systemctl enable signifier
fi
if [[ $OPTION_DL_VPN_CRED = "true" ]]; then
    scp -P 14444 signifier@192.168.30.10:~/sig-config/${HOSTNAME}.ovpn ~/
fi
if [[ $OPTION_DL_WIFI_CFG = "true" ]]; then
    scp -P 14444 signifier@192.168.30.10:~/sig-config/wpa_supplicant.conf ~/
    sudo cp ~/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
    rm ~/wpa_supplicant.conf
fi
if [[ $OPTION_DL_AUDIO = "true" ]]; then
    scp -r -P 14444 signifier@192.168.30.10:~/sig-sounds/* $MEDIA_DIR
fi


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

if ! command -v openvpn &> /dev/null
then
    echo "Installing OpenVPN client..."
    sudo apt install openvpn -y
else
    echo "OpenVPN already installed, skipping."
fi

VPN_PATH=/etc/openvpn
if [ ! -d "$VPN_PATH" ]; then
    sudo mkdir -p $VPN_PATH
    sudo chown root:root $VPN_PATH
    sudo chmod 700 $VPN_PATH
fi


VPN_FILE=$(find $HOME -name "$HOSTNAME.ovpn" | sed -n 1p)
if [ -f "$VPN_FILE" ]; then
    echo "Found VPN credentials: $VPN_FILE. Adding to OpenVPN..."
    sudo chmod 700 $VPN_FILE
    sudo cp $VPN_FILE $VPN_PATH/client.conf
    sudo rm $VPN_FILE
    # sudo openvpn --config /etc/openvpn/client/client.ovpn --daemon
    # sudo cp /etc/openvpn/client/client.ovpn /etc/openvpn/client.conf
else
    if [ ! -f $VPN_PATH/client.conf ]; then
        echo "VPN credentials not found! Add manually after installation and run setup script again."
    # else
        # sudo openvpn --config /etc/openvpn/client/client.ovpn --daemon
    fi
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


if [[ $OPTION_WEB_SERVICE = "true" ]]; then
    source update-arduino.sh
fi

echo Setting up audio environment...
sudo cp $SIG_PATH/sys/.asoundrc ~/
sudo modprobe snd-aloop
sudo dtc -I dts -O dtb -o /boot/overlays/disable_hdmi_audio.dtbo $SIG_PATH/sys/disable_hdmi_audio.dts

FILE=/boot/config.txt
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="dtoverlay=disable_hdmi_audio"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"

FILE=/etc/modules-load.d/modules.conf
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="snd_aloop"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"

FILE=/etc/modprobe.d/alsa-base.conf
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="options snd_bcm2835 index=0"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
LINE="options snd_aloop index=1"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
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

source docker-up.sh


FILE=$SIG_PATH/get-docker.sh
if [ -f "$FILE" ]; then
    rm $FILE
fi

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

if [[ $OPTION_ENABLE_VPN = "true" ]]; then
   sudo systemctl enable openvpn@client.service
fi



if [[ $OPTION_REBOOT = "true" ]]; then
    echo "Done! Rebooting in 5 seconds..."
    sleep 5
   sudo reboot
fi

echo -------------------------------------------------------
echo Done! Please reboot to complete Signifier installation.
echo -------------------------------------------------------
echo

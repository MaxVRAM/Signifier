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

sudo systemctl stop signifier
sudo systemctl disable signifier
echo

read -p "Get a VPN certificate from the SigNet server? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    scp -P 14444 signifier@192.168.30.10:~/ovpns/${HOSTNAME}.ovpn ~/
fi

read -p "Download audio files from server? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    scp -r -P 14444 signifier@192.168.30.10:~/sig-sounds $MEDIA_DIR
fi

echo "Updating system..."
sudo apt update
sudo apt upgrade -y
echo

if ! command -v openvpn &> /dev/null
then
    echo "Installing OpenVPN client..."
    sudo apt install openvpn -y
    mkdir -p /etc/openvpn/client
    chown root:root /etc/openvpn/client
    chmod 700 /etc/openvpn/client
else
    echo "OpenVPN already installed, skipping."
fi

VPN_FILE=$(find $HOME -name "$HOSTNAME.ovpn" | sed -n 1p)
if [ -f "$VPN_FILE" ]; then
    echo "Found VPN credentials: $VPN_FILE. Adding to OpenVPN..."
    sudo cp $VPN_FILE $HOME/client.ovpn
    VPN_FILE=$HOME/client.ovpn
    sudo chown root:root $VPN_FILE
    sudo chmod 700 $VPN_FILE
    sudo mv $VPN_FILE /etc/openvpn/client
    sudo openvpn --config /etc/openvpn/client/client.ovpn --daemon
    sudo cp /etc/openvpn/client/client.ovpn /etc/openvpn/client.conf
    sudo systemctl enable openvpn@client.service
    sudo systemctl start openvpn@client.service
else
    if [ -f /etc/openvpn/client/client.ovpn ]; then
        sudo openvpn --config /etc/openvpn/client/client.ovpn --daemon
        sudo systemctl enable openvpn@client.service
        sudo systemctl start openvpn@client.service
    else
        echo "VPN credentials not found! Obtain from VPN server and add manually after installation."
    fi
fi
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
LINE=$"export FLASK_APP=\"$SIG_PATH/signifier.py\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
LINE=$"export FLASK_ENV=\"development\""
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

LINE=$"source $HOME/.aliases"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

source $HOME/.profile
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
acompile ~/$SIG_PATH/src/sig_led && aupload ~/$SIG_PATH/src/sig_led -v
echo

echo Setting up audio environment...
cp $SIG_PATH/sys/.asoundrc ~/
sudo modprobe snd-aloop
sudo modprobe snd_pcm_oss
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
LINE="snd_pcm_oss"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"

FILE=/etc/modprobe.d/alsa-base.conf
if [ -f "$FILE" ]; then
    tail -c1 $FILE | read -r _ || echo >> $FILE
fi
LINE="options snd_bcm2835 index=0"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
LINE="options snd_aloop index=1"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
LINE="options snd_pcm_oss index=2"
grep -qF -- "$LINE" "$FILE" || echo "$LINE" | sudo tee -a "$FILE"
echo

sudo systemctl stop bluetooth
sudo systemctl disable bluetooth
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python`)
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

if ! command -v docker &> /dev/null
then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o $SIG_PATH/get-docker.sh
    chmod +x $SIG_PATH/get-docker.sh
    sudo $SIG_PATH/get-docker.sh sh
    if [ -d "$SIG_PATH/get-docker.sh" ]; then
        rm $SIG_PATH/get-docker.sh
    fi
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
docker compose -f "$SIG_PATH/docker/portainer/docker-compose.yaml" up -d
docker compose -f "$SIG_PATH/docker/metrics/docker-compose.yaml" up -d
echo

echo Enabling Signifier startup service...
SERVICE_TEMP=$HOME/signifier.service
cp "$SIG_PATH/sys/signifier.service" $SERVICE_TEMP
PYTHON_EXEC="ExecStart=/usr/bin/python $SIG_PATH/signifier.py"
sed -i "/ExecStart=/c\\$PYTHON_EXEC" $SERVICE_TEMP
sed -i "/User=/c\\User=$USER" $SERVICE_TEMP
sed -i "/WorkingDirectory=/c\\WorkingDirectory=$SIG_PATH" $SERVICE_TEMP
sudo cp $SERVICE_TEMP /etc/systemd/system/signifier.service
rm $SERVICE_TEMP

sudo systemctl enable signifier
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


read -p "Push latest Arduino code? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    source update-arduino.sh
fi


echo -------------------------------------------------------
echo Done! Please reboot to complete Signifier installation.
echo -------------------------------------------------------
echo

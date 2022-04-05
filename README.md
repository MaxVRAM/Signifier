
# MMW Signifier

> "Signifier" is comprehensive platform to run the interactive sound & light sculpture on Raspberry Pi 4. Each of the 15 Signifiers allow user interactive through integrated Bluetooth scanning, and microphone input analysis, which shapes the interactive audio composition and LED reactivity. Created by Chris Vik in collaboration with [office.org.au](https://office.org.au) for Melbourne Music Week 2021/2022.

![Signifier image](/doc/1280x640_signifier_test.jpg "Signifier image")

Each of the 15 Signifiers use a **Raspberry Pi 4B (4GB)** fitted with several hardware devices to provide interaction with the physical world.

This application manages a suite sensor input modules, **sources**, and output modules, **destinations**. A Signifier's behaviour is customisable via a scheduler and value mapping system, which allow total control over the automation and interaction between inputs and outputs, even during run-time.

## Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=2 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Contents](#contents)
- [Project features](#project-features)
  - [Codebase](#codebase)
  - [Hardware integration](#hardware-integration)
  - [Configuration and management](#configuration-and-management)
  - [Metrics and networking](#metrics-and-networking)
- [Hardware](#hardware)
- [Software](#software)
  - [Core](#core)
  - [System modules](#system-modules)
  - [Python modules](#python-modules)
  - [Docker & containers](#docker-containers)
- [Location](#location)
- [Format](#format)
- [Replacing / adding audio collections](#replacing-adding-audio-collections)
- [Option 1: SD card duplication](#option-1-sd-card-duplication)
- [Option 2: Install script](#option-2-install-script)
- [Method 1: Browser accesss](#method-1-browser-accesss)
  - [Sig-Config](#sig-config)
  - [Grafana](#grafana)
  - [Prometheus/Metrics Push Gateway](#prometheusmetrics-push-gateway)
- [Method 2: SSH](#method-2-ssh)
  - [Signifier Scripts](#signifier-scripts)
  - [Signifier Services](#signifier-services)
  - [General OS Commands](#general-os-commands)
- [Method 3: Physical access](#method-3-physical-access)

<!-- /code_chunk_output -->


## Project features

### Codebase

- Full multi-processor support.
- Automation scheduling manager.
- Source/destination value mapping system.
- Dynamic audio composition playback system.
- Composition output stream audio analysis.

### Hardware integration

- Duplex serial communication with Arduino for real-time LED control.
- Anonymised Bluetooth (BLE) activity scanner metrics.
- Microphone input analysis. (not yet implemented)
- Temperature sensor input. (not yet implemented)

### Configuration and management

- Local configuration serialisation.
- Integrated configuration and event API. (not yet implemented)
- Integrated web-app for convenient config/event API access and basic monitoring. (not yet implemented)
- Docker/Portainer agent for container management from the Signifier Server.

### Metrics and networking

- Local Prometheus push gateway for complete metrics capture.
- Custom VPN networking for secure remote access, during both development and production.
- Prometheus federation server for metrics aggregation.
- Grafana dashboards for real-time monitoring of all metrics.


## Hardware

**Note:** Hardware fit-out was specified and purchased prior to my involvement. I have added notes on sticking-points, work-arounds and incompatibilities with provided hardware.

- **Raspberry Pi 4B** (4GB) - [link](https://au.rs-online.com/web/p/raspberry-pi/1822096)
- **Arduino Nano Every** - [link](https://au.rs-online.com/web/p/arduino/1927590)
- 4m x **RGB LED strips** (WS2812B 60/m) - [link](https://www.jaycar.com.au/2m-rgb-led-strip-with-120-x-addressable-w2812b-rgb-leds-arduino-mcu-compatible-5v/p/XC4390)
  - Why WS2812B LEDs are not a good choice for RPi - [link](https://tutorials-raspberrypi.com/connect-control-raspberry-pi-ws2812-rgb-led-strips/)
  - Basic guide for controlling WS212B with Arduino - [link](https://randomnerdtutorials.com/guide-for-ws2812b-addressable-rgb-led-strip-with-arduino/)
- **Audio amplifier** (50 watt Bluetooth) - [link](https://core-electronics.com.au/digital-bluetooth-power-amplifier-50w-2.html)
  - Issues:
    - Only has Bluetooth or USB connectivity! 3.5mm jack input would be recommended.
    - Produces a loud vocal announcement when they are powered on! No good for a professional installation.
    - Cannot disable Bluetooth, and cannot prevent anyone taking over the input. Terrible for public installations.
- **Digital Temp Sensor** - [link](https://www.altronics.com.au/p/z6386-stainless-steel-housing-waterproof-ds18b20-temperature-probe/)
- **Mini USB Microphone** - [link](https://core-electronics.com.au/mini-usb-microphone.html)
- **NB-IoT Raspberry Pi HAT** - [link](https://core-electronics.com.au/nb-iot-emtc-edge-gprs-gnss-hat-for-raspberry-pi.html)
  - The previous developers were unable to make this module work on the Pi with the other hardware connected.
  - I will test these myself, but may not make it into the final build.
  - Guide on the specific SIM chip - [link](https://support.hologram.io/hc/en-us/articles/360036559494-SIMCOM-SIM7000)
  - Guide on different version, but might still be relavent - [link](https://www.switchdoc.com/2021/05/tutorial-using-cellular-modems-with-the-raspberry-pi-4b/)

## Software

### Core

- **Raspberry Pi OS** - [link](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2022-01-28/) - (Debian Bullseye) 64-bit/arm64
- **Python 3.9**

### System modules
- **libasound2-dev** - [link](https://packages.debian.org/bullseye/libasound2-dev) - Downloads ALSA C-libraries for Python library compilation. (might not be needed, will test without on a new build)
- **alsa-utils** - [link](https://packages.debian.org/bullseye/alsa-utils) - Provides loopback and additional debugging tools.

### Python modules 

- **schedule** - [link](https://pypi.org/project/schedule/) - Required for scheduling "jobs" to automate the Signifier.
- **pygame** - [link](https://pypi.org/project/pygame/) - Back-end framework for audio clip playback.
- **pyAlsaAudio** - [link](https://github.com/larsimmisch/pyalsaaudio) Wrapper for ALSA, required for analysis module.
- **PySerialTransfer** - [link](https://pypi.org/project/pySerialTransfer/) - Arduino communication framework, required for LED module.
- **prometheus-client** - [link](https://pypi.org/project/prometheus-client/) - Required if using Prometheus/Grafana to monitor Signifiers.

### Docker & containers

- **Docker** - [link](https://www.docker.com/) - Container framework
- **Docker Compose** - [link](https://docs.docker.com/compose/) - More convenient method of container management.
- **Portainer Agent** - [link](https://www.portainer.io/) - Remote management of Docker environment.
- **Prometheus** - [link](https://prometheus.io/) - Local time-series database for recording system metrics and sensor data.


---

# Networking

Signifiers will look for the WiFi SSID `mmw_sig_net`, and use the password ~~`redacted`~~.

Once connected, they will automatically attempt connection via VPN. The VPN provides a secure network for the Signifiers to communicate with the Signifier Server, which records metrics, allows for remote SSH access to the Signifiers, and hosts several front-end web-apps for remote monitoring and configuration of the Signifiers.

More information on these systems shortly.

---

# Media content

## Location

All media content for the Signifiers should go into the Signifier application's `/media` subdirectory (default `/home/pi/Signifier/media`). There is a subdirectory called `audio` which should contain the Signifier's audio clip collections.

The default path for audio resources supplied on delivery is here:

```
/home/pi/Signifier/media/audio/
```

There are 11 separate "collections" of Signifier audio presets: `S1`, `S2`... `S11`.

## Format

The expected format for audio content used by the Signifier application is:

- File extension: `.wav`
- Sample rate: `48000`
- Channels: `1` / `mono`
- Bit depth: `16-bit` / `signed 2-byte integer`

While the format of audio clips can be converted in real-time by the application, it uses a large amount of CPU to do so. Supplying the incorrect format will heavily impact performance, and may result in interrupted audio playback and incorrect audio analysis outputs.

## Replacing / adding audio collections

I suggest using the free Windows application FFMpeg Batch AV Converter to convert large quantities of audio files to the desired format. The following conversion command will produce the correct output:

```
-vn -c:a pcm_s16le -sample_fmt s16 -ar 48000 -ac 1
```

Once converted, simply add the folder containing the new collections into the `media/audio` directory, and ensure the `config.json` **collection** `base_path` setting points to the new audio library path. 


---

# Installation

## Option 1: SD card duplication


Use an application like BalenaEtcher to write the supplied Signifier image on to a fresh SD card. This is by far the easiest and quickest method to deploy a new Signifier.

**Note:** Each Signifier should have a unique *hostname* that reflects the assigned letter of its physical component. When duplicating the Signifier image, the hostname should be changed from within the operating system. This is especially important to do if the Signifiers are intended to be deployed in a networked or VPN environment.

## Option 2: Install script

Should the SD card duplication not work, or if you'd like to build the Signifier environment on a fresh environment, you can use the `setup.sh` script supplied in this repository.

On any Windows, OS X, or Linux system:

1. Download the the Raspberry Pi Imager software: <https://www.raspberrypi.com/software/>

2. Open the imager software, select **Raspberry Pi OS (other)** > **Raspberry Pi OS Lite (64-bit)**

3. Chose the SD card from the "Choose Storage" option.

4. Click the gear icon, and complete the following details:

    - **Hostname**:
      - Signifier name format: `mmwSig<letter>`
        - Where `<letter>` is the capital letter of the Signifier being deployed (e.g. "A", "B"... "N"):
        - For example: `mmwSigF`

    - **Enable SSH**:
      - Use password authentication

    - **Set username and password**
      - Username: `pi`
      - Password = **~~redacted~~**

    - **Configure wifi**:
      - SSID = `mmw_sig_net`
      - Password = **~~redacted~~**
      - WiFi country = `AU`

    - **Set locale settings**
    
      - Time zone = `Australia/Victoria`
      - Keyboard  layout = `us`
      - Skip first-run wizard = `checked`

5. Hit `SAVE` then `WRITE`, and wait for the image to finish installing and verifying.

6. Before removing the SD card from the reader, open the newly created drive called `BOOT` from your file explorer.

7. Copy and paste the `sig-contents` directory provided into the root of the SD card's `BOOT` drive. 

8. Remove the SD card from the computer and insert into the RPi, the connect the USB-C power cable.

Now it's time to install the Signifier application on your fresh Raspberry Pi OS:

9. Once the Pi has booted, login using the credentials your provided during installation, with username `pi`.

10. Install the `git` module:

    ```bash
    sudo apt install git
    ```

11. Clone this repo:

    ```bash
    git clone https://github.com/MaxVRAM/Signifier.git && cd Signifier
    ```

12. Execute the install script and follow any prompts:
    ```bash
    ./setup.sh
    ```

    - **NOTE:** The most straight-forward and comprehensive installation option is to enter **yes** to the first two options. This will install and copy/download all content and configure the system for all Signifier functionality. To customise the setup and select individual elements, enter **no** for the second option.

13. After installation, reboot the Raspberry Pi to start the Signifier.

**NOTE:** It's possible that the Signifier monitoring apps could not be installed during the setup.sh procedure. These can be installed by running the `./update-monitoring.sh` command from within the Signifier directory on the Pi.


# Accessing the Signifiers

There are several methods for accessing a Signifier. The method you use will depends on 2 things:

1. What you need to accomplish.
2. What kind of access you have to the Signifier.

There are 3 primary methods of accesss:

## Method 1: Browser accesss

If you're on the same WiFi network (or VPN) as the Signifier, you can access the following web applications hosted on the Signifier via your browser:

| Hostname | Sig-Config              | Grafana                 | Metrics Gateway         |
|----------|-------------------------|-------------------------|-------------------------|
| mmwSigA  | <http://10.8.0.8:5000>  | <http://10.8.0.8:3000>  | <http://10.8.0.8:9091>  |
| mmwSigB  | <http://10.8.0.9:5000>  | <http://10.8.0.9:3000>  | <http://10.8.0.9:9091>  |
| mmwSigC  | <http://10.8.0.10:5000> | <http://10.8.0.10:3000> | <http://10.8.0.10:9091> |
| mmwSigD  | <http://10.8.0.11:5000> | <http://10.8.0.11:3000> | <http://10.8.0.11:9091> |
| mmwSigE  | <http://10.8.0.12:5000> | <http://10.8.0.12:3000> | <http://10.8.0.12:9091> |
| mmwSigF  | <http://10.8.0.13:5000> | <http://10.8.0.13:3000> | <http://10.8.0.13:9091> |
| mmwSigG  | <http://10.8.0.14:5000> | <http://10.8.0.14:3000> | <http://10.8.0.14:9091> |
| mmwSigH  | <http://10.8.0.15:5000> | <http://10.8.0.15:3000> | <http://10.8.0.15:9091> |
| mmwSigI  | <http://10.8.0.16:5000> | <http://10.8.0.16:3000> | <http://10.8.0.16:9091> |
| mmwSigJ  | <http://10.8.0.17:5000> | <http://10.8.0.17:3000> | <http://10.8.0.17:9091> |
| mmwSigK  | <http://10.8.0.18:5000> | <http://10.8.0.18:3000> | <http://10.8.0.18:9091> |
| mmwSigL  | <http://10.8.0.19:5000> | <http://10.8.0.19:3000> | <http://10.8.0.19:9091> |
| mmwSigM  | <http://10.8.0.20:5000> | <http://10.8.0.20:3000> | <http://10.8.0.20:9091> |
| mmwSigN  | <http://10.8.0.21:5000> | <http://10.8.0.21:3000> | <http://10.8.0.21:9091> |
| mmwSigO  | <http://10.8.0.22:5000> | <http://10.8.0.22:3000> | <http://10.8.0.22:9091> |


### Sig-Config

Update the Signifier configuration.

**URL:** `<signifier-ip-address>:5000`

**Functionality:**
  
- Download the current Signifier configuration files.
- Upload new or modified configuration files.
- Restart the Signifier.
- Most Signifier modules will apply updated configurations during runtime without requiring a restart.

### Grafana

View Signifier data graphed on tidy dashboards.

**URL:** `<signifier-ip-address>:3000`

**Functionality:**
  
- Monitor the status of online Signifiers.
- View pretty graphs displaying sensor, composition, LED, and system data.
- Useful when updating Signifier configuration.


### Prometheus/Metrics Push Gateway

Provides the sensor data to Grafana.

**URL:** `<signifier-ip-address>:9091`

**Functionality:**
  
- View latest Signifier data if Grafana is inaccessable.
- Provides an API point for custom applications to ingest Signifier data.

## Method 2: SSH

SSH provides a command line interface (CLI) into the Signifier operating systems (OS). This will provide *essentially* the same functionality as having a mouse and keyboard connected to the Signifier Raspberry Pi from a remote computer, but requires network access to the Signifier.

On OS X platforms, you can follow the commands below from the _Terminal_ app. On Windows, this is available from either Command Line, or PowerShell.

Once in a terminal application on your computer, you can access a Signifier remotely via SSH with the following command:

```bash
ssh pi@<signifier-ip-address>
```

You'll then have to enter the password for the `pi` user of the Signifier (that you provided in the installation steps).

After which, you'll be connected to the Signifier OS CLI.

### Signifier Scripts

- Navigate to the Signifier directory:

  ```bash
  cd ~/Signifier
  ```

- Once in the Signifier directory, you can run the Signifier setup/installation script:
  ```bash
  ./setup.sh
  ```

- Or just update the Signifier code (if it's been updated on GitHub):
  ```bash
  ./update-app.sh
  ```

- Or update a connected Arduino with the latest LED code:
  ```bash
  ./update-arduino.sh
  ```

- Or bring up the Signifier monitoring Docker containers (Grafana and Prometheus):
  ```bash
  ./update-docker.sh
  ```

### Signifier Services

From anywhere in the OS, you can check the status of the Signifier system services. These services are configured during the initial Signifier `setup.sh` process, and try to ensure critical Signifier applications are kept running. Should there be a critical system fault, the service may not be able to maintain the online status of a Signifier application.

- You can check the status of a Signifier service via the following commands:

  - `sudo systemctl status signifier` - status of the Signifier application responsible for the primary Signifier functionality.
  - `sudo systemctl status sig-config` - status of the Sig-Config web-application.
  - `sudo systemctl status openvpn@client.service` - status of the Signifier's access to the Sig-Net VPN.

- If a service returns a `disabled` status, it can be re-enabled using the same command, only replacing `status` with `enable`. For example:

  ```bash
  sudo systemctl enable signifier
  ```
  
- When the system is rebooted, the service should automatically start. The service can be started immediately using the `start` keyword. For example:

  ```bash
  sudo systemctl start signifier
  ```

### General OS Commands

- Reboot the Signifier Raspberry Pi:
  ```bash
  sudo reboot
  ```

- Shutdown the Signifier Raspberry Pi:
  ```bash
  sudo poweroff
  ```

- Test the audio output:
  ```bash
  speaker-test -t wav
  # Use CTRL-C to abort the test at any time.
  ```

## Method 3: Physical access

If you are able to connect a monitor and keyboard (via micro HDMI and USB ports, respectively), you are afforded the same functionality as SSH (explained above), only without the requirement of network access.

This should only be required if the Signifier is inaccessible via SSH, in instances where the Signifier is unable to find a valid WiFi connection, or where the OS is unable to start critical system functionality (for example, if the SD card has been corrupted).

See **Method 2** for examples of functionality in this mode.

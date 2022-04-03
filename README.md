# MMW Signifier

This repository hosts the project for the individual Signifier units. For the Signifier Server code, see the associated repository **(TODO)**.

> "Signifier" is comprehensive platform to run the interactive sound & light sculpture on Raspberry Pi 4. Each of the 15 Signifiers allow user interactive through integrated Bluetooth scanning, and microphone input analysis, which shapes the interactive audio composition and LED reactivity. Created by Chris Vik in collaboration with [office.org.au](https://office.org.au) for Melbourne Music Week 2021/2022.

![Signifier image](/doc/1280x640_signifier_test.jpg "Signifier image")

Each of the 15 Signifiers use a **Raspberry Pi 4B (4GB)** fitted with several hardware devices to provide interaction with the physical world.

This application manages a suite sensor input modules, **sources**, and output modules, **destinations**. A Signifier's behaviour is customisable via a scheduler and value mapping system, which allow total control over the automation and interaction between inputs and outputs, even during run-time.

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

9. Execute the install script and follow any prompts:
    ```bash
    ./setup.sh
    ```

10. After installation, reboot the Raspberry Pi to start the Signifier.

**NOTE: It's possible that the Signifier monitoring apps could not be installed during the setup.sh procedure. These can be installed by running the `./update-monitoring.sh` command from within the Signifier directory on the Pi.


# Accessing the Signifiers

There are several methods for accessing the Signifiers. It depends on what you need to accomplish on them, and what kind of access you have to them (e.g. Can you plug a screen and keyboard into them? Are they only accessible via WiFi? etc..)

....more to go

# Signifier
Python scripts designed for Raspberry Pi 4B to manage sensor inputs, output modulated audio, and send serial messages to an Arduino for controlling RGB LED strips.

## Project targets
1. Reliable **non-interactive** audio and LEDs.
    - [x] Audio playback
    - [x] Generative audio layer composition manager
    - [x] Basic LED modulation
2. **Interactive** audio and non-interactive LEDs.
    - [x] Sensor: Bluetooth
        - [x] Tested 
        - [x] Integrated
    - [x] Sensor: Microphone
        - [x] Tested 
        - [ ] Integrated
    - [ ] Sensor: Temperature
        - [x] Tested 
        - [ ] Integrated
    - [x] Interactive audio manager
        - [x] Tested 
        - [x] Integrated
3. Interactive audio & interactive LEDs
    - [x] Raspberry Pi / Arduino interfacing
        - [x] Tested 
        - [x] Integrated
    - [x] Audio analysis
        - [x] Tested 
        - [x] Integrated
    - [x] Interactive LED manager
        - [x] Tested 
        - [x] Integrated
    - [ ] LED effects suite
        - [x] Tested 
        - [ ] Integrated
4. Network communication over WiFi/cellular to online server:
    - [ ] Simple API control of Signifier manager
    - [ ] Signifier management over WiFi
    - [ ] Writing sensor data to local time-series database
    - [ ] Pushing to remote database
    - [ ] Signifier management over cellular
BONUS ROUND:
    - [ ] Web-socket server on Signifiers
    - [ ] Centralised web-app to monitor and control Signifiers via web-sockets 
    - [ ] Real-time Signifier GPS coordinate map
    - [ ] Data-visualisation of sensor values and Signifier states

## Hardware

- [Raspberry Pi 4B](https://au.rs-online.com/web/p/raspberry-pi/1822096)
- [Arduino Nano Every](https://au.rs-online.com/web/p/arduino/1927590)
- 4m x [RGB LED strips - WS2812B 120p/m](https://www.jaycar.com.au/2m-rgb-led-strip-with-120-x-addressable-w2812b-rgb-leds-arduino-mcu-compatible-5v/p/XC4390)
  - Basic guide for controlling WS212B with Arduino - [link](https://randomnerdtutorials.com/guide-for-ws2812b-addressable-rgb-led-strip-with-arduino/)
  - Why WS2812B LEDs were not a good choice - [link](https://tutorials-raspberrypi.com/connect-control-raspberry-pi-ws2812-rgb-led-strips/)
  - For this reason, instead of driving the LEDs directly from the RPi, we're sending serial commands to an Arduino, connected via USB, with the Arduino library `fastled`.
- [Audio amplifier - 50 watt Bluetooth](https://core-electronics.com.au/digital-bluetooth-power-amplifier-50w-2.html)
  - It's unfortunate the amp doesn't have a 3.5mm jack input, as this would provide more options should there be issues with USB communication.
  - If there are complications with driving so many USB devices off the RPi, we may replace these amps for one with a 3.5mm input.
- [Digital Temp Sensor](https://www.altronics.com.au/p/z6386-stainless-steel-housing-waterproof-ds18b20-temperature-probe/)
- [Mini USB Microphone](https://core-electronics.com.au/mini-usb-microphone.html)
- [NB-IoT Raspberry Pi HAT](https://core-electronics.com.au/nb-iot-emtc-edge-gprs-gnss-hat-for-raspberry-pi.html)
  - Guide on the specific SIM chip - [link](https://support.hologram.io/hc/en-us/articles/360036559494-SIMCOM-SIM7000)
  - Guide on different version, but might still be relavent - [link](https://www.switchdoc.com/2021/05/tutorial-using-cellular-modems-with-the-raspberry-pi-4b/)
  - NOTE: These will likely not make it into the final build, as serial communication conflicts have been observed when running the other devices.

## Software software

### Core functionality

- OS: Raspberry Pi OS Bulleye 64-bit (arm64) - [link](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2021-11-08/)
- Python 3.9

### Monitoring/management:

- Docker/Portainer - local and remote management of additional packages.
- Prometheus - time-series database for local database recording of sensor data.


---

# Deployment: SD card duplication

Use an application like BalenaEtcher to write the supplied Signifier image on to a fresh SD card. This is by far the easiest and quickest method to deploy a new Signifier.

(will add steps later)

# Deployment: Install script

If you'd like to build the Signifier environment on a fresh OS environment, you can use the install script supplied in this repo.

1. Download the zip file of **Raspberry Pi OS Bulleye 64-bit (arm64)** from [here](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2021-11-08/)
2. Write the OS to the SD card with something like BalenaEtcher, insert the SD card into the Signifier and go through the default OS setup on the new image.
3. Clone this repo:
    ```bash
    git clone https://github.com/MaxVRAM/Signifier.git
    cd Signifier
    ```
4. Execute the install script with super user privileges and follow any prompts:
    ```bash
    sudo ./Signifier/install.sh
    ```

# Deployment: Manual installation

Follow **ALL** the steps this guide.

## Audio environment

For the Signifier to run as autonomously as possible, we are going to customise the OS audio environment. Here's a quick breakdown:

1. Install `PortAudio` and `ALSA Utils` system packages to extend our audio super-powers.
2. Disable the pesky and unnessessary HDMI audio devices to keep the environment clean.
3. Create an audio *loopback device* for routing audio between Signifier services.
4. Ensure our audio devices load reliably on system boot with fixed card/device numbers.

Let's go!

### 1. Install audio packages

There's only two packages we need at the moment:
```bash
sudo apt install libportaudio2    # PortAudio, required for LED audio-reactivity.
sudo apt install alsa-utils       # Provides loopback and additional debugging tools.
sudo apt install libasound2-dev   # Downloads ALSA C-libraries for Python library compilation.
sudo apt install python3-pyaudio  # Provides the Python ALSA <> PortAudio integration
```

### 2. Disable HDMI audio devices

> More information: <https://forums.raspberrypi.com/viewtopic.php?t=293672>

Signifiers only need access to the default **Headphones** device (Raspberry Pi's hardware 3.5mm output). But there are two additional audio devices for HDMI audio, **vc4hdmi0** and **vc4hdmi1**, so let's get rid of them.

1. Before we disable anything, let's check out the current state of our system audio devices:
    ```bash
    aplay -l
    ```
    This is the output you should get:
    ```yaml
    **** List of PLAYBACK Hardware Devices ****
    card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
      Subdevice #2: subdevice #2
      Subdevice #3: subdevice #3
      Subdevice #4: subdevice #4
      Subdevice #5: subdevice #5
      Subdevice #6: subdevice #6
      Subdevice #7: subdevice #7
    card 1: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
      Subdevices: 1/1
      Subdevice #0: subdevice #0
    card 2: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
      Subdevices: 1/1
      Subdevice #0: subdevice #0
    ```

2. Let's quickly test the audio output. Plug the Siginfier audio cable (or a pair of headphones) into the Pi's audio output socket and run the ALSA-Utils `speaker-test` utility:
    ```bash
    speaker-test -D Headphones -t wav -c 2
    ```
    - `-D Headphones` defines the PLAYBACK device to test
    - `-t wav` changes the default noise test sound to a voice saying something like "left channel", "right channel".
    - `-c 2` enables the test over both the left and right channels.
    - **NOTE:** One of the channels might not be heard on the Signifier, since it's a mono speaker. Everything is fine as along as one channel is audiable.
3. Aftering confirming that we have sound, we'll now create a *Device Tree Overlay* to disable the HDMI audio devices, they're not needed:
    ```dts
    cat << '_EOF_' > disable_hdmi_audio.dts
    /dts-v1/;
    /plugin/;
    / {
      compatible = "brcm,bcm2835";
      fragment@0 {
        target = <&audio>;
        __overlay__ {
          brcm,disable-hdmi = <1>;
        };
      };
    };
    _EOF_
    ```
4. Compile the overlay:
    ```bash
    sudo dtc -I dts -O dtb -o /boot/overlays/disable_hdmi_audio.dtbo disable_hdmi_audio.dts
    ```
5. Then add it to the Pi's `/boot/config.txt` file so it's apply every boot:
    ```bash
    echo "dtoverlay=disable_hdmi_audio" | sudo tee -a /boot/config.txt
    ```
6. Reboot the system:
    ```bash
    sudo reboot
    ```
7. Now let's have a look at the current state of our audio devices:
    ```bash
    aplay -l
    ```
    ```yaml 
    **** List of PLAYBACK Hardware Devices ****
    card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
      Subdevice #2: subdevice #2
      Subdevice #3: subdevice #3
      Subdevice #4: subdevice #4
      Subdevice #5: subdevice #5
      Subdevice #6: subdevice #6
      Subdevice #7: subdevice #7
    ```
    ```bash
    arecord -l
    ```
    ```yaml
    **** List of CAPTURE Hardware Devices ****
    ```
    A very tidy audio environment to start with!

### 3. Create loopback devices

For audio-reactive LEDs, we need to create a **loopback** device to internally pipe the sound produced by the Signifier's clip manager to the PortAudio Stream module. This module will first analyse the audio stream, then pass it to the Raspberry Pi's hardware **Headphones** audio output device.

1. First, let's check that the loopback utility does what we want it to by creating the loopback device manually:
    ```bash
    sudo modprobe snd-aloop
    ```
2. We should now have PLAYBACK and CAPTURE loopback devices:

    **NOTE:** I've truncated all but 2 subdevices on each device, but there should be 8 for each)

    ```bash
    aplay -l
    ```
    ```yaml
    **** List of PLAYBACK Hardware Devices ****
    card 0: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 0: Loopback [Loopback], device 1: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 1: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    ```
    ```bash
    arecord -l
    ```
    ```yaml
    **** List of CAPTURE Hardware Devices ****
    card 0: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 0: Loopback [Loopback], device 1: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    ```

3. This change is NOT persistent between restarts, so we need to add this to our system `modules` file:
    ```bash
    echo "snd_aloop" | sudo tee -a /etc/modules-load.d/modules.conf
    ```
4. Now let's check the file contents to make sure the module has been added:
    ```bash
    cat /etc/modules-load.d/modules.conf
    ```
    This should output something like this, the import bit to see is `snd_aloop`:
    ```yaml
    # /etc/modules: kernel modules to load at boot time.
    #
    # This file contains the names of kernel modules that should be loaded
    # at boot time, one per line. Lines beginning with "#" are ignored.

    i2c-dev
    snd_aloop
    ```
5. Restart the system and check the audio devices again:
    ```bash
    sudo reboot
    ```
    ```bash
    aplay -l
    ```
    ```yaml
    **** List of PLAYBACK Hardware Devices ****
    card 0: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 0: Loopback [Loopback], device 1: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 1: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    ```
    ```bash
    arecord -l
    ```
    ```yaml
    **** List of CAPTURE Hardware Devices ****
    card 0: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    card 0: Loopback [Loopback], device 1: Loopback PCM [Loopback PCM]
      Subdevices: 8/8
      Subdevice #0: subdevice #0
      Subdevice #1: subdevice #1
    ...
    ```
    **NOTE:** There's one problem here, notice how the **PLAYBACK card number** of the **Headphones** device has changed to **card 1**, when it was originally **card 0**. We don't want to risk any numbers changing, since most of the audio services reference audio device by their card numbers. The next step is to stop that happening...

### 4. Enforce fixed card numbers

> More information: <https://wiki.archlinux.org/title/Advanced_Linux_Sound_Architecture#Configuring_the_index_order_via_kernel_module_options>

1. Print out the audio OS **module** names and their current card numbers:
    ```bash
    cat /proc/asound/modules
    ```
    ```yaml
    0 snd_aloop
    1 snd_bcm2835
    ```
    Ah huh! The `snd_aloop` loopback module has been set to the first module.
2. We can enforce specific card numbers on system boot by creating a config file in `/etc/modprobe.d`, let's call it `alsa-base.conf` and swap the order of those card modules:
    ```bash
    echo "options snd_bcm2835 index=0" | sudo tee -a /etc/modprobe.d/alsa-base.conf
    echo "options snd_aloop index=1" | sudo tee -a /etc/modprobe.d/alsa-base.conf
    ```
3. Double check the contents of our new config file:
    ```bash
    cat /etc/modprobe.d/alsa-base.conf
    ```
    ```conf
    options snd_bcm2835 index=0
    options snd_aloop index=1
    ```
4. Reboot the system, then run a couple of commands to check the order is persistent:
    - First the system modules:
        ```bash
        cat /proc/asound/modules
        ```
        ```yaml
        0 snd_bcm2835
        1 snd_aloop
        ```
    - Nice one! What about the ALSA output?
        ```bash
        aplay -l
        ```
        ```yaml
        **** List of PLAYBACK Hardware Devices ****
        card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
          Subdevices: 8/8
          Subdevice #0: subdevice #0
          Subdevice #1: subdevice #1
        ...
        card 1: Loopback [Loopback], device 0: Loopback PCM [Loopback PCM]
          Subdevices: 8/8
          Subdevice #0: subdevice #0
          Subdevice #1: subdevice #1
        ...
        card 1: Loopback [Loopback], device 1: Loopback PCM [Loopback PCM]
          Subdevices: 8/8
          Subdevice #0: subdevice #0
          Subdevice #1: subdevice #1
        ...
        ```
        Heck yeah! Now when we need to use audio card/device numbers, we can depend on the following:
        - "Headphone" output card/device is (0, 0)
        - "Loopback" virtual card/devices are on (1, 0) and (1, 1)


<!-- OLD INFO!

5. Finally, we'll make a custom ALSA configuration that creates a new audio device called `SpeakerAndLoop`. This will duplicate its audio stream to both the hardware output and loopback device, and sets it as ALSA's default PLAYBACK device. The configuration will also set the second loopback device as the default RECORD device.


    > More information:
       - <https://itectec.com/unixlinux/send-sound-output-to-application-and-speaker/>
       - <https://alsa.opensrc.org/Asoundrc>

    ```bash
    pcm.!default {
      type asym
      playback.pcm "SpeakerAndLoop"
      capture.pcm "hw:1,1"
    }

    ctl.!default {
      type hw
      card 0
    }

    # PLAYBACK and LOOPBACK interface
    pcm.SpeakerAndLoop {
      type plug
      slave.pcm MultiCh
      route_policy "duplicate"
    }

    # Virtual multichannel device:
    # 1 x Headphones channels, 1 x Loopback channels
    pcm.MultiCh {
      type multi
      slaves.a.pcm pcm.MixerHeadphones
      slaves.a.channels 1
      slaves.b.pcm pcm.MixerLoopback
      slaves.b.channels 1
      bindings.0.slave a
      bindings.0.channel 0
      #bindings.1.slave a
      #bindings.1.channel 1
      bindings.1.slave b
      bindings.1.channel 0
      #bindings.3.slave b
      #bindings.3.channel 1
    }

    # Headphones device mixer
    pcm.MixerHeadphones {
      type dmix
      ipc_key 1024
      slave {
        pcm "hw:0,0"
        rate 48000
        periods 128
        period_time 0
        period_size 1024
        buffer_size 4096
      }
    }

    # Loopback device mixer
    pcm.MixerLoopback {
      type dmix
      ipc_key 1025
      slave {
        pcm "hw:1,0"
        rate 48000
        periods 128
        period_time 0
        period_size 1024
        buffer_size 4096
      }
    }
    ```

6. Now reboot, and use `speaker-test` to check that the new device is working:

    ```bash
    speaker-test -D SpeakerAndLoop -t wav -c 2
    ```

    If you're hearing sound from the headphones output, you've successfully created an audio device that sends its audio to other devices: one to the speaker, and one internally for the Signifier's audio analysis module. -->


<!-- 5. The Signifier audio playback engine uses PyGame's mixer module, which relies on SDL for interfacing with the OS' audio systems. We need to set environment variables to tell PyGame which audio device to output from.

    > More information: <https://raspberrypi.stackexchange.com/questions/68127/how-to-change-audio-output-device-for-python>

    ```bash

    ```

5. To add extra redundancy to our audio environment, the Signifier application automatically attempts to use the `default` audio device in the case the one defined in `config.json` is invalid. This can be done by setting the `Headphones` device as ALSA's defaults using environment variables:
    ```bash
    printf '%s\n' 'export ALSA_CARD=Headphones' 'export ALSA_CTL_CARD=Headphones' 'export ALSA_PCM_CARD=Headphones' >> ~/.bashrc
    ```
6. Reload the environment and check that the variables have stuck:
    ```bash
    source ~/.bashrc
    echo $ALSA_CARD $ALSA_CTL_CARD $ALSA_PCM_CARD
    ```
    Which should output:
    ```bash
    Headphones Headphones Headphones
    ``` -->

**We've now completed the audio environment configuration!** To recap what we've done:

- [x] Install required system packages.
- [x] Disable HDMI audio devices.
- [x] Create audio loopback device.
- [x] Assign audio device boot configurations.


---

## Python environment

The OS image we're using comes with `Python 3.9` by default, with Python 3 aliased to both the `python` and `python3` shell commands. You can double check this with `python -V` and `python3 -V`. The Signifier application has only been tested on Python version 3.9.

All required Python modules can be installed using the supplied `requirements.txt` file:

```bash
python -m pip install -r requirements.txt
```

If for some reason only specific modules are required, the can be installed individually:

```bash
pyhton -m pip install schedule          # Required for scheduling "jobs" to automate the Signifier
pyhton -m pip install pygame            # Back-end framework for audio clip playback
pyhton -m pip install sounddevice       # Wrapper for PortAudio, required for audio loopback/analysis
pyhton -m pip install PySerialTransfer  # Arduino communication framework
pyhton -m pip install prometheus-client # Required if using Prometheus/Grafana to monitor Signifiers
```

## Enable Signifier boot script

TODO


The environment is ready to roll!

## Connect devices

1. Power-off the Raspberry Pi, and unplug it's USB-C power cable once it's finished shutting down:
    ```bash
    sudo poweroff
    ```
2. Connect all the Signifier devices:
    - 3.5mm audio cable
    - Arduino USB cable
    - ...
3. Reconnect the USB-C power cable to the Raspberry Pi.

The Signifier should now run as expected!

---

# Questons to respond to on StackOverflow

- Excellent application!!!!
  <https://stackoverflow.com/questions/57099246/set-output-device-for-pygame-mixer>


# Debugging



## Bluetooth


- Using the bleson Python module: <https://bleson.readthedocs.io/en/latest/index.html>

- Recommended to stop the Pi's bluetooth service:

  ```bash
  sudo service bluetooth stop
  ```

- Can use BLE commands without sudo!

  ```bash
  sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
  ```

































## Realtime audio streaming

<https://codeberg.org/rtcqs/rtcqs>

## ALSA Commands

Config file is here:
```bash
sudo nano /usr/share/alsa/alsa.conf
```


```bash
cat /proc/asound/modules
# 0 snd_aloop
# 1 snd_bcm2835
```

```bash
cat /proc/asound/cards
 0 [Loopback       ]: Loopback - Loopback
                      Loopback 1
 1 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones
                      bcm2835 Headphones
```

- A pretty, but basic terminal GUI for inspecting and making changes to the audio device volumes: 

```bash
alsamixer
```

- Print out system sound modules:

  ```bash
  ls -l /dev/snd
  ```

  ```js
  total 0
  drwxr-xr-x  2 root root       80 Jan 26 11:41 by-path
  crw-rw----+ 1 root audio 116,  0 Jan 26 11:41 controlC0
  crw-rw----+ 1 root audio 116, 32 Jan 26 11:41 controlC1
  crw-rw----+ 1 root audio 116, 16 Jan 26 11:41 pcmC0D0p
  crw-rw----+ 1 root audio 116, 56 Jan 26 11:41 pcmC1D0c
  crw-rw----+ 1 root audio 116, 48 Jan 26 12:05 pcmC1D0p
  crw-rw----+ 1 root audio 116, 57 Jan 26 11:41 pcmC1D1c
  crw-rw----+ 1 root audio 116, 49 Jan 26 11:41 pcmC1D1p
  crw-rw----+ 1 root audio 116,  1 Jan 26 11:41 seq
  crw-rw----+ 1 root audio 116, 33 Jan 26 11:41 timer
  ```

- Print out ALSA hardware parameters:

  ```bash
  cat /proc/asound/card1/pcm0p/sub0/hw_params
  ```

  ```yaml
  access: MMAP_INTERLEAVED
  format: S16_LE
  subformat: STD
  channels: 1
  rate: 48000 (48000/1)
  period_size: 96000
  buffer_size: 96000
  ❯ cat /proc/asound/card0/pcm0p/sub0/hw_params
  access: MMAP_INTERLEAVED
  format: S16_LE
  subformat: STD
  channels: 1
  rate: 48000 (48000/1)
  period_size: 65536
  buffer_size: 65536
  ```


- Some interesting stuff here if I need to dig more into ALSA for converting formats: <https://alsa.opensrc.org/Asoundrc>



### Debugging PulseAudio

Runnign speaker output test through loopback....
```bash
speaker-test -c 2 -t wav -D hw:1,0

# speaker-test 1.2.4

# Playback device is hw:1,0
# Stream parameters are 48000Hz, S16_LE, 2 channels
# WAV file(s)
# Rate set to 48000Hz (requested 48000Hz)
# Buffer size range from 16 to 524288
# Period size range from 16 to 262144
# Using max buffer size 524288
# Periods = 4
# was set period_size = 131072
# was set buffer_size = 524288
#  0 - Front Left
#  1 - Front Right
# Time per period = 5.637673
#  0 - Front Left
#  1 - Front Right
```

Works fine, then try to use `sd_loopback_stream.py` to internally pipe the audio and get this error message:

```bash
python tests/sd_loopback_stream.py
# Input and output device must have the same samplerate
```

If I start the processes the other way around, the Python script runs fine, but speaker-test responds with:
```bash
speaker-test -c 2 -t wav -D hw:1,0

# speaker-test 1.2.4

# Playback device is hw:1,0
# Stream parameters are 48000Hz, S16_LE, 2 channels
# WAV file(s)
# Sample format not available for playback: Invalid argument
# Setting of hwparams failed: Invalid argument
```





### Pulse Audio


- Apparently `pi` user should be removed from `audio` group? Not sure if needed:
  > More information: https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/PerfectSetup/
- Python module `sounddevice` was returning errors when utilising `Stream` class. Apparently depends on PyAudio module:
  ```bash
  sudo apt install python3-pyaudio
  ```
- No sound after installing PulseAudio install -> NOTE! I belive masking this socket prevents PulseAudio from loading automatically, need to check:
  > More information: https://retropie.org.uk/forum/topic/28910/making-sound-back-after-december-update-broke-pixel-desktop/3
  ```bash
  systemctl --user mask pulseaudio.socket
  ```
- Menu bar disappears after installing PulseAudio:
  > More information: <https://retropie.org.uk/forum/topic/28910/making-sound-back-after-december-update-broke-pixel-desktop/3>
  ```bash
  sudo apt remove lxplug-volumepulse
  ```
- Create PulseAudio device to feed two audio output devices, called `module-combined-sink`:
  > More information: <https://linuxconfig.org/how-to-enable-multiple-simultaneous-audio-outputs-on-pulseaudio-in-linux>
  
  - Edit the PulseAudio default config file to add new devices:
    ```bash
    sudo nano /etc/pulse/defaults.pa
    ```
    ```ruby
    load-module module-alsa-sink device="hw:0,0" sink_name=audio_jack channels=1 sink_properties="device.description='Audio Jack Output'"
    load-module module-alsa-sink device="hw:1,0" sink_name=loop_send channels=1 sink_properties="device.description='Loop Send'"
    load-module module-alsa-source device="hw:1,1" source_name=loop_return channels=1 source_properties="device.description='Loop Return'"
    load-module module-combine-sink sink_name=combined_output channels=1 slaves=loop_send,audio_jack sink_properties="device.description='Jack And Loop'"
    ```
  - In the same file, comment out these options to prevent devices changing if things are plugged or unplugged:
    ```ruby
    ### Automatically load driver modules depending on the hardware available
    #.ifexists module-udev-detect.so
    #load-module module-udev-detect tsched=0
    #.else
    ### Use the static hardware detection module (for systems that lack udev support)
    #load-module module-detect
    #.endif

    ```
- Helpful PulseAudio service commands:
  ```bash
  systemctl --user status pulseaudio      # Check if the daemon is running for user -- do not run as sudo
  pulseaudio -k                           # Kill PulseAudio service
  pulseaudio --start
  pulseaudio --realtime
  ```
- Excellent example of weighted dB scaling to the sounddevice input stream with Numpy:
  > More information <https://github.com/SiggiGue/pyfilterbank/issues/17>


- PulseAudio not create correct sinks/sources. Ran commands to produce a verbose log:
  > More information: <https://wiki.ubuntu.com/PulseAudio/Log>
  ```bash
  echo autospawn = no >> ~/.config/pulse/client.conf
  killall pulseaudio
  LANG=C pulseaudio -vvvv --log-time=1 > ~/pulseverbose.log 2>&1
  ```
  First few links of PA's log:
  ```yaml
  (   0.000|   0.000) I: [pulseaudio] main.c: setrlimit(RLIMIT_NICE, (31, 31)) failed: Operation not permitted
  (   0.000|   0.000) D: [pulseaudio] core-rtclock.c: Timer slack is set to 50 us.
  (   0.071|   0.071) I: [pulseaudio] core-util.c: Failed to acquire high-priority scheduling: Permission denied
  (   0.071|   0.000) I: [pulseaudio] main.c: This is PulseAudio 14.2
  ```

  > More information: <https://forums.opensuse.org/showthread.php/400774-Pulseaudio-Can-t-get-realtime-or-high-priority-permissions>


SUUUUUPER High CPU usage when using the PulseAudio combined-sink devices. It comepletely maxes out a core. I believe this is because of the no-wait loops in the code. Either way, I need to utilise the 4 cores. Multithreading time!!

Attempting to move to Python `multiprocessing` module. But got error:

```python
DEBUG:signify.audioAnalysis:Starting audio analysis thread...
Expression 'ret' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1736
Expression 'AlsaOpen( &alsaApi->baseHostApiRep, params, streamDir, &self->pcm )' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1904
Expression 'PaAlsaStreamComponent_Initialize( &self->capture, alsaApi, inParams, StreamDirection_In, NULL != callback )' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 2171
Expression 'PaAlsaStream_Initialize( stream, alsaHostApi, inputParameters, outputParameters, sampleRate, framesPerBuffer, callback, streamFlags, userData )' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 2839
Process Audio Analysis Thread:
Traceback (most recent call last):
  File "/usr/lib/python3.9/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/home/pi/Signifier/signify/audioAnalysis.py", line 70, in run
    with sd.InputStream(device='pulse', channels=1, blocksize=2048,
  File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 1415, in __init__
    _StreamBase.__init__(self, kind='input', wrap_callback='array',
  File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 892, in __init__
    _check(_lib.Pa_OpenStream(self._ptr, iparameters, oparameters,
  File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 2741, in _check
    raise PortAudioError(errormsg, err)
sounddevice.PortAudioError: Error opening InputStream: Illegal combination of I/O devices [PaErrorCode -9993]
```

Apparently, this might be caused by the ALSA system integration of the Arduino audio device `snd_bcm2835` failing to process sample rates other than 480000. It's suggested to create an ALSA `plug` device to convert the sample rate: 

> More information <https://github.com/raspberrypi/linux/issues/994#issuecomment-141051047>


The issue appears to be in the source file format! `sounddevice` is a simple wrapper for PulseAudio, and according to the above github issue, PulseAudio has issues converting sample rates. Either way, converting the sample rates on the fly would most certainly add unnessessary CPU time to the system.

- Original audio source files were in 32bit Stereo @ 44.1KHz, but I since the Signifiers are using a single channel, I converted the files to Mono, which I've been using for most of the development.
- Since reading about the realtime sample rate conversion issues between PulseAudio and the snd_bcm2835 ALSA driver, I've moved to **32bit Mono @ 48KHz**
- I batch converted the original files using FFmpeg Batch AV Converter (Windows) and the command: `-vn -c:a pcm_s32le -ar 48000 -sample_fmt s32 -ac 1`
- I also realised (using `sd.query_devices()` on the default output), that PulseAudio defaults to 44.1KHz! So I needed to add some config to `/etc/pulse/daemon.conf`, and added some extra stuff while I was there:

> And more information: <https://forums.linuxmint.com/viewtopic.php?t=44862>

```yaml
allow-module-loading = yes
daemonize = yes

avoid-resampling = true
default-sample-format = s16le
default-sample-rate = 48000
alternate-sample-rate = 48000
default-sample-channels = 1
default-fragments = 4
default-fragment-size-msec = 5

high-priority = yes
nice-level = -11
realtime-scheduling = yes
realtime-priority = 5
```

- It turns out this didn't fix the issue. Looking at the PulseAudio log, it shows all devices being created as 48KHz. However, running `sd.query_devices()` over all the available devices in Python return 44.1KHz. Will attempt this solution:

> More information: <https://unix.stackexchange.com/questions/585789/pulseaudio-detects-wrong-sample-rate-forcing-pulseaudio-a-sample-rate>

> Uncomment and set alternate-sample-rate to 44100 in `/etc/pulse/daemon.conf` (and remove `~/.asoundrc`).

That didn't do anything.

- Attempting to create a custom ALSA devices for pulse audio:

```cs
pcm.pulse_test {
    @args[DEVICE]
    @args.DEVICE {
        type string
        default ""
    }
    type pulse
    device $DEVICE
    hint {
        show {
            @func refer
            name defaults.namehint.basic
        }
        description "TEST PulseAudio Sound Server"
    }
}

ctl.pulse_test {
    @args[DEVICE]
    @args.DEVICE {
        type string
        default ""
    }
    type pulse
    device $DEVICE
}
```

Also did nothing.....


 - So now I'll play with different audio input devices from within `sounddevice` to see if one of them works with the same sample properties....


 - Wait! There's something interesting here. It seems that the PulseAudio combined-sink can't be accessed from `multiprocessing` processes! See this Python I wrote to check which produces the following outputs: `tests/basic_sd_pulse_test.py`...
 
  ```python
  ❯ python tests/basic_sd_pulse_test.py

  Selected input device: {'name': 'Loopback: PCM (hw:1,1)', 'hostapi': 0, 'max_input_channels': 32, 'max_output_channels': 32, 'default_low_input_latency': 0.008707482993197279, 'default_low_output_latency': 0.008707482993197279, 'default_high_input_latency': 0.034829931972789115, 'default_high_output_latency': 0.034829931972789115, 'default_samplerate': 44100.0}


  SoundDevice defaults: [2, 11] [1, 1] ['float32', 'float32'] 44100
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
  Test done.

  Now to test the same function in multiprocessing...

  SoundDevice defaults: [2, 11] [1, 1] ['float32', 'float32'] 44100
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 2, Channels: 1, Dtype: float32, Samplerate: 44100.0
  Test done.

  ❯ python tests/basic_sd_pulse_test.py

  Selected input device: {'name': 'Loopback: PCM (hw:1,1)', 'hostapi': 0, 'max_input_channels': 32, 'max_output_channels': 32, 'default_low_input_latency': 0.008707482993197279, 'default_low_output_latency': 0.008707482993197279, 'default_high_input_latency': 0.034829931972789115, 'default_high_output_latency': 0.034829931972789115, 'default_samplerate': 44100.0}


  SoundDevice defaults: [2, 11] [1, 1] ['int16', 'int16'] 48000
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
  Test done.

  Now to test the same function in multiprocessing...

  SoundDevice defaults: [2, 11] [1, 1] ['int16', 'int16'] 48000
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 2, Channels: 1, Dtype: int16, Samplerate: 48000.0
  Test done.

  ❯ python tests/basic_sd_pulse_test.py

  Selected input device: {'name': 'default', 'hostapi': 0, 'max_input_channels': 32, 'max_output_channels': 32, 'default_low_input_latency': 0.008684807256235827, 'default_low_output_latency': 0.008684807256235827, 'default_high_input_latency': 0.034807256235827665, 'default_high_output_latency': 0.034807256235827665, 'default_samplerate': 44100.0}


  SoundDevice defaults: [11, 11] [1, 1] ['float32', 'float32'] 44100
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 11, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 11, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 11, Channels: 1, Dtype: float32, Samplerate: 44100.0
      Device: 11, Channels: 1, Dtype: float32, Samplerate: 44100.0
  Test done.

  Now to test the same function in multiprocessing...

  SoundDevice defaults: [11, 11] [1, 1] ['float32', 'float32'] 44100
  Expression 'ret' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1736
  Expression 'AlsaOpen( hostApi, parameters, streamDir, &pcm )' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1768
  Process Process-1:
  Traceback (most recent call last):
    File "/usr/lib/python3.9/multiprocessing/process.py", line 315, in _bootstrap
      self.run()
    File "/usr/lib/python3.9/multiprocessing/process.py", line 108, in run
      self._target(*self._args, **self._kwargs)
    File "/home/pi/Signifier/tests/basic_sd_pulse_test.py", line 23, in input_test
      if sd.check_input_settings() is None:
    File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 677, in check_input_settings
      _check(_lib.Pa_IsFormatSupported(parameters, _ffi.NULL, samplerate))
    File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 2741, in _check
      raise PortAudioError(errormsg, err)
  sounddevice.PortAudioError: Illegal combination of I/O devices [PaErrorCode -9993]
  ❯ python tests/basic_sd_pulse_test.py

  Selected input device: {'name': 'default', 'hostapi': 0, 'max_input_channels': 32, 'max_output_channels': 32, 'default_low_input_latency': 0.008684807256235827, 'default_low_output_latency': 0.008684807256235827, 'default_high_input_latency': 0.034807256235827665, 'default_high_output_latency': 0.034807256235827665, 'default_samplerate': 44100.0}


  SoundDevice defaults: [11, 11] [1, 1] ['int16', 'int16'] 48000
  No issues detected by SoundDevice

  Testing outside Process...
      Device: 11, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 11, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 11, Channels: 1, Dtype: int16, Samplerate: 48000.0
      Device: 11, Channels: 1, Dtype: int16, Samplerate: 48000.0
  Test done.

  Now to test the same function in multiprocessing...

  SoundDevice defaults: [11, 11] [1, 1] ['int16', 'int16'] 48000
  Expression 'ret' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1736
  Expression 'AlsaOpen( hostApi, parameters, streamDir, &pcm )' failed in 'src/hostapi/alsa/pa_linux_alsa.c', line: 1768
  Process Process-1:
  Traceback (most recent call last):
    File "/usr/lib/python3.9/multiprocessing/process.py", line 315, in _bootstrap
      self.run()
    File "/usr/lib/python3.9/multiprocessing/process.py", line 108, in run
      self._target(*self._args, **self._kwargs)
    File "/home/pi/Signifier/tests/basic_sd_pulse_test.py", line 23, in input_test
      if sd.check_input_settings() is None:
    File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 677, in check_input_settings
      _check(_lib.Pa_IsFormatSupported(parameters, _ffi.NULL, samplerate))
    File "/home/pi/.local/lib/python3.9/site-packages/sounddevice.py", line 2741, in _check
      raise PortAudioError(errormsg, err)
  sounddevice.PortAudioError: Illegal combination of I/O devices [PaErrorCode -9993]
  ``` 

  So!!! It's NOT a format issue, is somewhere near an issue between `sounddevice`, PulseAudio's `combined-sink` devices and `multiprocessing`.

  I don't think I need to use the combined-sink device in the Python script. I'll just use the loopback return device. Will report back shortly....

 - I tried to use loop the ALSA loopback return `hw:1,1`, which is supposed to be the device that PulseAudio pipes the output audio to (via the `hw:1,0` loopback output device. However, despite the *Loop Return* device metering with the Signifier output signals in PulseAudio's desktop GUI application, the analysis thread doesn't output anything except 0s....

 - There might be some insight within the systemctl logs:

  ```bash
  systemctl --user status pulseaudio
  ```

```yaml
● pulseaudio.service - Sound Service
     Loaded: loaded (/usr/lib/systemd/user/pulseaudio.service; enabled; vendor preset: enabled)
     Active: active (running) since Wed 2022-01-26 14:39:03 AEDT; 1h 50min ago
TriggeredBy: ● pulseaudio.socket
   Main PID: 3204 (pulseaudio)
      Tasks: 8 (limit: 4472)
        CPU: 8min 2.399s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/pulseaudio.service
             └─3204 /usr/bin/pulseaudio --daemonize=no --log-target=journal

Jan 26 14:39:03 sig-dev systemd[610]: Starting Sound Service...
Jan 26 14:39:03 sig-dev systemd[610]: Started Sound Service.
Jan 26 16:14:08 sig-dev pulseaudio[3204]: ALSA woke us up to read new data from the device, but there was actually nothing to read.
Jan 26 16:14:08 sig-dev pulseaudio[3204]: Most likely this is a bug in the ALSA driver 'snd_aloop'. Please report this issue to the ALSA developers.
Jan 26 16:14:08 sig-dev pulseaudio[3204]: We were woken up with POLLIN set -- however a subsequent snd_pcm_avail() returned 0 or another value < min_avail.
```

- Of course! What about using the PulseAudio output device monitors as sources! I didn't know how this would work, but found this potential approach:

  > Source: <https://unix.stackexchange.com/a/636410>

  > "Besides creating the sink, most applications filter out monitor sources. To be able to pick the source directly for example in Google Meet, the module-remap-source helps."

  ```bash
  # create sink
  pactl load-module module-null-sink sink_name=virtmic \
      sink_properties=device.description=Virtual_Microphone_Sink
  # remap the monitor to a new source
  pactl load-module module-remap-source \
      master=virtmic.monitor source_name=virtmic \
      source_properties=device.description=Virtual_Microphone
  ```

  Since I already have the ALSA Headphones output sink setup, why don't I just try to create a monitor source from that?

  ```r
  load-module module-remap-source master=audio_jack.monitor source_name=analysis_source source_properties="device.description='Source fed from Audio Jack output'"
  # ...
  # then at the bottom, change the default source with:
  set-default-source analysis_source
  ```
  Just to be sure we'll remove the user Pulse config cache, then restart the Pulse service:
  ```bash
  rm -rf ~/.config/pulse
  systemctl --user restart pulseaudio
  ```




### Extra stuff

Setting up a system-wide PulseAudio daemon. Could be worth checking this out: <https://rudd-o.com/linux-and-free-software/how-to-make-pulseaudio-run-once-at-boot-for-all-your-users>



## Arduino-CLI

Install
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=~/Arduino sh
```
Note: arudino-cli needs to be run with `./arduino-cli` from the folder the application is stored in, even when the path is added to $PATH. Maybe a mistake on my end. Yup. It was just a dumb $PATH issue on my end. Okay, moving on...

Display connected Arduino board:
```bash
arduino-cli board list

# /dev/ttyACM0   serial   Serial Port (USB) Arduino Nano Every arduino:megaavr:nona4809 arduino:megaavr
```
But we'll need to install a core module to use 

Download, then install the core module for the Arduino Nano Every
```bash
arduino-cli core download arduino:megaavr
arduino-cli core install arduino:megaavr
```

Then check the module is installed:
```bash
./arduino-cli core list

# ID              Installed Latest Name
# arduino:megaavr 1.8.7     1.8.7  Arduino megaAVR Boards
```

Looks good! Now we need to install the libraries:

```bash
./arduino-cli lib install FastLED
./arduino-cli lib install SerialTransfer
```

Another sense-check:
```bash
./arduino-cli lib list

# Name           Installed Available    Location              Description
# FastLED        3.5.0     -            LIBRARY_LOCATION_USER -
# SerialTransfer 3.1.2     -            LIBRARY_LOCATION_USER -
```

The libraries will be installed in `~/Arduino/libraries`. Make sure the VS Code `c_cpp_properties.json` has this path in the `includePath` section. We'll also add the Arduino core library at the same time. This is what mine looks like:

```json
{
    "configurations": [
        {
            "name": "Linux",
            "includePath": [
                "/home/pi/Arduino/libraries/**",
                "/home/pi/.arduino15/packages/arduino/hardware/megaavr/1.8.7/cores/arduino/**"
            ],
            "defines": [],
            "compilerPath": "/usr/bin/gcc",
            "cStandard": "gnu17",
            "cppStandard": "gnu++14",
            "intelliSenseMode": "linux-gcc-arm64"
        }
    ],
    "version": 4
}
```

To check the serial connection with the Arduino, we can run this command:
```bash
arduino-cli monitor -p /dev/ttyACM0 -b arduino:megaavr:nona4809:mode=off
```

You can add an alias to make it quicker to check the Arduino serial outputs when you're developing:
```bash
alias amonitor="arduino-cli monitor -p /dev/ttyACM0 -b arduino:megaavr:nona4809 -c baudrate=38400"
```
No you can just punch in `amonitor` instead.

Note, the alias will disappear when you reboot, so if you want it to stick around, you'll have to add it to your shell's config, e.g `~/.bashrc`, etc.


Next we can get on with building sketches and pushing them to the Arduino. This is what the commands look like with my development environment using an Arduino Nano Every:

```bash
arduino-cli compile --fqbn arduino:megaavr:nona4809
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809 <path to script>
```

Again, it's a bit too long-winded for me. So let's alias this one too:
```bash
alias acompile="arduino-cli compile --fqbn arduino:megaavr:nona4809"
alias aupload="arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809"
```

Now we can simply run the following command to build our sketch and push it to the Arduino:
``bash
acompile ~/Signifier/signify/sig_led && aupload ~/Signifier/signify/sig_led
```

Use the `-v` arugment for verbose mode, in case you need to debug:
``bash
acompile ~/Signifier/signify/sig_led && aupload ~/Signifier/signify/sig_led
```

> More information: <https://forum.arduino.cc/t/compile-with-cli-and-specify-register-emulation-option-solved/639015>









# Dead-ends

## PyAlsaAudio Python Module

https://github.com/larsimmisch/pyalsaaudio

This module is far less comprehensive than the PulseAudio module `sounddevice`. I attempted this module because `sounddevice` produced some strange errors in certain scenarios (running Stream in a thread, for instance).

PyAlsaAudio is very bare-bones in functionality. Futhermore, not only is it poorly documented, for some reason the module refused to import into my VC Code Intellisense. So I had to have a second terminal open running things like `dir(alsaaudio)` into `dir(alsaaudio.pcms())` and web browsers constantly searching on forums and the like.

## Pipe-wire ---- no, just stop

Attempting to swap over the `pipe-wire`

> More information: <https://askubuntu.com/questions/1333404/how-to-replace-pulseaudio-with-pipewire-on-ubuntu-21-04>

```bash
sudo apt install pipewire-audio-client-libraries
```



# EARLIER ARDUINO NOTES (KEEP)

https://github.com/PowerBroker2/pySerialTransfer
https://github.com/PowerBroker2/SerialTransfer

python3 -m pip install pySerialTransfer


DEVELOPMENT STEPS ONLY (NO NEED FOR THESE TOOLS FOR PRODUCTION)

Installing remote VSCODE headless Arduino project functionality:
https://joachimweise.github.io/post/2020-04-07-vscode-remote/

curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

sudo usermod -a -G tty $USER
sudo usermod -a -G dialout $USER
sudo usermod -a -G uucp $USER
sudo usermod -a -G plugdev $USER

arduino-cli config init
arduino-cli core update-index
arduino-cli board list
arduino-cli core search arduino
arduino-cli core install arduino:megaavr
arduino-cli lib search adafruit neopixel
arduino-cli lib install "Adafruit NeoPixel"
arduino-cli lib search FastLED
arduino-cli lib install "FastLED"
arduino-cli lib search SerialTransfer
arduino-cli lib install "SerialTransfer"
sudo find / -name 'arduino-cli'

GET FQBNs from commands:
  arduino-cli board list
      e.g.:
          "arduino:megaavr:nona4809"
Function Commands:
  alias acompile="arduino-cli compile --fqbn arduino:megaavr:nona4809"
  alias aupload="arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809"

Storing the commands:
  funcsave acompile
  funcsave aupload

Then, you can compile and push Arduino sketches like this:
  acompile /home/pi/Signifier/leds/arduino/mmw_led_breath_purple && aupload /home/pi/Signifier/leds/arduino/mmw_led_breath_purple

`cpptools`` is returning very high on the CPU and memory stats for `top`
..So is `node`. I wonder how related `node` and `cpptools` are to the Arduino apps. 
 Going to reboot and see what happens... but almost 80%+ CPU usage on all cores RN.

Still very high, doing to disable Sys-QTT and Node Exporter...
- Investigating furhter, this is a known issue with cpptools
  - https://github.com/microsoft/vscode-cpptools/issues/5574
- Attempting to limit C++ library directories to prevent recursive searching by library...

CPU usage seems to have settled for the moment. Obviously this won't be a problem for production,
but it would be good to have VS Code -> Arduino functionality during development. Will stick with this for now.
CPU is good again. Narrowed the libraries included in c_cpp_properties.json

















# OLD INFO!


<!-- ## Pygame 2 audio device not detected
<https://stackoverflow.com/questions/68529262/init-sounddevice-in-pygame2-on-raspberry>


- I was able to find the correct audio device using `_sdl2` Python module:

```python
import pygame as pg
import pygame._sdl2 as sdl2
pg.init()
is_capture = 0  # zero to request playback devices, non-zero to request recording devices
num_devices = sdl2.get_num_audio_devices(is_capture)
devices = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num)]
print("\n".join(device))
pg.quit()
```

Which returned the following:

```text
bcm2835 Headphones, bcm2835 Headphones
vc4-hdmi-0, MAI PCM i2s-hifi-0
vc4-hdmi-1, MAI PCM i2s-hifi-0
```

I was able to start the Pygame mixer successfully:

```python
pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename=devices[0])
pg.mixer.init()
pg.init()
```


- Using `aplay -l`, you can get the same information, albiet in a less succinct format:
```bash
aplay -l
**** List of PLAYBACK Hardware Devices ****
card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]
  Subdevices: 8/8
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
  Subdevice #7: subdevice #7
card 1: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```
fglgkbjs;gsjg;kljgsd;fgjd;jdfsd'lgkjsd'kjsd'flkjd'lkjdv'jdv;'sndv'osodifvnm'asvmnae'krvm'elrkmA'FMAF'LMF'L;MF';lme'LMLmdmsdfv;almv'avmS'DMASD';LMAD'CV;LMD'L;Msdc'LMC'lmc'AL;MSC'as'JL'efgoj'rpohjth'pojth'opjrth9operthj90erthj4w90thj4w90[hj56h90j6h


By comparing the output from both the `sdl2` module and `aplay -l`, we can see that the matching strings are between the square brackets from aplay's output:

<pre>
card 0: Headphones <b>[bcm2835 Headphones]</b>, device 0: bcm2835 Headphones <b>[bcm2835 Headphones]</b>
card 1: vc4hdmi0 <b>[vc4-hdmi-0]</b>, device 0: MAI PCM i2s-hifi-0 <b>[MAI PCM i2s-hifi-0]</b>
card 2: vc4hdmi1 <b>[vc4-hdmi-1]</b>, device 0: MAI PCM i2s-hifi-0 <b>[MAI PCM i2s-hifi-0]</b>
</pre>

So, if you're unable to use the `sdl2` module for some reason, a short Python `subprocess` return wrangle from `aplay` could potentially (I haven't tested this on systems other than a couple of RPi4Bs running Ubuntu Server 20.04 with default I/O) produce the same output using a native Linux module.

TODO - WRITE DEMO PYTHON SUBPROCESS SCRIPT



Other useful utilities for investigating audio devices:

- `alsabat` produces a test tone using ALSA audio output as a sanity check
- `sudo lsmod | grep snd` to display current system sound module usage


- Test ALSA audio output. Should produce a sine wave tone:
```bash
$ alsabat

alsa-utils version 1.2.4

Entering playback thread (ALSA).
Get period size: 2760  buffer size: 22050
Playing generated audio sine wave
Entering capture thread (ALSA).
Cannot open PCM capture device: No such file or directory(-2)
Playback completed.
Exit capture thread fail: -2
```

- Display system sound module usage:
```bash
$ sudo lsmod | grep snd

snd_soc_hdmi_codec     20480  2
snd_soc_core          241664  2 vc4,snd_soc_hdmi_codec
snd_bcm2835            24576  0
snd_compress           20480  1 snd_soc_core
snd_pcm_dmaengine      20480  1 snd_soc_core
snd_pcm               131072  5 snd_bcm2835,snd_soc_hdmi_codec,snd_compress,snd_soc_core,snd_pcm_dmaengine
snd_timer              36864  1 snd_pcm
snd                   102400  6 snd_bcm2835,snd_soc_hdmi_codec,snd_timer,snd_compress,snd_soc_core,snd_pcm
``` -->

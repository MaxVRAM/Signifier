# Signifier
Python scripts designed for Raspberry Pi 4B to manage sensor inputs, output modulated audio, and send serial messages to an Arduino for controlling RGB LED strips.

## Project targets
1. Reliable **non-interactive** audio and LEDs.
    - [x] Audio playback
    - [x] Generative audio layer composition manager
    - [x] Basic LED modulation
2. **Interactive** audio and non-interactive LEDs.
    - [ ] Sensor: Bluetooth
        - [ ] Tested 
        - [ ] Integrated
    - [ ] Sensor: Microphone
        - [ ] Tested 
        - [ ] Integrated
    - [ ] Sensor: Temperature
        - [ ] Tested 
        - [ ] Integrated
    - [ ] Interactive audio manager
        - [ ] Tested 
        - [ ] Integrated
3. Interactive audio & interactive LEDs
    - [x] Raspberry Pi / Arduino interfacing
        - [x] Tested 
        - [x] Integrated
    - [ ] Audio analysis
        - [x] Tested 
        - [ ] Integrated
    - [ ] Interactive LED manager
        - [x] Tested 
        - [ ] Integrated
    - [ ] LED effects suite
        - [ ] Tested 
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
sudo apt install libportaudio2  # PortAudio, required for LED audio-reactivity.
sudo apt install alsa-utils     # Provides loopback and additional debugging tools.
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
    - `-t wav` changes the default noise test sound to a voice saying "left channel", "right channel".
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
    - Heck yeah! What about the ALSA output?
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
        Looking good!

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
    ```

We've now completed the audio environment configuration. To recap what we've done:


[x] Install `PortAudio` and `ALSA Utils` system packages.

[x] Disable HDMI audio devices.

[x] Create an audio *loopback device*.

[x] Ensure everything runs on boot with fixed card numbers.


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

# Debugging

## Audio debugging CLI commands

### Various outputs of the available audio devices

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

### Audio configuration

A pretty terminal GUI for inspecting and making changes to the audio device volumes. 

```bash
alsamixer
```


## Pygame 2 audio device not detected
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
```


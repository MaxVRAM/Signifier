
# Full installation guide

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

- The cat walked across the keyboard:

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




# Networking

## WiFi

Signifiers are configured to search for the following WiFi details:

 - SSID: `mmw_sig_net`
 - Password: *redacted* (contact for password)

More networks can be added, along with their connection priority. To do so, create a new entry for the additional SSID(s) in the `/etc/wpa_supplicant/wpa_supplicant.conf` file. For example:

```rust
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=AU

network={
        ssid="mmw_sig_net"
        psk="redacted"
        key_mgmt=WPA-PSK
        priority=1
}

network={
        ssid="backup_network"
        psk="redacted"
        key_mgmt=WPA-PSK
        priority=2
}
```

- Once connected to `mm_sig_net` Signifiers will attempt connection with the Signifier Server via its VPN. **NOT YET IMPLEMENTED**




---

# Singifier Server Pi

## Option 1: SD card duplication

Use an application like BalenaEtcher to write the supplied Signifier image on to a fresh SD card. This is by far the easiest and quickest method to deploy a new Signifier.

(will add steps later)

## Option 2: Install script

If you'd like to build the Signifier Server on a fresh OS environment, you can use the install script supplied in this repo.

1. Download the zip file of **Raspberry Pi OS Bulleye 64-bit (rm64)** from [here](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2021-11-08/)

2. Write the OS to the SD card with something like BalenaEtcher, insert the SD card into the Signifier and go through the default OS setup on the new image.

3. Clone this repo:
    ```bash
    git clone https://github.com/MaxVRAM/SignifierServer.git && cd SignifierServer
    ```

4. Execute the install script and follow any prompts:
    ```bash
    install.sh
    ```

## Option 3: Manual installation

Follow **ALL** the steps this guide.



- The Signifier Server should be deployed on an additional Raspberry Pi 4B (4GB).
- This server will host the following:
  - VPN server for all Signifiers to connect to.
  - Web application for updating Signifier configurations.
  - Grafana/Prometheus database, for monitoring all Signifier metrics.

## Installation from scratch

1. Download the zip file of **Raspberry Pi OS Bulleye 64-bit (arm64)** from [here](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2021-11-08/)

2. Write the OS to the SD card with something like BalenaEtcher, insert the SD card into the Signifier and go through the default OS setup on the new image.

3. Install basic environment:

4. Install Docker, Docker Compose, Portainer-CE:

5. Install Monitoring stack (Prometheus, Grafana and Uptime):

6. 



# VPN Access

## VPN Server

The Signifier Server hosts the Linux application `pivpn` to manage the VPN server. This is configured to use the `OpenVPN`.

VPN server configuration resides on the Signifier Server Pi at `/etc/openvpn`.

`server.conf` contains the majority of VPN configuration options.



## VPN Client (Signifiers)

The following script is used to install `openvpn` and add the Signifier-specific `ovpn` file generated by the VPN server, described in the previous section.

```bash
#!/bin/sh
apt update
apt upgrade -y
apt install openvpn -y
mkdir -p /etc/openvpn/client
chown root:root /etc/openvpn/client
chmod 700 /etc/openvpn/client
chown root:root client.ovpn
chmod 700 client.ovpn
mv client.ovpn /etc/openvpn/client
openvpn --config /etc/openvpn/client/client.ovpn --daemon
cp /etc/openvpn/client/client.ovpn /etc/openvpn/client.conf
systemctl enable openvpn@client.service
systemctl start openvpn@client.service
```
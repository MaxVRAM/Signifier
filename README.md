# Signifier
Python scripts designed for Raspberry Pi 4B to manage sensor inputs, output modulated audio, and send serial messages to an Arduino for controlling RGB LED strips.

## Project targets
1. Reliable **non-interactive** audio and LEDs.
  - [x] Reliable non-interactive audio
  - [x] Reliable non-interactive LEDs
2. **Interactive** audio and non-interactive LEDs.
  - [ ] Sensor: Bluetooth
  - [ ] Sensor: Microphone
  - [ ] Sensor: Temperature
  - [ ] Interactive audio manager
3. Interactive audio & interactive LEDs
  - [ ] Raspberry Pi / Arduino interfacing
  - [ ] Audio analysis
  - [ ] Interactive LED manager
4. Network communication over WiFi/cellular to online server:
  - [ ] Signifier management over WiFi
  - [ ] Writing sensor data to local time-series database
  - [ ] Pushing local data to remote database
  - [ ] Signifier management over cellular
BONUS ROUND:
  - [ ] Web-socket server on Signifiers
  - [ ] Centralised web-app to monitor and control Signifiers via web-sockets 
  - [ ] Real-time Signifier GPS coordinate map
  - [ ] Data-visualisation of sensor values and Signifier states

## Hardware

### Computation

[Raspberry Pi 4B](https://au.rs-online.com/web/p/raspberry-pi/1822096)

[Arduino Nano Every](https://au.rs-online.com/web/p/arduino/1927590)

- Basic information on Raspberry Pi -> Arduino interfacing using PySerial - [link](https://create.arduino.cc/projecthub/ansh2919/serial-communication-between-python-and-arduino-e7cce0)
- Instructable guide on PySerial - [link](https://www.instructables.com/Interface-Python-and-Arduino-with-pySerial/)

### LEDs
[RGB LED strips - WS2812B 120p/m](https://www.jaycar.com.au/2m-rgb-led-strip-with-120-x-addressable-w2812b-rgb-leds-arduino-mcu-compatible-5v/p/XC4390)

- Basic guide for controlling WS212B with Arduino - [link](https://randomnerdtutorials.com/guide-for-ws2812b-addressable-rgb-led-strip-with-arduino/)
- Why WS2812B LEDs were not a good choice - [link](https://tutorials-raspberrypi.com/connect-control-raspberry-pi-ws2812-rgb-led-strips/)


### Audio
[Audio amplifier - 50 watt Bluetooth](https://core-electronics.com.au/digital-bluetooth-power-amplifier-50w-2.html)

- It's unfortunate the amp doesn't have a 3.5mm jack input, as this would provide more options should there be issues with USB communication.

Currently trying these:
- `python3 -m pip install sounddevice`
- `python3 -m pip install alsa-utils`
- `sudo apt install libportaudio2`


### Temperature sensor
[Digital Temp Sensor](https://www.altronics.com.au/p/z6386-stainless-steel-housing-waterproof-ds18b20-temperature-probe/)


### Microphone
[Mini USB Microphone](https://core-electronics.com.au/mini-usb-microphone.html)


### Networking
[NB-IoT Raspberry Pi HAT](https://core-electronics.com.au/nb-iot-emtc-edge-gprs-gnss-hat-for-raspberry-pi.html)

- Guide on the specific SIM chip - [link](https://support.hologram.io/hc/en-us/articles/360036559494-SIMCOM-SIM7000)
- Guide on different version, but might still be relavent - [link](https://www.switchdoc.com/2021/05/tutorial-using-cellular-modems-with-the-raspberry-pi-4b/)


## Signifier software
- OS: Raspberry Pi OS Bulleye 64-bit (arm64) - superior performance and far better compatibility with software packages - [link](https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2021-11-08/)
- Python 3.8 - primary language for Signifier functionality.
- Docker/Portainer - local and remote management of additional packages.
- Prometheus - time-series database for local database recording of sensor data.

## Python modules
- [PySerial](https://pypi.org/project/pyserial/)
- [sounddevices](https://python-sounddevice.readthedocs.io/en/0.4.3/)
- [Prometheus Python Client](https://pypi.org/project/prometheus-client/0.0.9/)




## Todos

Basic playback:
  1. ~~Create proper exit function and audio clip playback length limiting~~
  2. add function to move newly played clip from inactive_pool to active_pool
  3. ~~differentiate various clip types (short, med, long, loop, etc)~~
  4. replate original Signifier audio playback
  5. use noise to modulate channel volumes

Modulated playback:

  6. Create server of some kind. Accepting JSON would be ideal, for key/value control. (Flask server?)
  7. Affix server responses to functions
  8. Create documentation for server commands

LED reactivity:

  9. Add function to analyise channel output amplitudes
  10. Test pyserial to Arduino functionality
  11. Create simple LED brightness reactivity based on audio output
  



## Debugging

### Pygame 2 audio device not detected
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



# Main fixes

List of fixes over the original Siginifer code:
- Original code maxed out single thread:
  - This was mostly due to the program's while loop not containing a time.sleep(), slamming the main thread.
  - Many hard-coded values, making debugging and alterations difficult.
  - 

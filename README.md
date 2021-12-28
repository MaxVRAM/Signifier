# Signifier
Python scripts designed for Raspberry Pi 4B to manage sensor inputs, output modulated audio, and send serial messages to an Arduino for controlling RGB LED strips.

## Project targets
1. Reliable **non-interactive** audio and LEDs.
2. **Interactive** audio and non-interactive LEDs.
3. Interactive audio, with interactive LEDs controlled by the Raspberry Pi.
4. Features of target target 3, plus network communication via WiFi and cellular network to an online server.

## Feature checklist
- [ ] Reliable non-interactive audio
- [ ] Reliable non-interactive LEDs
- [ ] Interactive audio
- [ ] Raspberry Pi / Arduino interfacing
- [ ] Interactive LEDs
- [ ] Signifier management over WiFi
- [ ] Writing sensor data to local time-series database
- [ ] Pushing local data to remote database
- [ ] Signifier management over cellular
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
  



## Random notes

- Producing audio device list:

```python
import pygame._sdl2 as sdl2
pg.init()
is_capture = 0  # zero to request playback devices, non-zero to request recording devices
num = sdl2.get_num_audio_devices(is_capture)
names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num)]
print("\n".join(names))
pg.quit()
```




# Main fixes

List of fixes over the original Siginifer code:
- Original code maxed out single thread:
  - This was mostly due to the program's while loop not containing a time.sleep(), slamming the main thread.
  - Many hard-coded values, making debugging and alterations difficult.
  - 
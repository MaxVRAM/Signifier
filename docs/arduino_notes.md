# Arduino systems



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



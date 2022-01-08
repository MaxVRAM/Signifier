
# https://github.com/PowerBroker2/pySerialTransfer
# https://github.com/PowerBroker2/SerialTransfer

# python3 -m pip install pySerialTransfer


# DEVELOPMENT STEPS ONLY (NO NEED FOR THESE TOOLS FOR PRODUCTION)
#
# Installing remote VSCODE headless Arduino project functionality:
# https://joachimweise.github.io/post/2020-04-07-vscode-remote/
#
# curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# sudo usermod -a -G tty $USER
# sudo usermod -a -G dialout $USER
# sudo usermod -a -G uucp $USER
# sudo usermod -a -G plugdev $USER

# arduino-cli config init
# arduino-cli core update-index
# arduino-cli board list
# arduino-cli core search arduino
# arduino-cli core install arduino:megaavr
# arduino-cli lib search adafruit neopixel
# arduino-cli lib install "Adafruit NeoPixel"
# arduino-cli lib search FastLED
# arduino-cli lib install "FastLED"
# arduino-cli lib search SerialTransfer
# arduino-cli lib install "SerialTransfer"
# sudo find / -name 'arduino-cli'
# 
# GET FQBNs from commands:
#   arduino-cli board list
#       e.g.:
#           "arduino:megaavr:nona4809"
# Function Commands:
#   alias acompile="arduino-cli compile --fqbn arduino:megaavr:nona4809"
#   alias aupload="arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809"
#
# Storing the commands:
#   funcsave acompile
#   funcsave aupload
# 
# Then, you can compile and push Arduino sketches like this:
#   acompile /home/pi/Signifier/leds/arduino/mmw_led_breath_purple && aupload /home/pi/Signifier/leds/arduino/mmw_led_breath_purple
#
# `cpptools`` is returning very high on the CPU and memory stats for `top`
# ..So is `node`. I wonder how related `node` and `cpptools` are to the Arduino apps. 
#  Going to reboot and see what happens... but almost 80%+ CPU usage on all cores RN.
#
# Still very high, doing to disable Sys-QTT and Node Exporter...
# - Investigating furhter, this is a known issue with cpptools
#   - https://github.com/microsoft/vscode-cpptools/issues/5574
# - Attempting to limit C++ library directories to prevent recursive searching by library...
#
# CPU usage seems to have settled for the moment. Obviously this won't be a problem for production,
# but it would be good to have VS Code -> Arduino functionality during development. Will stick with this for now.
# CPU is good again. Narrowed the libraries included in c_cpp_properties.json


import time
from pySerialTransfer import pySerialTransfer as txfer


if __name__ == '__main__':
    try:
        link = txfer.SerialTransfer('COM3')
        link.open()
        time.sleep(2) # allow some time for the Arduino to completely reset
        
        while True:
            send_size = 0
            
            ###################################################################
            # Send a list
            ###################################################################
            list_ = [1, 3]
            list_size = link.tx_obj(list_)
            send_size += list_size
            
            ###################################################################
            # Send a string
            ###################################################################
            str_ = 'hello'
            str_size = link.tx_obj(str_, send_size) - send_size
            send_size += str_size
            
            ###################################################################
            # Send a float
            ###################################################################
            float_ = 5.234
            float_size = link.tx_obj(float_, send_size) - send_size
            send_size += float_size
            
            ###################################################################
            # Transmit all the data to send in a single packet
            ###################################################################
            link.send(send_size)
            
            ###################################################################
            # Wait for a response and report any errors while receiving packets
            ###################################################################
            while not link.available():
                if link.status < 0:
                    if link.status == txfer.CRC_ERROR:
                        print('ERROR: CRC_ERROR')
                    elif link.status == txfer.PAYLOAD_ERROR:
                        print('ERROR: PAYLOAD_ERROR')
                    elif link.status == txfer.STOP_BYTE_ERROR:
                        print('ERROR: STOP_BYTE_ERROR')
                    else:
                        print('ERROR: {}'.format(link.status))
            
            ###################################################################
            # Parse response list
            ###################################################################
            rec_list_  = link.rx_obj(obj_type=type(list_),
                                     obj_byte_size=list_size,
                                     list_format='i')
            
            ###################################################################
            # Parse response string
            ###################################################################
            rec_str_   = link.rx_obj(obj_type=type(str_),
                                     obj_byte_size=str_size,
                                     start_pos=list_size)
            
            ###################################################################
            # Parse response float
            ###################################################################
            rec_float_ = link.rx_obj(obj_type=type(float_),
                                     obj_byte_size=float_size,
                                     start_pos=(list_size + str_size))
            
            ###################################################################
            # Display the received data
            ###################################################################
            print('SENT: {} {} {}'.format(list_, str_, float_))
            print('RCVD: {} {} {}'.format(rec_list_, rec_str_, rec_float_))
            print(' ')


            time.sleep(1)
    
    except KeyboardInterrupt:
        try:
            link.close()
        except:
            pass
    
    except:
        import traceback
        traceback.print_exc()
        
        try:
            link.close()
        except:
            pass
# Testing the sounddevice's Stream() method for created
# real-time analysis of the Signifier's audio output.
#
# Analysis data will be used for modulating the LED
# outputs via serial from the signifier.py module.
# 
import sounddevice as sd
#sd.Stream()
sd.query_devices()
sd.get_stream()
# Okay, so seems like sounddevice requires PortAudio.



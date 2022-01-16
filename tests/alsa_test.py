
#!/usr/bin/env python3
import struct
import alsaaudio as alsa

sound_out = alsa.PCM()  # open default sound output
sound_out.setchannels(1)  # use only one channel of audio (aka mono)
sound_out.setperiodsize(5) # buffer size, default is 32

sound_in = alsa.PCM(type=alsa.PCM_CAPTURE)  # default recording device
sound_in.setchannels(1)  # use only one channel of audio (aka mono)
sound_in.setperiodsize(5) # buffer size, default is 32

while True:
    sample_lenght, sample = sound_in.read()
    sound_out.write(sample)


# Attempting to ALSA-only

# alsa.pcms()

# [
    # 'null',
    # 'default', 
    # 'CardAndLoop', 
    # 'MultiCh', 
    # 'MixCard', 
    # 'MixLoopback', 
    # 'hw:CARD=Headphones,DEV=0', 
    # 'plughw:CARD=Headphones,DEV=0', 
    # 'sysdefault:CARD=Headphones', 
    # 'dmix:CARD=Headphones,DEV=0', 
    # 'hw:CARD=vc4hdmi0,DEV=0', 
    # 'plughw:CARD=vc4hdmi0,DEV=0', 
    # 'sysdefault:CARD=vc4hdmi0', 
    # 'hdmi:CARD=vc4hdmi0,DEV=0', 
    # 'dmix:CARD=vc4hdmi0,DEV=0', 
    # 'hw:CARD=vc4hdmi1,DEV=0', 
    # 'plughw:CARD=vc4hdmi1,DEV=0', 
    # 'sysdefault:CARD=vc4hdmi1', 
    # 'hdmi:CARD=vc4hdmi1,DEV=0', 
    # 'dmix:CARD=vc4hdmi1,DEV=0', 
    # 'hw:CARD=Loopback,DEV=0', 
    # 'hw:CARD=Loopback,DEV=1', 
    # 'plughw:CARD=Loopback,DEV=0', 
    # 'plughw:CARD=Loopback,DEV=1', 
    # 'sysdefault:CARD=Loopback', 
    # 'front:CARD=Loopback,DEV=0', 
    # 'surround21:CARD=Loopback,DEV=0', 
    # 'surround40:CARD=Loopback,DEV=0', 
    # 'surround41:CARD=Loopback,DEV=0', 
    # 'surround50:CARD=Loopback,DEV=0', 
    # 'surround51:CARD=Loopback,DEV=0', 
    # 'surround71:CARD=Loopback,DEV=0', 
    # 'dmix:CARD=Loopback,DEV=0', 
    # 'dmix:CARD=Loopback,DEV=1'
# ]


# - `python3 -m pip install alsa-utils`?
# - `sudo apt install libasound2-dev`?
# - `sudo modprobe snd-aloop`?


# - `python3 -m pip install pyalsaaudio`
# https://github.com/larsimmisch/pyalsaaudio/blob/master/recordtest.py#L64



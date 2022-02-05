# System audio


## ALSA

### Context

Default audio system for many Linux distributions (importantly, Debian, which I was using), defines the audio devices available to the OS. All other Linux audio systems hook into ALSA.

### Summary

...

### Raw notes

## Realtime audio streaming

<https://codeberg.org/rtcqs/rtcqs>

## ALSA Commands

- Config file is here:

    ```bash
    sudo nano /usr/share/alsa/alsa.conf
    ```

- Displaying existing system audio modules:

    ```bash
    cat /proc/asound/modules
    # 0 snd_aloop
    # 1 snd_bcm2835
    ```

- Displaying existing ALSA audio cards:

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




## PulseAudio

### Context

The first audio system abstraction I tried after vanilla ALSA. Convenient, but essentially just another CLI/configuration layer to ALSA's core system.

### Summary

There are several conveniences that PulseAudio adds, including a slightly easier configuration format and appears to have more of an ecosystem behind using it. I encountered CPU issues using PulseAudio to share audio between devices and performing audio analysis on one. It could be a sample rate conversion issue, but I had difficulty ensuring the sample rate and bit depth of the devices were ubiquitous across all ALSA and PulseAudio devices, so I attempted alternatives to PulseAudio.


### Raw notes


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

- Setting up a system-wide PulseAudio daemon. Could be worth checking this out:

    > <https://rudd-o.com/linux-and-free-software/how-to-make-pulseaudio-run-once-at-boot-for-all-your-users>

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

- Disable/disabling PulseAudio:

    ```bash
    sudo nano /etc/pulse/client.conf
    ```

    Change `;autospawn = yes` to `autospawn = no`.

    Then kill the process:

    ```bash
    pulseaudio --k
    ```

    Then check:

    ```bash
    ps -e | grep pulse
    ```

    PulseAudio will invoke itself again should a device still associated call it. For example:

    ```bash
    ❯ speaker-test -d hw:0,0

    speaker-test 1.2.4

    Playback device is hw:0, 0
    Stream parameters are 48000Hz, S16_LE, 1 channels
    Using 16 octaves of pink noise
    Rate set to 48000Hz (requested 48000Hz)
    Buffer size range from 192 to 2097152
    Period size range from 64 to 699051
    Using max buffer size 2097152
    Periods = 4
    was set period_size = 524288
    was set buffer_size = 2097152
    ALSA <-> PulseAudio PCM I/O Plugin
    Its setup is:
    stream       : PLAYBACK
    access       : RW_INTERLEAVED
    format       : S16_LE
    ....
    ```

    ```bash
    ❯ ps -e | grep pulse
    5924 ?        00:00:00 pulseaudio
    ```

    The socket needs to be terminated too:

    ```bash
    systemctl --user stop pulseaudio.socket\
    && systemctl --user stop pulseaudio.service
    ```

    AND disabled:

    ```bash
    systemctl --user disable pulseaudio.socket
    systemctl --user disable pulseaudio.service
    ```

    Once removed, the `speaker-test -D hw:0,0` started with almost no latency (confirming the impact of PulseAudio's streaming buffer size). The output now had this:

    ```bash
    ...
    was set period_size = 16384
    was set buffer_size = 65536
    Hardware PCM card 0 'bcm2835 Headphones' device 0 subdevice 0
    Its setup is:
    stream       : PLAYBACK
    access       : RW_INTERLEAVED
    ...
    ```

    So I ran `speaker-test -D hw:Loopback,0` to pusht he noise through the native ALSA loopback device. Then ran `python tests/alsa_in_test.py` (which simply prints the loopback device audio buffer once it's full):

    ```python
    import alsaaudio

    device = 'hw:Loopback,1'

    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, 
        channels=1, rate=48000, format=alsaaudio.PCM_FORMAT_S16_LE, 
        periodsize=160, device=device)

    loops = 10000
    while loops > 0:
        loops -= 1
        # Read data from device
        l, data = inp.read()
        if l > 0:
            print(data)
    ```


    ```bash
    b'M\rB\nf\x06\xcf\x0b\x9a\x07\xcc\x02\x89\x07k\tb\x05\xf2\x13\x17\x12\xf7\x17\x8a\x1a2\x15\xd9\x19\xa2\r \x0eS\x05\x88\x03\x1f\xf6r\xfb\xf9\xf9{\xf34\xea-\xf6G\xf5\xcb\xf3\xe6\xfdn\xfcr\xfd\xc3\xff\x81\x03\xa4\xfa\x80\x05\x80\xfe\x1d\x0c \n\xc1\x0c\xcd\x03\xc0\x03\xdf\xf7,\xf4\xbb\xf3;\xf2i\xf6\xdf\xffY\x00w\x07?\x0b\xb9\x07\xaa\xf8~\xfb \nv\x0f\xf9\x08}\x10k\x05\xb8\x05\xdc\x0c\x19\x11\x95\x0c\xbd\x0c\xde\r\xc8\xff\xac\x08\xd2\x03@\xfc=\xef\xd6\xf1\x1d\xf6\x95\xf8\xae\xfb?\x020\x05\xa0\xfb\xac\xfdL\x0c\xfc\xfd`\xfa?\x03y\x0c\xc8\x0b\x87\x06t\xfcd\x00\xbb\x03\x84\xfe\x02\x01\x92\x02Q\xfe\x13\xfd\xc2\x08g\xfc\x10\td\r\xcd\x10[\x0bs\r\x93\x11\n\x08J\x02U\xfa\xe3\x00\xc8\x0c*\x04S\x07\xce\x0eD\x10y\x05+\x08$\r\x12\x0bH\t\x7f\xfb\x18\x00A\x11\x90\x08\xed\x00\xfa\x07(\xf5\r\xfd?\xfe\x9b\x07^\xffB\x00\xdc\xfc\xd4\x06\xb8\x04#\x01\xda\x08\xeb\x06-\x04\x1f\x01\\\x03\x8a\xf4\xde\xf9\x06\xf3\xb9\xfa\xe9\x08\xeb\x0c\xb1\te\x06\xc9\x07\xba\x08\xcc\x05`\rU\x13q\r\x9d\x15\x1a\x13/\x05\x0e\x0b\xe4\x12\xdd\x13\\\x17\x17\x1dd\x10H\x0b\xc6\x07\xc8\x06'
    b'n\x05+\x01}\x03$\t\xba\x07n\x04\xf3\x0b\x8d\x12\x99\x0e&\x13\x04\x124\x02g\n\xb0\x16?\x0bf\x13\x97\x0c\xa6\x07\xa5\n\x9a\tv\x10\xfd\x0b\x1c\r\x97\x0c\xa2\t[\x0f\x0f\x05M\x08\xbc\xfde\x08<\x04\x89\xfc\x05\x06@\x0b1\x026\x07\xf2\x01\x84\xfd\xb2\x04L\x06\x82\xfd\xfc\xf4(\xfe\xf2\x04\xbd\x00\xf5\x01\xe8\x00\xc2\t\xd9\x07;\x0c\x14\x0c9\x0b\x04\x10\xd0\x1a\xea\x14;\x11v\x1aN\n_\x05Q\x02\xa0\x07z\x0c\x18\x11\xa0\n\xfd\tf\x0e\xd2\x0c\xa0\x04p\x04\xaa\x02\x85\x01v\x0c\xc8\x07$\xff\xc2\x08R\r\xf4\x14T\ti\x08\x9c\x0b\xd0\xfd\xf6\x01)\x0fi\nw\x0bF\x03 \x07\x1a\xfb\xe5\xfd\x01\xfci\x07\x9b\xffM\xf9\x85\xfe\x18\x04\x1b\x02r\t\xd6\x03#\xfa\xcc\xf84\xf7z\xfb\xeb\x01e\xf7C\xf1\x06\xf9t\x00\xcc\x07m\xfdx\xfdS\xfa\x84\xfa\x06\x04\xab\xf8\x8b\xfb\xf2\xfcj\xfa0\x07i\xfb%\x08+\x02\xf3\xfd\xce\x025\xfe\x89\xf5\x91\xfc\xf6\xf9\xa4\xeb\xe2\xe8\x89\xea\n\xee[\xf1B\xfd\x9f\xfd\xda\xff\x12\t\x8e\xffB\xfe\xd2\x07\x85\x02d\xff\x95\x00\xce\xfed\xfdj\xf4\xf2\x02\xa8\x0c\x8e\x01\x97\x01\n\xfc4\xfbi\xef\x86\xf0\x04\xeaP\xebr\xed\xf0\xed|\xe0\xb7\xe5L\xf5'
    b'V\xf3)\xf1\x9e\xef5\xf8A\xf3\xd2\xf3\x8f\xfa[\xfd7\xf7\x8b\xf0\xdb\xf4%\x03I\xff \x00\x1b\x0b(\x0c\xe2\xff\xd3\xff_\x04F\x00\x97\xf5\xdc\x01-\xfaq\x03a\x03\xd5\xfc\xda\xf7\xb2\xf9\xda\xff\xc6\x04\t\tV\x12\xfd\x11d\x155\x07\x82\x02\xb6\x10\x82\x0b\xf3\x0eP\x08T\x04<\x11W\t\x02\x05\xdf\xff\xcd\x03\x00\x0bt\x16\xbc\x0c\xfa\r\x8f\x0e\x1e\x11\xe4\n\x90\x02\xf8\x04\xed\x08\x15\x04"\x07\xac\x10\x81\x0f\xd2\x0b\xd6\x06\xf3\x08%\xf57\xf6\x98\x01m\xfe\x7f\t\xbc\x02\x8d\x04\x10\x02y\x04\xc5\x08\xc6\x03\xbc\xffK\xfb\xd7\t\xe0\xfd\xd6\xfe\x05\xf5\x8f\xf9\xf3\x03y\xff\xec\xf7D\xfe\xcb\xf8\xa9\xf3.\xf8\xca\xf6\x17\xf8"\xf5\x80\xf3[\xfa\x0f\xf2z\xfd\x97\xf4\x15\xf80\xf7\xa0\xf7m\xf4.\xff.\x00\x00\x01B\x03\x85\x02\xdd\xfb8\xf8N\xfe\xa0\xfc\xc0\x00`\x07\x85\x08\xbf\x02\x16\x05\xf4\x03\x19\x0c\x83\x04K\x01\x19\xffS\xff\xff\xff\x15\x07e\xfe\x0f\t\x98\n\x14\x02\x84\xf5\xa6\xfa\x0f\xfb\xee\x05\xf0\x0b\x03\r]\xff\x13\x00\xe2\x01\xd5\xf8\x96\xf7U\x02\x9f\x07\x16\xfb;\xf4\xbc\xf7|\xf8C\x07O\xfa\x13\xf7a\x06\x86\x04\xfa\xfc\xfa\xfed\x0c4\n\xb3\x12]\x15f\x15\xba\x19/\t\xc9\x0e\xef\r\xaa\x07'
    ```

    That's what I was looking for :) ALSA loopback audio buffer piped directly into Python!

    Now I just need to try creating an ALSA pipe through device to share the audio stream with the headphones output... 

    A quick check that it works in a `Process`:

    ```python
    import alsaaudio
    from multiprocessing import Process

    device = 'hw:Loopback,1'

    def listen():
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, 
            channels=1, rate=48000, format=alsaaudio.PCM_FORMAT_S16_LE, 
            periodsize=160, device=device)

        loops = 10000
        while loops > 0:
            loops -= 1
            # Read data from device
            l, data = inp.read()
            if l > 0:
                print(data)

    listener = Process(target=listen)
    listener.start()
    ```

    Bingo! Now I have a native ALSA audio playback pass-through stream in Python I can push into multithreaded analysis routines <3
    
    Now I need to create the shared input/output ALSA audio device.

    Changing  `~/.asoundrc` to the following:

    > More information <https://stackoverflow.com/questions/43939191/alsa-how-to-duplicate-a-stream-on-2-outputs-and-save-system-configs>

    ```ruby
    pcm.quad {
        type multi
        slaves.a.pcm "dmix:CA0106,0"
        slaves.a.channels 2
        slaves.b.pcm "dmix:CA0106,2"
        slaves.b.channels 2
        bindings.0 { slave a; channel 0; }
        bindings.1 { slave a; channel 1; }
        bindings.2 { slave b; channel 0; }
        bindings.3 { slave b; channel 1; }
    }
    pcm.stereo2quad {
        type route
        slave.pcm "quad"
        ttable.0.0 1
        ttable.1.1 1
        ttable.0.2 1
        ttable.1.3 1
    }
    pcm.!default {
        type asym
        playback.pcm "plug:stereo2quad"
        capture.pcm "plug:dsnoop:CA0106"
    }

    pcm.shared {
        type multi
        slaves.a.pcm "hw:Headphones,0"
        slaves.a.channels 1
        slaves.b.pcm "hw:Loopback,0"
        slaves.b.channels 1
        bindings.0 { slave a; channel 0; }
        bindings.1 { slave a; channel 1; }
        bindings.2 { slave b; channel 0; }
        bindings.3 { slave b; channel 1; }
    }
    pcm.out2both {
        type route
        slave.pcm "shared"
        ttable.0.0 1
        ttable.1.1 1
        ttable.0.2 1
        ttable.1.3 1
    }
    pcm.!default {
        type asym
        playback.pcm "plug:out2both"
        capture.pcm "plug:dsnoop:Loopback"
    }
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


- I got sample rate issues while attempting to create a `sounddevice` `InputStream` in my script running on the loopback audio input. Runnign speaker output test through loopback....

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


- SUUUUUPER High CPU usage when using the PulseAudio combined-sink devices. It comepletely maxes out a core. I believe this is because of the no-wait loops in the code. Either way, I need to utilise the 4 cores. Multithreading time!!

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

- Apparently, this might be caused by the ALSA system integration of the Arduino audio device `snd_bcm2835` failing to process sample rates other than 480000. It's suggested to create an ALSA `plug` device to convert the sample rate: 

    > More information <https://github.com/raspberrypi/linux/issues/994#issuecomment-141051047>


- The issue appears to be in the source file format! `sounddevice` is a simple wrapper for PulseAudio, and according to the above github issue, PulseAudio has issues converting sample rates. Either way, converting the sample rates on the fly would most certainly add unnessessary CPU time to the system.

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

    > "Uncomment and set alternate-sample-rate to 44100 in `/etc/pulse/daemon.conf` (and remove `~/.asoundrc`)."

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

    Also did nothing... so removed it.


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




## JACK

Suggested by a friend. Seems convenient, however didn't spent long looking into it. Since my goal was just to share the audio buffer between several audio devices, JACK did not provide anything additional and only seemed to add an additional set of configurations and learnings to perform something available from either Pulse or vanilla ALSA.



## Pipewire

### Context

Had difficulties sharing audio between devices. GUI editor looked appealing.

### Summary

Unnecessary additional layer based on requirements of the Signifier project. Went back to Pulse.

### Raw notes

- Attempting to swap over the `pipe-wire`

    > More information: <https://askubuntu.com/questions/1333404/how-to-replace-pulseaudio-with-pipewire-on-ubuntu-21-04>

    ```bash
    sudo apt install pipewire-audio-client-libraries
    ```

    Let's not. This seems unnessessary...



# Python audio


## (Old module) AlsaAudio

https://stackoverflow.com/questions/34619779/implement-realtime-signal-processing-in-python-how-to-capture-audio-continuous


## PyAlsaAudio Python Module

<https://github.com/larsimmisch/pyalsaaudio>

### Context

Early in the project, I was attempting to keep all audio systems within native ALSA. I was concerned about potential CPU overhead introduced by adding layers of abstraction to the audio pipeline. 

### Summary

- Far less comprehensive than other modules. Documentation is very basic, with limited examples and no detailing of the API. Moved on after a few hours experimenting.

- Attempting again in case this module will solve CPU usage issues from PulseAudio's `sounddevice` wrapper. Despite the drawback of the module not integrating in VS Code nicely.

- Had issues working out what format the `PCM` object needs in the "device" string. There are no examples provided on the project's repo or documentation website.

    - The loopback device was the target for me: `Loopback: PCM (hw:1,1)`

    - Which the `pyalsaaudio` module accepted as `hw:1,1`

    - I discovered through trial and error. Device formatting should be in the ASLA `hw:x,y` format, where `hw` is the ALSA device **TYPE** (which also can be "plug", etc..), `x` is the **CARD** number, and `y` is the **DEVICE** number when using `aplay -l` and `arecord -l` to list the available ALSA devices.



### Raw notes

This module is far less comprehensive than the PulseAudio module `sounddevice`. I attempted this module because `sounddevice` produced some strange errors in certain scenarios (running Stream in a thread, for instance).

PyAlsaAudio is very bare-bones in functionality. Futhermore, not only is it poorly documented, for some reason the module refused to import into my VC Code Intellisense. So I had to have a second terminal open running things like `dir(alsaaudio)` into `dir(alsaaudio.pcms())` and web browsers constantly searching on forums and the like.

With the time-pressures of the project, I decided to move on.




## sounddevice (PulseAudio)

### Context

Not satisfied with PyAlsaAudio, I attempted to use the most current PulseAudio Python wrapper module, `sounddevice` to perform the audio analysis.

### Summary

Enabled the exact functionality I wanted, but will not work within a multiprocessor Process. This forces the `InputStream` object onto the main thread, and caused the core to run at 100% the entire time. It works, but the CPU issue needs to be resolved.

### Raw notes

...





## pyAudioAnalysis (ALSA)

<https://github.com/tyiannak/pyAudioAnalysis/wiki>

### Context

I was trying this module to find an alternative to `sounddevice`.

### Summary

I thought this module could perform real-time analysis, but it's purely for reading existing wav files. It may have some useful processes I could integrate. But not using this module.



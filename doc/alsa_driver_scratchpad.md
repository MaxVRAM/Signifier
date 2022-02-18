bytes_per_frame = channels * bytes_per_sample
    - 16-bit = 2 bytes


period_bytes = ? * 2 bytes


https://sites.google.com/site/es4share/home/alsa-application-note#appl
https://www.alsa-project.org/wiki/FramesPeriods


buffer_size = period_size * periods

period_bytes = period_size * bytes_per_frame

(in frames)
period_size = 48000 (1 second)
period_size = 4800 (100 ms)
period_size = 960 (20 ms) <-- target
period_size = 480 (10 ms)

(in frames)
buffer_size = (at least 2 * period size)
buffer_size = 960 * 4 = 3840  (3840 * 2 = 7680 bytes)


slave.rate            48000;
slave.period_size     4096;
slave.buffer_size     16384;

slave.period_time     84000;
slave.buffer_time     340000;



Now, if ALSA would interrupt each second, asking for bytes - we'd need to have 176400 bytes ready for it (at end of each second), in order to sustain analog 16-bit stereo @ 44.1Khz.

    If it would interrupt each half a second, correspondingly for the same stream we'd need 176400/2 = 88200 bytes ready, at each interrupt;
    if the interrupt hits each 100 ms, we'd need to have 176400*(0.1/1) = 17640 bytes ready, at each interrupt.


We can control when this PCM interrupt is generated, by setting a period size, which is set in frames.

    Thus, if we set 16-bit stereo @ 44.1Khz, and the period_size to 4410 frames => (for 16-bit stereo @ 44.1Khz, 1 frame equals 4 bytes - so 4410 frames equal 4410*4 = 17640 bytes) => an interrupt will be generated each 17640 bytes - that is, each 100 ms.
    Correspondingly, buffer_size should be at least 2*period_size = 2*4410 = 8820 frames (or 8820*4 = 35280 bytes).


> > The "frame" represents the unit, 1 frame = # channels x sample_bytes.
> > In your case, 1 frame corresponds to 2 channels x 16 bits = 4 bytes.
> > 
> > The periods is the number of periods in a ring-buffer.  In OSS, called
> > as "fragments".
> > 
> > So,
> >  - buffer_size = period_size * periods
> >  - period_bytes = period_size * bytes_per_frame
> >  - bytes_per_frame = channels * bytes_per_sample 









# Jack (qjackctl)

- Running the desktop remotely via LightDM releases the limits provided to the `audio` user to provide realtime processing:

    ```
    # /etc/security/limits.d/audio.conf
    @audio - rtprio 95
    @audio - memlock unlimited
    ```

    This can be checked by running `ulimit -l` and `ulimit -r` in the terminal via remote desktop, and logged in via SSH, returning different results.

    Remote desktop:
    ```bash
    ❯ ulimit -l
    64
    ❯ ulimit -r
    0
    ```

    SSH:
    ```bash
    ❯ ulimit -l
    unlimited
    ❯ ulimit -r
    95
    ```

    Apparently this can be solved by adding `session required pam_limits.so` to `/etc/pam.d/lightdm`. However, this already existed in my lightdm file, so I may have to revert to local screen/keyboard interaction for development.

    > More information: <https://github.com/void-linux/void-packages/issues/20051>


- A workaround is to enter the terminal during a remote graphical session and log back in to the same user using `su pi`. For some reason this resolves the session limit issue, and `qjackctl` can now be run from the terminal to open a working instance with real-time permissions enabled.

    > More information: <https://bugs.launchpad.net/ubuntu/+source/lightdm/+bug/1627769>

    Since upgraded to 16.10 Yakkety, modifications in /etc/security/limits.conf are not taken into consideration when logging in the graphical interface.

    /etc/security/limits.conf:
    @audio - rtprio 99
    @audio - memlock unlimited

    I tried the same settings in /etc/security/limits.d/audio.conf, to the same results.

    After logging in Unity, opening a console, the limits are not set:
    blablack@ideaon:~$ ulimit -l -r
    max locked memory (kbytes, -l) 64
    real-time priority (-r) 0

    Reloging to my user via bash DOES apply the limits:
    blablack@ideaon:~$ ulimit -l -r
    max locked memory (kbytes, -l) 64
    real-time priority (-r) 0
    blablack@ideaon:~$ su blablack
    Password:
    blablack@ideaon:~$ ulimit -l -r
    max locked memory (kbytes, -l) unlimited
    real-time priority (-r) 95



- Unfortunately, Jack would not accept combinations of devices that included the ALSA loopback device. After further reading, apparently using Jack with ALSA loopback is nothing but trouble anyway.

- Will have to return to pure-ALSA and try to solve under-runs... or at least work out a way to restart the audio services after it fails.
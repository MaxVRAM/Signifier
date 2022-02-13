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
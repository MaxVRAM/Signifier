

from multiprocessing import Process



def input_test():
    import sounddevice as sd
    sd.query_hostapis()
    sd.query_devices()
    sd.default.device = [11, 11]
    sd.default.channels = 1
    sd.default.dtype = 'int16'
    sd.default.samplerate = 48000

    print()
    print(f'Selected input device: {sd.query_devices(sd.default.device[0])}')
    print()
    print()
    sd.sleep(1000)
    print(f'SoundDevice defaults: {sd.default.device} {sd.default.channels} {sd.default.dtype} {sd.default.samplerate}')
    sd.sleep(500)
    if sd.check_input_settings() is None:
        print('No issues detected by SoundDevice')
    sd.sleep(500)
    print()
    print('Testing outside Process...')
    stream = sd.InputStream()
    stream.start()
    for r in range(20):
        print(f'    Device: {stream.device}, Channels: {stream.channels}, Dtype: {stream.dtype}, Samplerate: {stream.samplerate}')
        sd.sleep(500)
    stream.close()
    print('Test done.')
    print()
    sd.sleep(500)



sdProcess = Process(target=input_test)
sdProcess.start()
sdProcess.join()


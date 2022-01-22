import sounddevice as sd
import numpy as np

def print_sound(indata, outdata, frames, time, status):
    norm = np.linalg.norm(indata)
    bars = norm * 4
    print(norm)
    print("|" * int(bars))

with sd.Stream(callback=print_sound):
    sd.sleep(10000)
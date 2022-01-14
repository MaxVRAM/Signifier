import numpy
import matplotlib.pyplot as plt

# python3 -m pip install matplotlib

mean = 0
std = 1 
num_samples = 1000
samples = numpy.random.normal(mean, std, size=num_samples)

plt.plot(samples)
plt.show()
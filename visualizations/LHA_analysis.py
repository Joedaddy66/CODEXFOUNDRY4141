import numpy as np
import matplotlib.pyplot as plt
x = np.linspace(0, 10, 500)
y = np.sin(2 * np.pi * x)
plt.plot(x, y)
plt.title('Local Harmonic Analysis')
plt.savefig('visualizations/plots/example_plot.png')

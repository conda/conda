import numpy as np
import sep

data = np.random.random((256, 256))

# Measure a spatially variable background of some image data
# (a numpy array)
bkg = sep.Background(data)

# ... or with some optional parameters
# bkg = sep.Background(data, mask=mask, bw=64, bh=64, fw=3, fh=3)

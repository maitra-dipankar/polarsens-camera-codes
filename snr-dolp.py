#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 19:11:20 2023

@author: w00322012
"""

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.visualization import ImageNormalize, ZScaleInterval, LinearStretch

fitsfile='/Users/w00322012/Downloads/2023-03-21-0126_8-Capture_00015_p000_out2.fits'
i000 = fits.getdata(fitsfile, ext=0).astype(np.float64)

fitsfile='/Users/w00322012/Downloads/2023-03-21-0126_8-Capture_00015_p045_out2.fits'
i045 = fits.getdata(fitsfile, ext=0).astype(np.float64)

fitsfile='/Users/w00322012/Downloads/2023-03-21-0126_8-Capture_00015_p090_out2.fits'
i090 = fits.getdata(fitsfile, ext=0).astype(np.float64)

fitsfile='/Users/w00322012/Downloads/2023-03-21-0126_8-Capture_00015_p135_out2.fits'
i135 = fits.getdata(fitsfile, ext=0).astype(np.float64)


# At each pixel compute the Stokes parameters and the DoLP
S0 = (i000 + i045 + i090 + i135)/2
S1 = i000 - i090
S2 = i045 - i135
dolp = np.sqrt( S1*S1 + S2*S2 ) / S0

# Also compute the uncertainties in the Stokes parameters S1 and S2
del_S1 = np.sqrt(i000 + i090)
del_S2 = np.sqrt(i045 + i135)

# Some other quantities we need for the uncertainty in DoLP
S1sq, S2sq = S1*S1, S2*S2
del_S1sq, del_S2sq = del_S1*del_S1, del_S2*del_S2
h2 = (S1sq+S2sq)
h2 = h2*h2
h2[h2 < 1] = 1      # Ensure h2 never becomes zero.

del_dolp_over_dolp_sq = (S1sq*del_S1sq + S2sq*del_S2sq)/h2 + 0.5/S0
del_dolp_over_dolp = np.sqrt(del_dolp_over_dolp_sq)
snr_dolp = 1.0/del_dolp_over_dolp

print(np.median(snr_dolp))

# Plotting
plotarr = snr_dolp
fig, ax = plt.subplots()
norm = ImageNormalize(plotarr, interval=ZScaleInterval(),
                      stretch=LinearStretch())
#im = ax.imshow(plotarr, cmap=cm.viridis, norm=norm, interpolation='none')
im = ax.imshow(plotarr, cmap=cm.viridis, vmin=3, vmax=5, interpolation='none')
fig.colorbar(im)

plt.show()
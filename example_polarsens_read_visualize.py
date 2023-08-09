#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Read a FITS or raw image from polarsens camera and visualize basic results
"""
import sys
import numpy as np
from os.path import splitext
# Import functions to analyse polarsens camera images
import polarsens_img_analysis as pia
import polarsens_visualizations as pvz


# Read FITS or raw image data, and get bits-per-pixel
fp='/path/to/sample_images/'
#ipfile = fp + 'Sharpcap-2023-03-21-0212_8-Capture_00005.fits'
ipfile = fp + 'Nina-2023-08-04_15-29-31__0.70_0.01s_0000.fits'
#ipfile = fp + 'asun20ms.raw'

extension = splitext(ipfile)[1]

if extension == '.fits':
    imgArray, bpp = pia.readFitsToNumpy(ipfile)
elif extension == '.raw':
    imgArray, bpp = pia.readRawToNumpy(ipfile)
else:
    print('Unknow file format. Has to be fits or raw')
    sys.exit(0)


nonlinear = int(0.85*np.power(2, bpp))   # Nonlinearity when ADU > nonlinear

opfile = ipfile + '.pdf'        # Output file name

# Extract subimages for different polarizer orientations
s000, s045, s090, s135 = pia.extractSubimages(imgArray)

# Bilinear interpolation to fill gaps between pixels of same orientation
o000 = pia.do_bilinear(s000, 1, 1)
o045 = pia.do_bilinear(s045, 0, 1)
o090 = pia.do_bilinear(s090, 0, 0)
o135 = pia.do_bilinear(s135, 1, 0)

av,minp,maxp,p01,p50,p99 = pia.getArrayStat(s000, bpp)

# Compute Stokes parameters, then DoLP and AoLP
S0, S1, S2 = pia.computeStokes (o000, o045, o090, o135)
DoLP = pia.computeDOLP (S0, S1, S2)
AoLP = pia.computeAOLP (S1, S2)

# Make visualizations
pvz.makePlots(imgArray, o000, o045, o090, o135, DoLP, AoLP, nonlinear, 
              opfile)

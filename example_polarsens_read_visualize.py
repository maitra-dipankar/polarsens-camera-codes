#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Read a FITS or raw image from polarsens camera and visualize basic results
"""

# Import functions to analyse polarsens camera images
import polarsens_img_analysis as pia
import polarsens_visualizations as pvz

import sys
import numpy as np

# Read FITS or raw image data, and get bits-per-pixel
ipfile = '/home/dmaitra/Downloads/2023-03-21-0212_8-Capture_00005.fits'
ipfile = '/home/dmaitra/Downloads/2023-08-04_15-29-31__0.70_0.01s_0000.fits'
imgArray, bpp = pia.readFitsToNumpy(ipfile)
#ipfile = '/home/dmaitra/Downloads/asun20ms.raw'
#imgArray, bpp = pia.readRawToNumpy(ipfile)

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
pvz.makePlots(imgArray, o000, o045, o090, o135, DoLP, AoLP, opfile)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Read a raw image from PHX050S camera and visualize basic results
"""

# Import functions to analyse polarsens camera images
import polarsens_img_analysis as pia
import polarsens_visualizations as pvz

import sys
import time
import numpy as np

ipfile = '/Users/w00322012/Downloads/arena_dm_codes/asun20ms.raw'
opfile = ipfile + '.pdf'

# Read image into numpy array
imgArray = pia.readRawToNumpy(ipfile)

# Extract subimages for different polarizer orientations
t0 = time.time()
s000, s045, s090, s135 = pia.extractSubimages(imgArray)
print('Subimages extraction time (s) = ', time.time() - t0)


t0 = time.time()
o000 = pia.do_bilinear(s000, 1, 1)
o045 = pia.do_bilinear(s045, 1, 1)
o090 = pia.do_bilinear(s090, 1, 1)
o135 = pia.do_bilinear(s135, 1, 1)
print('Bilinear interpolation time (s) = ', time.time() - t0)


# Compute Stokes parameters, then DoLP and AoLP
S0, S1, S2 = pia.computeStokes (o000, o045, o090, o135)
DoLP = pia.computeDOLP (S0, S1, S2)
AoLP = pia.computeAOLP (S1, S2)


# Make visualizations
pvz.makePlots(imgArray, o000, o045, o090, o135, DoLP, AoLP, opfile)

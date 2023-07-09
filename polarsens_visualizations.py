#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The functions defined in this file allows basic visualization of
images from polarsens cameras.

Requirement(s): numpy, matplotlib, astropy
"""

import sys
import numpy as np
from copy import copy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from astropy.visualization import (ManualInterval, MinMaxInterval, \
        ZScaleInterval, PercentileInterval, LinearStretch, ImageNormalize)

try:
    import cmocean
    cmoceanFound = True
except ModuleNotFoundError:
    print('Using hsv instead of cmocean')
    cmoceanFound = False

# Location and size of the main image and colorbar [xmin, ymin, dx, dy]   
main_axis = [0.05, 0.05, 0.75, 0.85]
cbar_axis = [0.85,0.10, 0.04,0.75]

###############
# Arrays needed to create the half-circular colorbar for AoLP maps

# Radial grid
rmin, rmax, rpts = 0.7, 1.0, 100
radii = np.linspace(rmin, rmax, rpts)

# theta values on the right side of the color circle
thpts = 500 
azimuthsR = np.linspace(-90, 91, thpts)
valuesR =  azimuthsR * np.ones((rpts, thpts))
###############

print('Creating plots')

def makePlots(fullImgArray, o000, o045, o090, o135, \
              DoLP, AoLP, opfile):
    '''
    Creates visualizations

    Parameters
    ----------
    fullImgArray, o000, o045, o090, o135, DoLP, AoLP : 2D arrays
        Arrays to display
    opfile : str
        Name of output PDF file that contains visualizations.

    Returns
    -------
    PDF file with visualizations.

    '''
    # use copy so that we do not mutate the global colormap instance
    grayCmap = copy(plt.cm.gray)

    with PdfPages(opfile) as pdf:
       
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       ax0.set_title('Raw image from sensor')
       im = ax0.imshow(fullImgArray, origin='upper', cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
    
    
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       ax0.set_title('Subimage with pixels oriented $0^\circ$, measured CCW from horizontal')
       im = ax0.imshow(o000, origin='upper', cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
    
    
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       ax0.set_title('Subimage with pixels oriented $90^\circ$, measured CCW from horizontal')
       im = ax0.imshow(o090, origin='upper', cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
    
    
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       ax0.set_title('Subimage with pixels oriented $45^\circ$, measured CCW from horizontal')
       im = ax0.imshow(o045, origin='upper', cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
    
    
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       ax0.set_title('Subimage with pixels oriented $-45^\circ$, measured CCW from horizontal')
       im = ax0.imshow(o135, origin='upper', cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
    
    
       mycmap = copy(plt.cm.viridis)
       mycmap.set_bad('w', 1.0)  
       fig = plt.figure(figsize=(10, 8), dpi=200)
       dolpmin, dolpmax = np.amin(DoLP), np.amax(DoLP)
       mynorm = ImageNormalize(DoLP, interval=ManualInterval(dolpmin, dolpmax),
                             stretch=LinearStretch())
       ax0 = fig.add_axes(main_axis)
       ax0.set_title('Degree of Linear Polarization (white pixels were nonlinear and excluded)')
       im = ax0.imshow(DoLP, origin='upper', norm=mynorm, cmap=mycmap)
    
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1)
       cbar.set_label('Degree of linear polarization (percent)')
       pdf.savefig(fig)
       plt.close()
    
    
       mycmap = copy(plt.cm.hsv)
       if cmoceanFound:
           mycmap = copy(cmocean.cm.phase)
       mycmap.set_bad('w', 1.0)   
       fig = plt.figure(figsize=(10, 8), dpi=200)
       ax0 = fig.add_axes(main_axis)
       ax0.set_title('Angle of Linear Polarization (white pixels were nonlinear and excluded)')
       im = ax0.imshow(AoLP, origin='upper', cmap=mycmap)
    
       ax1 = fig.add_axes([0.72,0.45, 0.25,0.25], projection='polar')
       ax1.grid(False)
       ax1.axis('off')
       ax1.pcolormesh(azimuthsR*np.pi/180.0, radii, valuesR, cmap=mycmap)
    
       # Label AoLP angles
       for ii in np.arange(-90, 91, 30):
           iirad = ii*np.pi/180
           ax1.plot( (iirad, iirad), (rmax-0.03, rmax+0.00), color='k', ls='-')
           ax1.plot( (iirad, iirad), (rmin-0.00, rmin+0.03), color='k', ls='-')
           labl = str(ii) + "$^\circ$"
           if np.absolute(ii)==90:
               labl = "$\pm 90^\circ$"
           ax1.text(iirad, 1.20, labl, style='italic', fontsize=12, rotation=0, 
                   horizontalalignment='center', verticalalignment='center')
           
       pdf.savefig(fig)
       plt.close()
    
    
    
       d = pdf.infodict()
       d['Title'] = 'Polarization results'
       d['Author'] = 'Wheaon Physics and Astronomy'   
       
    print('All done.')

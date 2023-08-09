#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The functions defined in this file allows basic visualization of
images from polarsens cameras.

Requirement(s): numpy, matplotlib, astropy

TBD: Combined DoLP + AoLP map
"""


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
    print('Using hsv instead of cmocean! Consider installing cmocean ...')
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


def makePlots(fullImgArray, o000, o045, o090, o135, \
              DoLP, AoLP, nonlinear, opfile):
    '''
    Creates visualizations

    Parameters
    ----------
    fullImgArray, o000, o045, o090, o135, DoLP, AoLP : 2D arrays
        Arrays to display
    nonliinear : int
        ADU above which nonlinearity set is, and hence data is bad.
    opfile : str
        Name of output PDF file that contains visualizations.

    Returns
    -------
    PDF file with visualizations.

    '''
    print('Creating plots')
    
    DPI = 100
    
    # use copy so that we do not mutate the global colormap instance
    grayCmap = copy(plt.cm.gray)
    grayCmap.set_bad('r', 1.0)
    grayCmap.set_over('r', 1.0)
    grayCmap.set_under('g', 1.0)


    with PdfPages(opfile) as pdf:
        
       # Full Image
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       pltTitle = 'Full image. Red pixels were nonlinear (>' \
           + str(nonlinear) + ' ADU)'
       ax0.set_title(pltTitle)
       mynorm = ImageNormalize(fullImgArray, interval=ManualInterval(0, \
                            nonlinear), stretch=LinearStretch())
       arr = np.where(fullImgArray > nonlinear, np.nan, fullImgArray)
       im = ax0.imshow(arr, origin='upper', norm=mynorm, cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
       
       # 0-deg image
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       pltTitle = '$0^\circ$ image. Red pixels were nonlinear (>' \
           + str(nonlinear) + ' ADU)'
       ax0.set_title(pltTitle)
       mynorm = ImageNormalize(o000, interval=ManualInterval(0, \
                            nonlinear), stretch=LinearStretch())
       arr = np.where(o000 > nonlinear, np.nan, o000)
       im = ax0.imshow(arr, origin='upper', norm=mynorm, cmap=grayCmap)
       
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()    
    
       # 90-deg image
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       pltTitle = '$90^\circ$ image. Red pixels were nonlinear (>' \
           + str(nonlinear) + ' ADU)'
       ax0.set_title(pltTitle)
       mynorm = ImageNormalize(o090, interval=ManualInterval(0, \
                            nonlinear), stretch=LinearStretch())
       arr = np.where(o090 > nonlinear, np.nan, o090)
       im = ax0.imshow(arr, origin='upper', norm=mynorm, cmap=grayCmap)
      
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()    
    
       # 45-deg image
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       pltTitle = '$45^\circ$ image. Red pixels were nonlinear (>' \
           + str(nonlinear) + ' ADU)'
       ax0.set_title(pltTitle)
       mynorm = ImageNormalize(o045, interval=ManualInterval(0, \
                            nonlinear), stretch=LinearStretch())
       arr = np.where(o045 > nonlinear, np.nan, o045)
       im = ax0.imshow(arr, origin='upper', norm=mynorm, cmap=grayCmap)
      
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()    
    
       # 135-deg image
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       cbar_label = 'Counts (ADU)'
       pltTitle = '-45$^\circ$ image. Red pixels were nonlinear (>' \
           + str(nonlinear) + ' ADU)'
       ax0.set_title(pltTitle)
       mynorm = ImageNormalize(o135, interval=ManualInterval(0, \
                            nonlinear), stretch=LinearStretch())
       arr = np.where(o135 > nonlinear, np.nan, o135)
       im = ax0.imshow(arr, origin='upper', norm=mynorm, cmap=grayCmap)
      
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label(cbar_label)
       pdf.savefig(fig)
       plt.close()
       
       # Make a mask to ignore nonlinear pixels
       maskArr = np.where(( (o000<nonlinear) & (o045<nonlinear) & \
                           (o090<nonlinear) & (o135<nonlinear) ), False, True)
       
       # DoLP image
       mycmap = copy(plt.cm.viridis)
       mycmap.set_bad('w', 1.0)
       mycmap.set_over('w', 1.0)
       mycmap.set_under('r', 1.0)
       masked = np.ma.masked_where(maskArr, DoLP)
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       dolpmin, dolpmax = 0, 100     # np.amin(DoLP), np.amax(DoLP)
       mynorm = ImageNormalize(DoLP, interval=ManualInterval(dolpmin, dolpmax),
                             stretch=LinearStretch())
       ax0 = fig.add_axes(main_axis)
       ax0.set_title('Degree of Linear Polarization. White pixels were nonlinear and excluded')
       im = ax0.imshow(masked, origin='upper', norm=mynorm, cmap=mycmap)
    
       ax1 = fig.add_axes(cbar_axis)
       cbar = fig.colorbar(im, cax=ax1, extend='both', shrink=0.9)
       cbar.set_label('Degree of linear polarization (percent)')
       pdf.savefig(fig)
       plt.close()
       
       # AoLP image
       mycmap = copy(plt.cm.hsv)
       if cmoceanFound:
           mycmap = copy(cmocean.cm.phase)
       else:
           mycmap = copy(plt.cm.hsv)

       mycmap.set_bad('w', 1.0)
       masked = np.ma.masked_where(maskArr, AoLP)
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_axes(main_axis)
       ax0.set_title('Angle of Linear Polarization. White pixels were nonlinear and excluded')
       im = ax0.imshow(masked, origin='upper', cmap=mycmap)
    
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
       
       # Histograms
       fig = plt.figure(figsize=(10, 8), dpi=DPI, clear=True)
       ax0 = fig.add_subplot(1, 1, 1)
       ax0.set_title('Histogram of pixel intensities')
       kwargs = dict(histtype='step', alpha=0.99, bins=100, log='True')
       ax0.hist(o000.ravel(), **kwargs, color='r', label='0 deg')
       ax0.hist(o045.ravel(), **kwargs, color='g', label='45 deg')
       ax0.hist(o090.ravel(), **kwargs, color='b', label='90 deg')
       ax0.hist(o135.ravel(), **kwargs, color='k', label='-45 deg')
       ax0.legend()
       ax0.set_xlabel('Pixel value (ADU)')
       ax0.set_ylabel('Number of pixels')
       pdf.savefig(fig)
       plt.close()
   
    
       d = pdf.infodict()
       d['Title'] = 'Polarization results'
       d['Author'] = 'Wheaon Physics and Astronomy'   
       
    print('All done.')

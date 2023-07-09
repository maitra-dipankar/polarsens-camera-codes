#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The functions defined in this file are to aid in analysing data
taken with polarization sensitive cameras, which contain Sony's
IMX250MZR or IMX264MZR chips. 

The top-left corner has the following pixel orientations
+-----+-----+        In general, the pixel orientations are:
|  90 |  45 |           row, col = odd, odd =>   0 deg 
+-----+-----+           row, col = evn, odd =>  45 deg
| 135 |   0 |           row, col = evn, evn =>  90 deg
+-----+-----+           row, col = odd, evn => 135 deg

Requirement(s): numpy

TBD: Handle FITS images
"""


import sys
import numpy as np

IMG_HEIGHT, IMG_WIDTH = 2048, 2448      # For IMX250MZR/IMX264MZR chip
NPIX = IMG_HEIGHT * IMG_WIDTH           # Total number of pixels

    
def readRawToNumpy(rawfile):
    '''
    Read raw binary image file from PHX050 camera into 
    a 2D numpy image array.
    

    Parameters
    ----------
    myfile : str
        Input *.raw binary image from a Lucid Vision PHX050S 
        camera containing a Sony IMX250MZR or an IMX264MZR chip.

    Returns
    -------
    Numpy 2D array of size IMG_HEIGHT rows and IMG_WIDTH columns. 
    The bit depth is 8 or 16 bits depending on the input raw image.
    '''
    binary_array = np.fromfile(rawfile, dtype='uint8')
    
    num_bytes = len(binary_array)

    if (num_bytes == NPIX):          # Mono8 format
        print('Decoding 8-bit image:', rawfile)
        img_arr_1d = binary_array
    
    elif (num_bytes == 2*NPIX):      # Mono12 format
        print('Decoding 12-bit image:', rawfile)
    
        # Select even bytes, i.e. the 0th, 2nd, 4th, 6th, ...
        # and the odd bytes, i.e. the 1st, 3rd, 5th, 7th, ...
        evn_arr = binary_array[0::2].copy()
        odd_arr = binary_array[1::2].copy()

        # Recast odd/even arrays as larget 16-bit integer arrays because an 
        # 8-bit integer array can store from 0 to 255 only whereas we 
        # need to store bigger numbers when working with 12-bit integers.
        evn_arr = evn_arr.astype('int16')
        odd_arr = odd_arr.astype('int16')

        # Shift the odd bytes 8 binary digits and then add to the even 
        # byte to get the 12-bit pixel value.
        pix_val = (odd_arr << 8) + evn_arr
        img_arr_1d = pix_val
    
    else:
        print('Unrecognized image format')
        sys.exit(0)

    # Reshape 1D array img_arr_1d to 2D image array
    img_array_2d = img_arr_1d.reshape(IMG_HEIGHT, IMG_WIDTH)
    
    return img_array_2d


def extractSubimages(img_array_2d):
    '''
    Extracts subimages corresponding to different polarizer orientations.
    
    Parameters
    ----------
    img_array_2d : 8 or 16 bit
        Numpy array 

    Returns
    -------
    Subarrays/subimages orient000, orient045, orient090, and
    orient135, corresponding to pixel with 0, 45, 90, and 135
    degree orientation.

    '''
    orient090 = img_array_2d[::2,   ::2].astype('float64')
    orient045 = img_array_2d[::2,  1::2].astype('float64')
    orient135 = img_array_2d[1::2,  ::2].astype('float64')
    orient000 = img_array_2d[1::2, 1::2].astype('float64')
    
    return orient000, orient045, orient090, orient135


def do_bilinear(orientX, rowOffset, colOffset):
    '''
    Carries out bilinear interpolation.

    Parameters
    ----------
    orientX: float64
        2D array of pixels extracted for any given polarization
        orientation.
    
    rowOffset, colOffset: each is an int, defined as below.
        img_array[rowOffset][colOffset] = orientX[0][0]

    Returns
    ------
    trimmedX: float64
        2D array such that any array element gives the pixel
        value for the input orientation, at the full resolution of the
        CMOS sensor. However the top, bottom, left, and right row/column are
        trimmed because not all edges contain useful information about all
        orientations. Therefore the dimensions of trimmedX are 2*nr - 2 rows
        and 2*nc - 2 columns, where nr and nc are the number of rows and 
        columns of the input array orientX.
    '''

    nr, nc = orientX.shape[0], orientX.shape[1]

    top = orientX[:-1, :]      # delete last row
    bot = orientX[1:, :]       # delete first row
    vAv = (top+bot)/2          # interpolated values vertically above/below

    left = orientX[:, :-1]     # delete right-most column
    rght = orientX[:, 1:]      # delete left-most column
    hAv  = (left+rght)/2       # interpolated values horizontally between

    vAv_r = vAv[:, :-1]        # delete the right-most column of vAv
    vAv_l = vAv[:, 1:]         # delete the left-most column of vAv
    midPt = (vAv_r+vAv_l)/2    # interpolated values in the middle of 4 pix

    # Now start placing these in the right places
    orientXfull = np.zeros((2*nr-1, 2*nc-1), dtype='float64')
    orientXcmos = np.zeros((2*nr, 2*nc), dtype='float64')

    # orientX inserted in orientXfull at every row,col = evn,evn
    orientXfull[0::2, 0::2] = orientX

    # vAv inserted in orientXfull at every row,col = odd, evn
    orientXfull[1::2, 0::2] = vAv

    # hAv inserted in orientXfull at every row,col = evn, odd
    orientXfull[0::2, 1::2] = hAv

    # mid inserted in orientXfull at every row,col = odd, odd
    orientXfull[1::2, 1::2] = midPt

    # Apply offset to put the array on the entire CMOS array
    orientXcmos[rowOffset : 2*nr - 1 + rowOffset : 1, \
        colOffset : 2 * nc - 1 + rowOffset : 1] = orientXfull

    # Trim the edges because not all edges will contain useful
    # information about all orientations
    trimmedX = orientXcmos[1:-1, 1:-1]

    return trimmedX


def computeStokes (orient000, orient045, orient090, orient135):
    '''
    Computes the Stokes parameters given subimages with different 
    polarizer orientations.

    Parameters
    ----------
    orient000, orient090, orient090, orient135 : All are float64
        2D arrays for different polarizer orientations

    Returns
    -------
    S0,S1,S2 : float64
        2D arrays with Stokes parameters
    '''
    S0 = (orient000 + orient045 + orient090 + orient135)/2
    S1 = orient000 - orient090
    S2 = orient045 - orient135
    
    return S0, S1, S2
    

def computeDOLP (S0, S1, S2):
    '''
    Given Stokes parameters S0, S1, and S2, returns the percentage 
    Degree of Linear Polarization (DOLP) at each pixel.

    Parameters
    ----------
    S0, S1, S2 : float64
        2D arrays with Stokes parameters

    Returns
    -------
    DOLP : float64
        2D array with percent DOLP values at each pixel.

    '''
    DOLP = 100.0*(np.sqrt((S1*S1) + (S2*S2)))/S0
    
    return DOLP


def computeAOLP (S1, S2):
    '''
    Given Stokes parameters S1 and S2, returns the Angle of Linear 
    Polarization (AOLP) at each pixel, in degrees.

    Parameters
    ----------
    S0, S1, S2 : float64
        2D arrays with Stokes parameters

    Returns
    -------
    AOLP : float64
        2D array with AOLP values at each pixel, in degrees

    '''
    AOLP = np.rad2deg( 0.5 * np.arctan2(S2, S1) )
    
    return AOLP

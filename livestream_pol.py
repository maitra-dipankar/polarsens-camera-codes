#!/usr/bin/env python3

'''
Goal: Start livestreaming DoLP values from the connected PHX050S camera
      with specified gain. Nonlinear (>80% saturation) pixels can be
      displayed in red.
'''

import sys
import argparse
import numpy as np
from datetime import datetime
from arena_api.system import system
from arena_api.buffer import *
import ctypes

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

try:
    import cmocean
    cmoceanFound = True
except ModuleNotFoundError:
    print('Using hsv instead of cmocean! Consider installing cmocean...')
    cmoceanFound = False

from copy import copy
from astropy.visualization import (ManualInterval, ImageNormalize,
        LinearStretch)
from mpl_toolkits.axes_grid1 import make_axes_locatable


# Nonlinear pixels are >=80% of saturation
nlin = 0.8*255    

def getArgs(argv=None):
    descr='Start livestreaming from the connected PHX050S camera, given \
        the gain.\
        For example "python %(prog)s -g 7 -n" starts livestreaming\
        from the camera at 7 dB gain, showing nonlinear pixels\
        in red.'
    parser = argparse.ArgumentParser(description=descr)
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-g', 
            type=float, 
            required=True, 
            dest='gain',
            help="Gain in dB. A float between [0 : 24]")
    parser.add_argument('-n',
            required=False,
            action='store_true',
            dest='markNL',
            help="mark non-linear pixels or not")

    args = parser.parse_args(argv)

    # Some further sanity checks on inputs
    if args.gain < 0 or args.gain > 24:
        print('Gain has to be between 0 and 24 dB.')
        sys.exit(0)

    return args.gain, args.markNL


def create_devices_with_tries():
    '''
    Waits for the user to connect a device before raising an
    exception if it fails
    '''
    tries = 0
    tries_max = 3
    sleep_time_secs = 10
    while tries < tries_max:  # Wait for device for 30 seconds
        devices = system.create_device()
        if not devices:
            print(
                    f'Try {tries+1} of {tries_max}: waiting for {sleep_time_secs} '
                    f'secs for a device to be connected!')
            for sec_count in range(sleep_time_secs):
                time.sleep(1)
                print(f'{sec_count + 1 } seconds passed ',
                        '.' * sec_count, end='\r')
                tries += 1
        else:
            return devices
    else:
        raise Exception('No device found! Please connect a device and run ')


def getHalfResStokesFromFullResImage(img_array):
    orient_090 = img_array[::2,   ::2].astype('float64')
    orient_045 = img_array[::2,  1::2].astype('float64')
    orient_135 = img_array[1::2,  ::2].astype('float64')
    orient_000 = img_array[1::2, 1::2].astype('float64')

    # Compute Stokes parameters
    S0 = (orient_000 + orient_045 + orient_090 + orient_135)/2
    S1 = orient_000 - orient_090
    S2 = orient_045 - orient_135

    return S0, S1, S2


def getDolpFromStokes(S0, S1, S2):
    dolp = 100.0*(np.sqrt((S1*S1) + (S2*S2)))/(S0+1)
    return dolp


def getAolpFromStokes(S0, S1, S2):
    aolp = np.rad2deg( 0.5 * np.arctan2(S2, S1) )
    return aolp


def setup(device, gain):
    """
    Setup stream dimensions and stream nodemap
        num_channels changes based on the PixelFormat
        Mono 8 would have 1 channel, RGB8 has 3 channels

    """
    nodemap = device.nodemap
    nodes = nodemap.get_node(['Width', 'Height', 'PixelFormat', 'Gain',
        'DeviceSerialNumber'])

    nodes['Width'].value = 2448
    nodes['Height'].value = 2048
    nodes['PixelFormat'].value = 'Mono8'
    nodes['Gain'].value = gain

    num_channels = 1

    # Stream nodemap
    tl_stream_nodemap = device.tl_stream_nodemap

    tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"
    tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
    tl_stream_nodemap['StreamPacketResendEnable'].value = True

    return num_channels


def on_close(event):
    print('Type CTRL-c to stop.')
    

def livestream(gain, markNL):
    devices = create_devices_with_tries()
    device = devices[0]
    num_channels = setup(device, gain)

    # Set up the display
    res = np.ones((2048, 2448), dtype='float64')
    fig,axes = plt.subplots(nrows=2, ncols=1, figsize=(8, 9))
    axes[0].axis('off')
    divider0 = make_axes_locatable(axes[0])
    cbar_ax0 = divider0.append_axes('right', size='5%', pad=0.05)
    divider1 = make_axes_locatable(axes[1])
    cbar_ax1 = divider1.append_axes('right', size='5%', pad=0.05)

    # DoLP
    axes[0].title.set_text('Degree of Linear Polarization (percent)')
    dcmap = copy(plt.cm.viridis)
    dnorm = ImageNormalize(res, interval=ManualInterval(0, 100),
                     stretch=LinearStretch())
    im0 = axes[0].imshow(res, origin='upper', norm=dnorm, cmap=dcmap)
    cbar0 = fig.colorbar(im0, cax=cbar_ax0)
    cbar0.set_label('DoLP (percent)')

    # AoLP
    axes[1].title.set_text('Angle of Linear Polarization (degrees)')
    if cmoceanFound:
        acmap = copy(cmocean.cm.phase)
    else:
        acmap = copy(plt.cm.hsv)
      
    anorm = ImageNormalize(res, interval=ManualInterval(-90, 90),
                         stretch=LinearStretch())
    im1 = axes[1].imshow(res, origin='upper', norm=anorm, cmap=acmap)
    cbar1 = fig.colorbar(im1, cax=cbar_ax1)
    cbar1.set_label('AoLP (degrees)')

    fig.tight_layout()
    cid = fig.canvas.mpl_connect('close_event', on_close)

    with device.start_stream():
        # Infinitely fetch and display buffer data until ctrl-c
        try:
            while True:
                buffer = device.get_buffer()
                # Copy buffer and requeue to avoid running out of buffers
                item = BufferFactory.copy(buffer)
                device.requeue_buffer(buffer)

                #Buffer data as cpointers can be accessed using buffer.pbytes
                array = (ctypes.c_ubyte * num_channels * item.width * \
                        item.height).from_address(ctypes.addressof(item.pbytes))
                
                #Create a reshaped NumPy array
                nparray = np.ndarray(buffer=array, dtype=np.uint8, \
                        shape=(item.height, item.width))

                # Compute D/AoLP 
                S0, S1, S2 = getHalfResStokesFromFullResImage(nparray)
                res = getDolpFromStokes(S0, S1, S2)
                im0.set_data(res)
                res = getAolpFromStokes(S0, S1, S2)
                im1.set_data(res)

                plt.show(block=False)
                plt.pause(1e-2)
                
                #Destroy the copied item to prevent memory leaks
                BufferFactory.destroy(item)
 
        except KeyboardInterrupt:
            device.stop_stream()
            system.destroy_device()
            print('\nStopped streaming.')



if __name__ == '__main__':
    if len(sys.argv)<=1:
        print('Type "progname -h" or "python3 progname -h" for help.')
        sys.exit(1)

    myGain, marker = getArgs()   # Read command line inputs
    livestream(myGain, marker)   # Start livestream


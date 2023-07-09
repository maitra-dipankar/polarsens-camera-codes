#!/usr/bin/env python3

import sys
import time
import argparse
import numpy as np
import ctypes  # ctypes.cast(), ctypes.POINTER(), ctypes.c_ushort
from astropy.io import fits
from astropy.time import Time
from arena_api.system import system

'''
Single image acquisition given exposure time, gain, and 
offset (black level). The saved image buffer is written
as a FITS file. For usage help type in terminal
 python takeimage.py -h
'''


def update_create_devices():
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


def acquire_and_save_image(device, exptime_s, offset_adu, gain):

    # Get device nodemap to get, and set imaging parameters
    devmap = device.nodemap

    # Make sure to get 2448x2048, Mono12 images
    nodes = devmap.get_node(['Width', 'Height', 'PixelFormat',
                             'DeviceTemperature', 'AcquisitionFrameRate',
                             'ExposureTime', 'BlackLevelRaw', 'Gain',
                             'DeviceSerialNumber','DeviceModelName',
                             'DevicePower'])
    nodes['Width'].value = nodes['Width'].max
    nodes['Height'].value = nodes['Height'].max
    nodes['PixelFormat'].value = 'Mono12'

    devtemp = nodes['DeviceTemperature'].value

    # Enable frame rate change, if needed
    if devmap['AcquisitionFrameRateEnable'].value is False:
        devmap['AcquisitionFrameRateEnable'].value = True

    # Make sure the framerate is such that an exposure can be taken between 
    # between two succesive frames
    framerate = 0.90 / exptime_s

    # However don't go beyond the camera's maximum frame rate
    maxframerate = nodes['AcquisitionFrameRate'].max
    if framerate > maxframerate :
        framerate = maxframerate

    nodes['AcquisitionFrameRate'].value = framerate
        
    # Turn off auto exposure [possibilities are Continuous or Off]
    # And check to make sure we can change the exposure time
    if devmap['ExposureAuto'].value == 'Continuous':
        devmap['ExposureAuto'].value = 'Off'
    if devmap['ExposureTime'] is None:
        raise Exception("ExposureTime node not found")
    if devmap['ExposureTime'].is_writable is False:
        raise Exception("ExposureTime node is not writable")
    
    # Set the exposure time (internally in microseconds)
    nodes['ExposureTime'].value = exptime_s * 1e6
    
    # Set the black level (offset) in ADU
    nodes['BlackLevelRaw'].value = offset_adu
    
    # Turn off automatic gain [possibilities are Continuous or Off]
    if devmap['GainAuto'].value == 'Continuous':
        devmap['GainAuto'].value = 'Off'
        
    nodes['Gain'].value = gain
        
    # Get stream nodemap to set features before streaming
    stream_nodemap = device.tl_stream_nodemap
    
    # Enable stream auto negotiate packet size and packet resend
    stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
    stream_nodemap['StreamPacketResendEnable'].value = True

    # Double check and print exposure essentials
    exptime = nodes['ExposureTime'].value/1e6
    offset  = nodes['BlackLevelRaw'].value
    gain    = nodes['Gain'].value
    devSrl  = nodes['DeviceSerialNumber'].value
    devModel= nodes['DeviceModelName'].value
    devPower= nodes['DevicePower'].value

    print('Images:', nodes['Width'].value, 'x',  nodes['Height'].value,
          nodes['PixelFormat'].value,
          '\nTemperature (C)\t=', devtemp, 
          '\nFramerate (Hz) \t=', nodes['AcquisitionFrameRate'].value, 
          '\nExptime (s)    \t=', exptime,
          '\nOffset (ADU)   \t=', offset,
          '\nGain (dB)      \t=', gain)

    
    '''
    Acquire Image
    Once a device is created, use get_buffer to acquire the image and requeue
    the buffer so that the next image can be added
    '''
    with device.start_stream(1):
        buffer = device.get_buffer()
        t = Time.now()    # Get the time right after getting the buffer
        mjd_now = t.mjd
        utc_now = t.isot

        # The two lines below recasts the buffer as a numpy array
        # of data type unit16
        pdata_as16 = ctypes.cast(buffer.pdata, 
                                 ctypes.POINTER(ctypes.c_ushort))
        nparray_reshaped = np.ctypeslib.as_array(pdata_as16,
                            (buffer.height, buffer.width))
        
        # Save the numpy array as a FITS image with some metadata
        save2fits(nparray_reshaped, utc_now, mjd_now, exptime, 
                offset, gain, devtemp, devPower, devSrl, devModel)

        
        # Requeue to release buffer memory
        device.requeue_buffer(buffer)
    
    return 0



def save2fits(imgarray, utc_isot, mjd, exptime_s, offset_adu, gain_db,
        sensor_temp, dev_power, dev_serial, dev_model):
    '''
    Each camera needs to have its own filter hardcoded.
    The goal is to write the FITS as quickly as possible, so we supply
    both UTC and MJD of observation.
    '''
    #The chip name is figured out from dev_model
    if dev_model == "PHX050S-P":
        chip = "IMX250MZR"
    elif dev_model == "PHX050S1-P":
        chip = "IMX264MZR"
    else:
        print('No good camera. Quitting...')
        sys.exit(0)
    
 
    
    opfile = 'p' + str(mjd) + '.fits'  # Create output FITS filename

    # Force FITS scaling to be bscale=1 and bzero=0
    hdu = fits.PrimaryHDU(data=imgarray, do_not_scale_image_data=True)
    hdu.scale(bzero=0)

    # Create the header
    hdr = hdu.header
    hdr['BSCALE']   = 1
    hdr['BZERO']    = 0
    hdr['DATE-OBS'] = (utc_isot,       'UTC of exposure start')
    hdr['MJD']      = (mjd,            'MJD of exposure start')
    hdr['EXPTIME']  = (exptime_s,      'Exposure time [s]')
    hdr['OFFSET']   = (offset_adu,     'Black-level offset [ADU]')
    hdr['GAIN']     = (gain_db,        'Gain [dB]')
    hdr['DET-TEMP'] = (sensor_temp,    'Detector temperature [C]')
    hdr['DEV-PWR']  = (dev_power,      'Device power [Watts]')
    hdr['DET-MAC']  = ('1C0FAF699E85', 'MAC address of detector')
    hdr['DET-SRL']  = (dev_serial,     'Serial number of detector')
    hdr['DET-MDL']  = (dev_model,      'Model of device')
    hdr['CHIPNAME'] = (chip,           'Sony CMOS chip name')
    hdr['PIX-SIZE'] = (3.45,           'Detector pixel size [microns]')
    hdr['BITDEPTH'] = (12,             'Detector bit depth per pixel')
    hdr['SWCREATE'] = ('ArenaSDK',     'Software used for acquisition')
    hdr['TELESCOP'] = ('RedCat 51',    'Telescope name')
    hdr['APERTURE'] = (51,             'Telescope diameter [mm]')
    hdr['FOCALLEN'] = (250,            'Telescope focal length [mm]')
    hdr['FILTER']   = ('R/G/B',        'Chroma R/G/B filter')
    hdr['PLATESCL'] = (2.85,           'Plate scale [arcsec/pixel]')
    hdr['HFOV']     = (1.94,           'Horizontal FOV [degrees]')
    hdr['VFOV']     = (1.62,           'Vertical FOV [degrees]')
    hdr['SITE-LAT'] = ('00.00000',     'Latitude of site [degrees]')
    hdr['SITE-LON'] = ('00.00000',     'Longitude of site [degrees]')
    hdr['SITE-ALT'] = ('00.00000',     'Altitude of site [meters]')

    hdu.writeto(opfile, overwrite=False)


def getArgs(argv=None):
    descr='Take an image with the PHX050S camera, given \
        exposure time in seconds, offset in ADUs, and the   \
        gain in dB. \
        For example "python %(prog)s -e 1.5 -o 200 -g 7" takes\
        a 1.5 second exposure with 200 ADU offset and 7 dB gain.'
    parser = argparse.ArgumentParser(description=descr)
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-e', 
            type=float, 
            required=True, 
            dest='exp',
            help="Exposure time in seconds. A real number between [0.001 : 10]")
    requiredNamed.add_argument('-o', 
            type=int, 
            required=True, 
            dest='offset',
            help="Offset in ADU. An integer between [0 : 500]")
    requiredNamed.add_argument('-g', 
            type=float, 
            required=True, 
            dest='gain',
            help="Gain in dB. An integer between [0 : 24]")

    args = parser.parse_args(argv)

    # Some further sanity checks on inputs
    if args.exp < 0.001 or args.exp > 10:
        print('Exposure time has to be between 0.001 and 10 seconds.')
        sys.exit(0)
    if args.offset < 0 or args.offset > 500:
        print('Offset has to be between 0 and 500 ADU.')
        sys.exit(0)
    if args.gain < 0 or args.gain > 24:
        print('Gain has to be between 0 and 24 dB.')
        sys.exit(0)

    return args.exp, args.offset, args.gain


if __name__ == '__main__':

    # Get/set exposure time, offset, gain for the image
    myexptime_s, myoffset_adu, mygain_db = getArgs()

    print('\nExample started\n')
    mydevices = update_create_devices()      # Get connected devices
    mydevice = mydevices[0]                  # Get the device
    
    acquire_and_save_image(mydevice, myexptime_s, myoffset_adu, mygain_db)

    # Clean up
    system.destroy_device() 
    
    print('\nExample finished successfully')


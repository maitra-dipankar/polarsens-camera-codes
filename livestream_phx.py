#!/usr/bin/env python3
'''
Goal: Start livestreaming from a specified (r or g or b) camera with a
      specified gain. Nonlinear (>80% saturation) pixels can be displayed
      in red.

Hardware info: the serial numbers of the r, g, and b cameras are hardcoded
      in the global array variable rgbSerial.

2023-Jun-27: First working version (DM)

TBD:
* Show zoom/panel icons in window (near top).
'''

import sys
import argparse
import numpy as np
from datetime import datetime
from arena_api.system import system
from arena_api.buffer import *
import ctypes
import cv2

# Serial numbers of the cameras, in [r, g, b] order
rgbSerial = np.array([213301046, 211300110, 223200097])

# Nonlinear pixels are >=80% of saturation
nlin = 0.8*255    


if len(sys.argv)<=1:
    print('Type "progname -h" or "python3 progname -h" for help.')
    sys.exit(1)


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


def setup(device, exptime_s, gain):
    """
    Setup stream dimensions and stream nodemap
        num_channels changes based on the PixelFormat
        Mono 8 would have 1 channel, RGB8 has 3 channels
    """
    nodemap = device.nodemap

    # Turn off automatic gain [possibilities are Continuous or Off]
    if nodemap['GainAuto'].value == 'Continuous':
        nodemap['GainAuto'].value = 'Off'
 
    nodes = nodemap.get_node(['Width', 'Height', 'PixelFormat', 'Gain',
        'DeviceSerialNumber','ExposureTime','AcquisitionFrameRate'])

    nodes['Width'].value = 2448
    nodes['Height'].value = 2048
    nodes['PixelFormat'].value = 'Mono8'
    nodes['Gain'].value = gain

    # Enable frame rate change, if needed
    if nodemap['AcquisitionFrameRateEnable'].value is False:
        nodemap['AcquisitionFrameRateEnable'].value = True
 
    # Make sure the framerate is such that an exposure can be taken between 
    # between two succesive frames
    framerate = 0.90 / exptime_s

    # However don't go beyond the camera's max/min frame rate limits
    maxframerate = nodes['AcquisitionFrameRate'].max
    if framerate > maxframerate :
        framerate = maxframerate
    minframerate = nodes['AcquisitionFrameRate'].min
    if framerate < minframerate :
        framerate = minframerate

    nodes['AcquisitionFrameRate'].value = framerate

    # Turn off auto exposure [possibilities are Continuous or Off]
    # And check to make sure we can change the exposure time
    if nodemap['ExposureAuto'].value == 'Continuous':
        nodemap['ExposureAuto'].value = 'Off'
    if nodemap['ExposureTime'] is None:
        raise Exception("ExposureTime node not found")
    if nodemap['ExposureTime'].is_writable is False:
        raise Exception("ExposureTime node is not writable")
    
    # Set the exposure time (internally in microseconds)
    nodes['ExposureTime'].value = exptime_s * 1e6
    
    num_channels = 1

    # Stream nodemap
    tl_stream_nodemap = device.tl_stream_nodemap

    tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"
    tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
    tl_stream_nodemap['StreamPacketResendEnable'].value = True

    return num_channels


def getSerial(devices):
    nDevFound = len(devices)
    detectedSerials = np.zeros(nDevFound, dtype=np.uint32)
    ii=0
    for device in devices:
        detectedSerials[ii] = \
                device.nodemap.get_node("DeviceSerialNumber").value
        ii+=1

    return detectedSerials


def cameraToSerial(camName):
    # Given camera name (r or g or b),
    # return the serial number of that camera.
    if camName == 'r':
        serial = rgbSerial[0]
    elif camName == 'g':
        serial = rgbSerial[1]
    elif camName == 'b':
        serial = rgbSerial[2]
    else:
        print('This should not happen. Quitting')
        sys.exit(0)

    return serial


def serialToCamera(serial):
    # Given camera's serial number, return the camera name
    if serial == rgbSerial[0]:
        name = 'r'
    elif serial == rgbSerial[1]:
        name = 'g'
    elif serial == rgbSerial[2]:
        name = 'b'
    else:
        print('This should not happen. Quitting')
        sys.exit(0)

    return name


def findCamInDetectedDeviceList (camSrl, detectedDeviceList):
    '''
    Search for camera with serial number camSrl in the list of detected
    devices. Note that np.where returns a tuple, hence the [0] at end.
    '''
    devNum = np.where(detectedDeviceList == camSrl)[0]

    # A couple of sanity checks
    if len(devNum) == 0:
        print('Specified camera not detected. Quitting...')
        sys.exit(0)
    if len(devNum)  > 1:
        print('Multiple cameras with same serial. Quitting...')
        sys.exit(0)

    return devNum[0]
    
def livestream(cam, exptime_s, gain, markNL):

    # Find all connected devices and get their serial numbers
    devices = create_devices_with_tries()
    srlDetected = getSerial(devices)

    # if cam is a camera name
    if cam == 'r' or cam == 'g' or cam == 'b':    
        # Get serial number of requested camera and look 
        # for requested camera in detected device list
        camSrl = cameraToSerial(cam)  
        devNum = findCamInDetectedDeviceList (camSrl, srlDetected)
        camName = cam

    # otherwise, if cam is a detected-device-number
    elif cam == '0' or cam == '1' or cam == '2':
        devNum = int(cam)
        camSrl = srlDetected[devNum]
        camName = serialToCamera(camSrl)

    # problem
    else:
        print('Ill-defined cam. Quitting...')
        sys.exit(0)


    print('The',camName, 'camera with serial number',camSrl,\
        'is device[', devNum,']')
    print('Now starting live stream from this camera.')

    device = devices[devNum]
    num_channels = setup(device, exptime_s, gain)
    expStr  = " Exptime_s= {0:.2f}".format(exptime_s)
    gainStr = " Gain= {0:.1f}".format(gain)
    devStr  = " dev[" + str(devNum) + "]"
    escStr  = " Press ESC to quit."
    combStr = camName + devStr + expStr + gainStr + escStr

    if markNL is True:  # Mark nonlinear pixels as red
        window_title = "Camera: " + combStr + \
                ' Red pixels => nonlinear'
    else:
        window_title = "Camera=" + combStr

    with device.start_stream():
        """
        Infinitely fetch and display buffer data until esc is pressed
        """
        while True:
            buffer = device.get_buffer()
            """
            Copy buffer and requeue to avoid running out of buffers
            """
            item = BufferFactory.copy(buffer)
            device.requeue_buffer(buffer)

            buffer_bytes_per_pixel = int(len(item.data)/(item.width * \
                    item.height))
            """
            Buffer data as cpointers can be accessed using buffer.pbytes
            """
            array = (ctypes.c_ubyte * num_channels * item.width * \
                    item.height).from_address(ctypes.addressof(item.pbytes))
            """
            Create a reshaped NumPy array to display using OpenCV
            """
            npndarray = np.ndarray(buffer=array, dtype=np.uint8, \
                    shape=(item.height, item.width, buffer_bytes_per_pixel))
            
            tNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Resize to fit on screen
            frac = 0.3
            imS = cv2.resize(npndarray, (0,0), fx=frac, fy=frac)

            if markNL is True:  # Mark nonlinear pixels as red
                # First convert grayscale to RGB 
                imS = cv2.cvtColor(imS, cv2.COLOR_GRAY2RGB)

                # Then color all nonlinear pixels red
                res = np.where(imS[...,[0]]>nlin, \
                        (0,0,255), imS).astype(np.uint8)
            else:
                res = imS

            cv2.putText(res, tNow, (7, 50), cv2.FONT_HERSHEY_SIMPLEX, \
                    0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow(window_title, res)

            #Destroy the copied item to prevent memory leaks
            BufferFactory.destroy(item)

            #Break if esc key is pressed
            key = cv2.waitKey(1)
            if key == 27:
                break
            
        device.stop_stream()
        cv2.destroyAllWindows()
    
    system.destroy_device()


def getArgs(argv=None):
    descr='Start livestreaming from a specified PHX050S camera. For example\
        "python %(prog)s -c r -g 7 -e 0.05 -n" starts livestreaming\
        from the Red (r) camera at 7 dB gain, 0.05 s exposure, showing\
        nonlinear pixels in red.'
    parser = argparse.ArgumentParser(description=descr)
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-c', 
            type=str.lower, 
            required=True, 
            dest='cam',
            help="Camera name. Has to be either r/g/b/0/1/2.")
    requiredNamed.add_argument('-e', 
            type=float, 
            required=True, 
            dest='exp',
            help="Exposure time in seconds. A real number between [0.001 : 10]")
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
    if args.cam != 'r' and args.cam != 'g' and args.cam != 'b' and \
            args.cam != '0' and args.cam != '1' and args.cam != '2':
                print('Camera has to be one of r/g/b/0/1/2.')
                sys.exit(0)
    if args.gain < 0 or args.gain > 24:
        print('Gain has to be between 0 and 24 dB.')
        sys.exit(0)
    if args.exp < 0.001 or args.exp > 10:
        print('Exposure time has to be between 0.001 and 10 seconds.')
        sys.exit(0)

    return args.cam, args.exp, args.gain, args.markNL




if __name__ == '__main__':
    myCam, myExp, myGain, marker = getArgs()   # Read command line inputs
    livestream(myCam, myExp, myGain, marker)   # Start livestream

    # Ask whether to stream another camera or quit
    while True:
        res = input('Press q to quit, or r/g/b/0/1/2 exp gain to restart: ')
        inp = res.split()
        if len(inp) == 1 and inp[0] == 'q':
            print('All done. Quitting ...')
            sys.exit(0)
        elif len(inp) == 3:
            myCam, myExp, myGain = inp[0], float(inp[1]), float(inp[2])
        else:
            print('Input not in "r/g/b/0/1/2 exp gain" format. Quitting...')
            sys.exit(0)

        if myGain < 0 or myGain > 24:
            print('Bad gain. Need [0:24]. Quitting...')
            sys.exit(0)
        elif myExp < 0.001 or myExp > 10:
            print('Bad exposure. Need [0.001:10]. Quitting...')
            sys.exit(0)
        else:
            livestream(myCam, myExp, myGain, marker)



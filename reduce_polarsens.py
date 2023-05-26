'''
Reduces observations made with the QHY550P camera.
File or folder names should not contain spaces!
Assumes user says that the FITS frames from the QHY550P camera is in
     datadir, which is organized as below:
     datadir/Bias         includes the bias frames,
     datadir/Darks        includes the dark frames,
     datadir/Flats        includes the flat frames,
     datadir/Science      includes the science frames.

Then in a user specified path opdir this function splits the frames 
into pXXX = (p000 & p045 & p090 & p135) subdirectories such that
     opdir/pXXX/Bias         includes the bias frames,
     opdir/pXXX/Darks        includes the dark frames,
     opdir/pXXX/Flats        includes the flat frames,
     opdir/pXXX/Science      includes the science frames.

Thereafter it calibrates the science images via bias- and dark-subtraction,
and flat-correction.

TBD: 
- Create AoLP images from the calibrated science images.
- Read FITS produced by Lucidvision Cameras as well.
'''

import os, sys, glob, shutil
import numpy as np
import ccdproc as ccdp
from astropy.io import fits
from astropy import units as u
from astropy.stats import mad_std
from astropy.nddata import CCDData

angles = ["p000", "p045", "p090", "p135"]

def inv_median(a):
    return 1 / np.median(a)      #Normalize the flats by their median value


def split_poldata(datadir, opdir):
    '''
    Assumes user says that the FITS frames from the QHY550P camera is in
     datadir, which is organized as below:
     datadir/Bias         includes the bias frames,
     datadir/Darks        includes the dark frames,
     datadir/Flats        includes the flat frames,
     datadir/Science      includes the science frames.

    Then in a user specified path opdir this function splits the frames 
    into pXXX = (p000 & p045 & p090 & p135) subdirectories such that
     opdir/pXXX/Bias         includes the bias frames,
     opdir/pXXX/Darks        includes the dark frames,
     opdir/pXXX/Flats        includes the flat frames,
     opdir/pXXX/Science      includes the science frames.
    '''
   
    subdirs = ["Science", "Bias", "Darks", "Flats"]

    # Check if all data and calibration directories exist
    for dirs in subdirs:
        checkPath = os.path.join(datadir, dirs)
        if not os.path.exists(checkPath):
            print(checkPath, ' not found. Quitting.')
            sys.exit(0)

    # Create the output directories fresh every time
    if os.path.exists(opdir):
        print('Deleting',opdir,'and recreating ...')
        shutil.rmtree(opdir)

    for ang in angles:
        for dirs in subdirs:
            mkDir = os.path.join(opdir,ang,dirs)
            os.makedirs(mkDir, exist_ok=True)

    # Make a list of the raw FITS images in each of the different 
    # kinds of images in subdirs
    for ii in subdirs:     # Loop over Science and Calib subdirectories
        rawPath = os.path.join(datadir, ii)
        rawFiles = sorted(glob.glob(rawPath + "/*.fits"))
        for image in rawFiles:
            print(image)

            # Read header and data in image
            img_array_raw, header = fits.getdata(image, ext=0, header=True)

            # Create names of the split files
            split_tup = os.path.splitext(image)
            op_000 = os.path.basename( split_tup[0] + '_p000.fits')
            op_090 = os.path.basename( split_tup[0] + '_p090.fits')
            op_045 = os.path.basename( split_tup[0] + '_p045.fits')
            op_135 = os.path.basename( split_tup[0] + '_p135.fits')

            # Append the full path for these split files
            op_000 = os.path.join(opdir,'p000',ii,op_000)
            op_045 = os.path.join(opdir,'p045',ii,op_045)
            op_090 = os.path.join(opdir,'p090',ii,op_090)
            op_135 = os.path.join(opdir,'p135',ii,op_135)

            # Split each raw image into four angles

            # Determine whether the image was created using NINA or SharpCap
            sw = fits.getval(image, 'SWCREATE', ext=0)
            if (sw.find('SharpCap') != -1):
                print('Reading FITS image taken with SharpCap')
        
                # Crop image to keep good region
                img_data = img_array_raw[0:-22, 0:-12]
        
                # Get rid of some junk header keywords inserted by SharpCap
                header.pop('COLORTYP', None)
                header.pop('XBAYROFF', None)
                header.pop('YBAYROFF', None)
                header.pop('YBAYROFF', None)
                header.pop('BAYOFFX', None)
                header.pop('BAYOFFY', None)
                header.pop('BAYERPAT', None)
    

            elif (sw.find('N.I.N.A.') != -1):
                print('Reading FITS image taken with NINA')
        
                # Crop image to keep good region
                img_data = img_array_raw[22:, 12:]
        
            else:
                print('Neither SharpCap nor NINA! Quitting ...')
                sys.exit(0)

            # Divide by 16 (= 2^16 / 2^12) because the FITS files are
            # stretched to 16 bits/pixel whereas the CMOS is 12 bpp!
            img_data_scaled = img_data/16
            img_data_scaled = img_data_scaled.astype('int16')
    
            # Extract the subimages 
            orient_000 = img_data_scaled[1::2, 1::2]
            orient_045 = img_data_scaled[::2,  1::2]
            orient_090 = img_data_scaled[::2,   ::2]
            orient_135 = img_data_scaled[1::2,  ::2]

            # Write the subimages as FITS
            header['POL_ANG'] = 0
            fits.writeto(op_000, orient_000, header, overwrite=True)
            header['POL_ANG'] = 45
            fits.writeto(op_045, orient_045, header, overwrite=True)
            header['POL_ANG'] = 90
            fits.writeto(op_090, orient_090, header, overwrite=True)
            header['POL_ANG'] = 135
            fits.writeto(op_135, orient_135, header, overwrite=True)


    return 0


def biasCombine (ipDir):
    '''
    Combine all bias frames for all angles. 
    '''

    for angle in angles:
        # Path to the biases, and figure out where to write results
        biasDir = os.path.join(ipDir, angle, "Bias")
        masterBiasFile = os.path.join(ipDir, angle) + "/masterBias_" + \
                angle + ".fits"

        biasImages = ccdp.ImageFileCollection(biasDir)
        
        # Combining the biases
        to_combine = biasImages.files_filtered(include_path = True)
        combinedBias = ccdp.combine(to_combine,
                method='average', unit='adu',
                sigma_clip=True, sigma_clip_low_thresh=5, sigma_clip_high_thresh=5,
                sigma_clip_func=np.ma.median, sigma_clip_dev_func=mad_std
                )

        # Add header to masterBias and write to disk
        combinedBias.meta['combined'] = True
        combinedBias.write(masterBiasFile, overwrite = True)

    return 0


def darkCombine (ipDir):
    '''
    Subtract the combined bias from each dark, then combine 
    these debiased darks. Do this for each angle.
    '''

    for angle in angles:
        # Path to the darks, masterBias,
        # and figure out where to write results
        darkDir = os.path.join(ipDir, angle, "Darks")
        masterBiasFile = os.path.join(ipDir, angle) + "/masterBias_" + \
                angle + ".fits"
        masterDarkFile = os.path.join(ipDir, angle) + "/masterDark_" + \
                angle + ".fits"
        debiasedDarkDir = os.path.join(ipDir, angle, "debiasedDarks")
        os.makedirs(debiasedDarkDir, exist_ok=True)

        # Read the darks and the masterbias
        darkImages = ccdp.ImageFileCollection(darkDir)
        masterBias = CCDData.read(masterBiasFile, unit='adu')

        # Debias the darks
        for ccd, file_name in darkImages.ccds(ccd_kwargs={'unit': 'adu'},
                return_fname=True):
            ccd = ccdp.subtract_bias(ccd, masterBias)
            op = os.path.join(debiasedDarkDir, file_name)
            ccd.write(op, overwrite=True)

       # Combined the debiased darks to create a masterDark
        debiasedDarkImages = ccdp.ImageFileCollection(debiasedDarkDir)
        to_combine = debiasedDarkImages.files_filtered(include_path = True)
        combinedDark = ccdp.combine(to_combine, 
                method='average', unit='adu',
                sigma_clip=True, sigma_clip_low_thresh=5, sigma_clip_high_thresh=5,
                sigma_clip_func=np.ma.median, sigma_clip_dev_func=mad_std
                )

        # Add header to masterDark and write to disk
        combinedDark.meta['combined'] = True
        combinedDark.write(masterDarkFile, overwrite = True)

    return 0


def flatCombine (ipDir):
    '''
    Subtract the masterBias from each flat,
    then subtract exposure-scaled masterDark,
    then combine (normalizing each to median) to create masterFlat.
    Do this for each angle.
    '''

    for angle in angles:
        # Paths to the flats, masterBias, masterDark, masterFlat
        flatDir = os.path.join(ipDir, angle, "Flats")
        masterBiasFile = os.path.join(ipDir, angle) + "/masterBias_" + \
                angle + ".fits"
        masterDarkFile = os.path.join(ipDir, angle) + "/masterDark_" + \
                angle + ".fits"
        masterFlatFile = os.path.join(ipDir, angle) + "/masterFlat_" + \
                angle + ".fits"

        # Location to save debiased, and bias+dark-subtracted flats
        de_BD_FlatDir = os.path.join(ipDir, angle, "de_BD_Flats")
        os.makedirs(de_BD_FlatDir, exist_ok=True)

        masterBias = CCDData.read(masterBiasFile, unit='adu')
        masterDark = CCDData.read(masterDarkFile, unit='adu')

        # Debias and scaled-dark-subtract the flats
        flatImages = ccdp.ImageFileCollection(flatDir)
        for ccd, file_name in flatImages.ccds(ccd_kwargs={'unit': 'adu'},
                return_fname=True):
            ccd = ccdp.subtract_bias(ccd, masterBias)
            ccd = ccdp.subtract_dark(ccd, masterDark,
                    exposure_time='exptime', 
                    exposure_unit=u.second, 
                    scale=True)
            op = os.path.join(de_BD_FlatDir, file_name)
            ccd.write(op, overwrite=True)

        # Combine the flats, normalizing each to their median value
        de_BD_Flats = ccdp.ImageFileCollection(de_BD_FlatDir)
        to_combine = de_BD_Flats.files_filtered(include_path=True)
        combined_flat = ccdp.combine(to_combine, 
                method='average', unit='adu', scale=inv_median,
                sigma_clip=True, sigma_clip_low_thresh=5, sigma_clip_high_thresh=5,
                sigma_clip_func=np.ma.median, signma_clip_dev_func=mad_std
                )

        # Add header to masterFlat and write to disk
        combined_flat.meta['combined'] = True
        combined_flat.write(masterFlatFile, overwrite = True)

    return 0


def calibrateScience (ipDir):
    '''
    Calibrate each science image by subtracting masterBias and masterDark,
    and then dividing by the masterFlat.
    Do this for each angle.
    '''

    for angle in angles:
        # Get science images, masterBias, masterDark, masterFlat
        scienceDir = os.path.join(ipDir, angle, "Science")
        masterBiasFile = os.path.join(ipDir, angle) + "/masterBias_" + \
                angle + ".fits"
        masterDarkFile = os.path.join(ipDir, angle) + "/masterDark_" + \
                angle + ".fits"
        masterFlatFile = os.path.join(ipDir, angle) + "/masterFlat_" + \
                angle + ".fits"
        masterBias = CCDData.read(masterBiasFile, unit='adu')
        masterDark = CCDData.read(masterDarkFile, unit='adu')
        masterFlat = CCDData.read(masterFlatFile, unit='adu')


        # Location to save calibrated science images
        calibScienceDir = os.path.join(ipDir, angle, "calibScience")
        os.makedirs(calibScienceDir, exist_ok=True)

        # Calibrate science images
        scienceImages = ccdp.ImageFileCollection(scienceDir)
        for ccd, file_name in scienceImages.ccds(ccd_kwargs={'unit': 'adu'},
                return_fname=True):
            ccd = ccdp.subtract_bias(ccd, masterBias)
            ccd = ccdp.subtract_dark(ccd, masterDark,
                    exposure_time='exptime', 
                    exposure_unit=u.second, 
                    scale=True)
            ccd = ccdp.flat_correct(ccd, masterFlat)
            op = os.path.join(calibScienceDir, file_name)
            ccd.write(op, overwrite=True)

    return 0


def getDoLP (dataDir, opDir):
    sciencePath = os.path.join(dataDir, 'Science')
    scienceFiles = sorted(glob.glob(sciencePath + "/*.fits"))

    # Create directory to store DoLP images
    dolpDir = os.path.join(opDir,'dolp')
    os.makedirs(dolpDir, exist_ok=True)

    for image in scienceFiles:
        split_tup = os.path.splitext(image)
        dolpNam = os.path.basename( split_tup[0] + '_dolp.fits')
        dolpLoc = os.path.join(dolpDir,dolpNam)

        for angle in angles:
            fnam = os.path.basename( split_tup[0] + '_' + angle + '.fits')
            floc = os.path.join(opDir, angle, 'calibScience',fnam)
            if not os.path.isfile(floc):
                print(floc, 'not found')

            dat, header = fits.getdata(floc, ext=0, header=True)
            if angle == 'p000':
                I000 = dat
            elif angle == 'p045':
                I045 = dat
            elif angle == 'p090':
                I090 = dat
            elif angle == 'p135':
                I135 = dat
            else:
                print('This should not happen!!!')

        # Stokes parameters
        I = 0.5*(I000+I090 + I045+I135)
        Q = (I000-I090)
        U = (I045-I135)

        # Compute DoLP and AoLP values and write to FITS
        dolp = np.sqrt(Q*Q + U*U)/I
        aolp = 0.5*np.arctan2(U, Q)

        header.pop('SWCREATE', None)
        header.pop('POL_ANG', None)
        header.pop('BUNIT', None)
        #header['FRAMETYP'] = ('DoLP', 'Pixels are fractional DoLP values')
        #fits.writeto(dolpLoc, dolp, header, overwrite=True)
        empty_primary = fits.PrimaryHDU(header=header)
        dolp_hdu1 = fits.ImageHDU(dolp)
        aolp_hdu2 = fits.ImageHDU(aolp)
        hdul = fits.HDUList([empty_primary, dolp_hdu1, aolp_hdu2])
        hdul.writeto(dolpLoc, overwrite=True)

    return 0


ip = sys.argv[1]
op = sys.argv[2]

'''
# Split raw FITS into different angles
ret = split_poldata(ip, op)   

# Combine biases into masterBias
ret = biasCombine(op)         

# Debias darks, then combine to create masterDark
ret = darkCombine(op)         

# Bias-subtract flats, then subtract exposure-scaled masterdark.
# Then combine median-normalized to create masterFlat.
ret = flatCombine(op)         

# Calibrate the science images
ret = calibrateScience (op)
'''

# Write DoLP and AoLP images
ret = getDoLP(ip, op)


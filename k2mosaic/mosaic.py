"""Implements the logic to stitch K2 data together into channel mosaics.

Example usage
-------------
mos = KeplerChannelMosaic(campaign=6, channel=15, cadenceno=3051)
mos.gather_pixels()
mos.add_wcs()
mos.writeto("mymosaic.fits")
"""
from collections import OrderedDict
import glob
import os
import re

import astropy
from astropy.io import fits
from astropy.io.fits import getheader
from astropy.io.fits.card import UNDEFINED
from astropy.time import Time

import fitsio
import numpy as np
import pandas as pd
import click
import datetime

from . import PACKAGEDIR, KEPLER_CHANNEL_SHAPE

FFI_HEADERS_FILE = os.path.join(PACKAGEDIR, 'data', 'k2-ffi-headers.csv')
WCS_KEYS = ['TELESCOP', 'INSTRUME', 'CHANNEL', 'MODULE', 'OUTPUT', 'RADESYS',
            'EQUINOX', 'WCSAXES', 'CTYPE1', 'CTYPE2', 'CRVAL1',
            'CRVAL2', 'CRPIX1', 'CRPIX2', 'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
            'A_ORDER', 'B_ORDER', 'A_2_0', 'A_0_2', 'A_1_1', 'B_2_0', 'B_0_2',
            'B_1_1', 'AP_ORDER', 'BP_ORDER', 'AP_1_0', 'AP_0_1', 'AP_2_0',
            'AP_0_2', 'AP_1_1', 'BP_1_0', 'BP_0_1', 'BP_2_0', 'BP_0_2', 'BP_1_1']


class MosaicException(Exception):
    pass


class KeplerChannelMosaic(object):
    """Factory for an artificial Kepler Full-Frame Channel Image."""
    def __init__(self, campaign=0, channel=1, cadenceno=1, data_store=None,
                 shape=KEPLER_CHANNEL_SHAPE, add_background=False, time=None,
                 quality=None, dateobs=None, dateend=None, mjdbeg=None, 
                 mjdend=None, template_tpf_header0=None,
                 template_tpf_header1=None):
        self.campaign = campaign
        self.channel = channel
        self.cadenceno = cadenceno
        self.data_store = data_store
        self.header = fits.Header()
        self.data = np.empty(shape, dtype=np.float32)
        self.data[:] = np.nan
        self.uncert = np.empty(shape, dtype=np.float32)
        self.uncert[:] = np.nan
        self.add_background = add_background
        self.time = time
        self.quality = quality
        self.template_tpf_header0 = template_tpf_header0
        self.template_tpf_header1 = template_tpf_header1
        self.dateobs = dateobs
        self.dateend = dateend
        self.mjdbeg = mjdbeg
        self.mjdend = mjdend

    def gather_pixels(self):
        """Figures out the files needed and adds the pixels."""
        print("Querying MAST to obtain a list of target pixel files...")
        from .mast import get_tpf_urls
        urls = get_tpf_urls(self.campaign, channel=self.channel)
        print("Found {} target pixel files.".format(len(urls)))
        with click.progressbar(urls, label="Reading target pixel files",
                               show_pos=True) as bar:
            for url in bar:
                if self.data_store is not None:
                    path = url.replace("http://archive.stsci.edu/missions/k2/target_pixel_files",
                                       self.data_store)
                else:
                    path = url
                self.add_tpf(path)

    def add_wcs(self):
        """Injects the WCS keywords from an FFI of the same campaign."""
        ffi_hdr = get_ffi_header(self.campaign, self.channel)
        if ffi_hdr is not None:
            for kw in WCS_KEYS:
                self.header[kw] = ffi_hdr[kw]
        else:
            print('Warning: this version of k2mosaic does not contain '
                  'WCS information for campaign {} data.'.format(self.campaign))

    def add_tpf(self, tpf_filename):
        #print("Adding {}".format(tpf_filename))
        if tpf_filename.startswith("http"):
            tpf_filename = astropy.utils.data.download_file(tpf_filename, cache=True)

        self.template_tpf_header0 = getheader(tpf_filename, 0)
        self.template_tpf_header1 = getheader(tpf_filename, 1)

        tpf = fitsio.FITS(tpf_filename)
        self.add_pixels(tpf)
        tpf.close()

    def add_pixels(self, tpf):
        tpfdata = tpf[1].read()
        aperture_shape = tpfdata['FLUX'][0].shape
        # Get the pixel coordinates of the corner of the aperture
        col, row = (self.template_tpf_header1['1CRV5P'], self.template_tpf_header1['2CRV5P'])
        height, width = aperture_shape[0], aperture_shape[1]

        # Fill the data
        mask = tpf[2].read() > 0
        idx = self.cadenceno - tpfdata["CADENCENO"][0]

        # When time is nan, we know that there is no available data.
        if (tpfdata['QUALITY'][idx] & int(65536) > 0): 
            raise Exception('Error: Cadence {} does not appear to contain data!'.format(self.cadenceno))

        if self.add_background:
            self.data[row:row+height, col:col+width][mask] = \
                tpfdata['FLUX'][idx][mask] \
                + tpfdata['FLUX_BKG'][idx][mask]
            self.uncert[row:row+height, col:col+width][mask] = \
                np.sqrt(
                    (tpfdata['FLUX_ERR'][idx][mask])**2 +
                    (tpfdata['FLUX_BKG_ERR'][idx][mask])**2
                )
        else:
            self.data[row:row+height, col:col+width][mask] = \
                tpfdata['FLUX'][idx][mask]
            self.uncert[row:row+height, col:col+width][mask] = \
                tpfdata['FLUX_ERR'][idx][mask]

        # If this is the first TPF being added, record the time and calculate DATE-OBS/END
        if self.time is None:
            self.time = tpfdata['TIME'][idx]
            self.quality = tpfdata['QUALITY'][idx]
            frametim = np.float(self.template_tpf_header1['FRAMETIM'])
            num_frm = np.float(self.template_tpf_header1['NUM_FRM'])

            # Calculate DATE-OBS from BJD time:
            mjd_start = self.time \
                + np.float(self.template_tpf_header1['BJDREFI']) \
                - frametim/3600./24./2. * num_frm \
                - 2400000.5
            self.mjdbeg = mjd_start
            starttime = Time(mjd_start, format='mjd')
            starttime = str(starttime.datetime)
            self.dateobs = starttime.replace(' ', 'T') + 'Z'

            # Calculate DATE-END:
            mjd_end = self.time \
                + np.float(self.template_tpf_header1['BJDREFI']) \
                + frametim/3600./24./2. * num_frm \
                - 2400000.5
            self.mjdend = mjd_end
            endtime = Time(mjd_end, format='mjd')
            endtime = str(endtime.datetime)
            self.dateend = endtime.replace(' ', 'T') + 'Z'

    def to_fits(self):
        """Returns an astropy.io.fits.HDUList object."""
        return fits.HDUList([self._make_primary_hdu(),
                             self._make_image_extension('IMAGE', self.data),
                             self._make_image_extension('UNCERTAINTY', self.uncert),
                             self._make_cr_extension()])

    def _make_primary_hdu(self):
        hdu = fits.PrimaryHDU()

        int_time = np.float(self.template_tpf_header1['INT_TIME'])
        num_frm = np.float(self.template_tpf_header1['NUM_FRM'])

        # Override the defaults where necessary
        hdu.header['NEXTEND'] = 3
        hdu.header.cards['NEXTEND'].comment = 'number of standard extensions'
        hdu.header['EXTNAME'] = 'PRIMARY'
        hdu.header.cards['EXTNAME'].comment = 'name of extension'
        hdu.header['EXTVER'] = 1
        hdu.header.cards['EXTVER'].comment = 'extension version number (not format version)'
        hdu.header['ORIGIN'] = "NASA/Ames"
        hdu.header.cards['ORIGIN'].comment = 'institution responsible for creating this file'
        hdu.header['DATE'] = datetime.datetime.now().strftime("%Y-%m-%d")
        hdu.header.cards['DATE'].comment = 'file creation date.'
        hdu.header['DATE-OBS'] = self.dateobs
        hdu.header.cards['DATE-OBS'].comment = 'TSTART as UTC calendar date'
        hdu.header['DATE-END'] = self.dateend
        hdu.header.cards['DATE-END'].comment = 'TSTOP as UTC calendar date'
        hdu.header['MJD-BEG'] = self.mjdbeg
        hdu.header.cards['MJD-BEG'].comment = 'TSTART as modified barycentric Julian date'
        hdu.header['MJD-END'] = self.mjdend
        hdu.header.cards['MJD-END'].comment = 'TSTOP as modified barycentric Julian date'
        hdu.header['XPOSURE'] = int_time * num_frm
        hdu.header.cards['XPOSURE'].comment = '[s] time on source'
        hdu.header['CREATOR'] = "k2mosaic"
        hdu.header.cards['CREATOR'].comment = 'file creator'
        hdu.header['PROCVER'] = UNDEFINED
        hdu.header.cards['PROCVER'].comment = 'SW version'
        hdu.header['FILEVER'] = UNDEFINED
        hdu.header.cards['FILEVER'].comment = 'file format version'
        hdu.header['TIMVERSN'] = 'OGIP/93-003'
        hdu.header.cards['TIMVERSN'].comment = 'OGIP memo number for file format'
        hdu.header['TELESCOP'] = 'Kepler'
        hdu.header.cards['TELESCOP'].comment = 'telescope'
        hdu.header['INSTRUME'] = 'Kepler Photometer'
        hdu.header.cards['INSTRUME'].comment = 'detector type'
        hdu.header['FILTER'] = 'Kepler'
        hdu.header.cards['FILTER'].comment = 'photometric passband'
        hdu.header['DATA_REL'] = UNDEFINED
        hdu.header.cards['DATA_REL'].comment = 'data release version number'

        hdu.header['ASTATE'] = UNDEFINED
        hdu.header.cards['ASTATE'].comment = 'TESS keyword not used by Kepler'
        hdu.header['CAMPAIGN'] = self.campaign
        hdu.header.cards['CAMPAIGN'].comment = 'Observing campaign number'
        hdu.header['SCCONFIG'] = UNDEFINED
        hdu.header.cards['SCCONFIG'].comment = 'commanded S/C configuration ID'
        hdu.header['RADESYS'] = 'ICRS'
        hdu.header.cards['RADESYS'].comment = 'reference frame of celestial coordinates'
        hdu.header['EQUINOX'] = 2000.0
        hdu.header.cards['EQUINOX'].comment = 'equinox of celestial coordinate system'
        hdu.header['CRMITEN'] = UNDEFINED
        hdu.header.cards['CRMITEN'].comment = 'spacecraft cosmic ray mitigation enabled'
        hdu.header['CRBLKSZ'] = UNDEFINED
        hdu.header.cards['CRBLKSZ'].comment = 'TESS keyword not used by Kepler'
        hdu.header['CRSPOC'] = UNDEFINED
        hdu.header.cards['CRSPOC'].comment = 'TESS keyword not used by Kepler'
        hdu.header['MISSION'] = 'K2'
        hdu.header.cards['MISSION'].comment = 'Mission name'

        return hdu

    def _make_image_extension(self, extname, data):
        """Create an image extension."""
        hdu = fits.ImageHDU(data)

        hdu.header.cards['NAXIS1'].comment = 'length of first array dimension'
        hdu.header.cards['NAXIS2'].comment = 'length of second array dimension'
        hdu.header['EXTNAME'] = extname
        hdu.header.cards['EXTNAME'].comment = 'name of extension'
        hdu.header['EXTVER'] = 1
        hdu.header.cards['EXTVER'].comment = 'extension version number (not format version)'
        hdu.header['TELESCOP'] = 'Kepler'
        hdu.header.cards['TELESCOP'].comment = 'telescope'
        hdu.header['INSTRUME'] = 'Kepler Photometer'
        hdu.header.cards['INSTRUME'].comment = 'detector type'
        hdu.header['CAMERA'] = UNDEFINED
        hdu.header.cards['CAMERA'].comment = 'TESS keyword not used by Kepler '
        hdu.header['CCD'] = UNDEFINED
        hdu.header.cards['CCD'].comment = 'TESS keyword not used by Kepler'
        hdu.header['CHANNEL'] = self.channel
        hdu.header.cards['CHANNEL'].comment = 'CCD channel'

        for keyword in ['MODULE', 'OUTPUT']:
            hdu.header[keyword] = self.template_tpf_header0[keyword]
            hdu.header.cards[keyword].comment = self.template_tpf_header0.comments[keyword]

        hdu.header['CADENCEN'] = self.cadenceno
        hdu.header.cards['CADENCEN'].comment = 'unique cadence number'

        for keyword in ['TIMEREF', 'TASSIGN', 'TIMESYS', 'BJDREFI', 'BJDREFF', 'TIMEUNIT']:
            hdu.header[keyword] = self.template_tpf_header1[keyword]
            hdu.header.cards[keyword].comment = self.template_tpf_header1.comments[keyword]

        frametim = np.float(self.template_tpf_header1['FRAMETIM'])
        int_time = np.float(self.template_tpf_header1['INT_TIME'])
        num_frm = np.float(self.template_tpf_header1['NUM_FRM'])
        deadc = np.float(self.template_tpf_header1['DEADC'])

        hdu.header['MIDTIME'] = self.time
        hdu.header.cards['MIDTIME'].comment = 'mid-time of exposure in BJD-BJDREF'

        hdu.header['TSTART'] = self.time - frametim/3600./24./2. * num_frm
        hdu.header.cards['TSTART'].comment = 'observation start time in BJD-BJDREF'

        hdu.header['TSTOP'] = self.time + frametim/3600./24./2. * num_frm
        hdu.header.cards['TSTOP'].comment = 'observation stop time in BJD-BJDREF'

        hdu.header['TELAPSE'] = frametim/3600./24. * num_frm
        hdu.header.cards['TELAPSE'].comment = '[d] TSTOP - TSTART'

        hdu.header['EXPOSURE'] = int_time/3600./24. * num_frm
        hdu.header.cards['EXPOSURE'].comment = '[d] time on source'

        hdu.header['LIVETIME'] = hdu.header['TELAPSE'] * deadc
        hdu.header.cards['LIVETIME'].comment = '[d] TELAPSE multiplied by DEADC'

        for keyword in ['DEADC', 'TIMEPIXR', 'TIERRELA',
                        'INT_TIME', 'READTIME', 'FRAMETIM',
                        'NUM_FRM', 'TIMEDEL', 'DEADAPP', 'VIGNAPP']:
            hdu.header[keyword] = self.template_tpf_header1[keyword]
            hdu.header.cards[keyword].comment = self.template_tpf_header1.comments[keyword]

        hdu.header['BUNIT'] = 'electrons/s'
        hdu.header.cards['BUNIT'].comment = 'physical units of image data'

        hdu.header['BACKAPP'] = (not self.add_background)
        hdu.header.cards['BACKAPP'].comment = 'background is subtracted'

        hdu.header['DATE-OBS'] = self.dateobs
        hdu.header['DATE-END'] = self.dateend
        hdu.header.cards['DATE-OBS'].comment = 'TSTART as UTC calendar date'
        hdu.header.cards['DATE-END'].comment = 'TSTOP as UTC calendar date'

        hdu.header['BTC_PIX1'] = UNDEFINED
        hdu.header.cards['BTC_PIX1'].comment = 'reference col for barycentric time correction'
        hdu.header['BTC_PIX2'] = UNDEFINED
        hdu.header.cards['BTC_PIX2'].comment = 'reference col for barycentric time correction'

        for keyword in ['GAIN', 'READNOIS', 'NREADOUT', 'MEANBLCK']:
            hdu.header[keyword] = self.template_tpf_header1[keyword]
            hdu.header.cards[keyword].comment = self.template_tpf_header1.comments[keyword]

        for keyword in ['GAINA', 'GAINB', 'GAINC', 'GAIND', 'READNOIA', 'READNOIB',
                        'READNOIC', 'READNOID', 'FXDOFF', 'MEANBLCA', 'MEANBLCB',
                        'MEANBLCC', 'MEANBLCD']:
            hdu.header[keyword] = UNDEFINED
            hdu.header.cards[keyword].comment = 'TESS keyword not used by Kepler'

        for keyword in ['RA_NOM', 'DEC_NOM', 'ROLL_NOM', 'DQUALITY', 'IMAGTYPE']:
            hdu.header[keyword] = UNDEFINED
            hdu.header.cards[keyword].comment = 'TESS keyword not used by Kepler'

        hdu.header['QUALITY'] = self.quality
        hdu.header.cards['QUALITY'].comment = 'data quality flags'

        for keyword in ['RADESYS', 'EQUINOX']:
            hdu.header[keyword] = self.template_tpf_header1[keyword]
            hdu.header.cards[keyword].comment = self.template_tpf_header1.comments[keyword]

        return hdu

    def _make_cr_extension(self):
        """Create the cosmic ray extension (i.e. extension #3)."""
        cols = []
        cols.append(fits.Column(name='RAWX', format='I', disp='I4', array=np.array([])))
        cols.append(fits.Column(name='RAWY', format='I', disp='I4', array=np.array([])))
        cols.append(fits.Column(name='COSMIC_RAY', format='E', disp='E14.7', array=np.array([])))
        coldefs = fits.ColDefs(cols)
        hdu = fits.BinTableHDU.from_columns(coldefs)
        return hdu

    def writeto(self, output_fn, overwrite=True):
        self.to_fits().writeto(output_fn, overwrite=overwrite, checksum=True)


###
# Functions to export and retrieve WCS keywords from standard K2 FFIs
###

def export_ffi_headers(output_fn=FFI_HEADERS_FILE, ffi_store=None):
    """Writes the headers of all available K2 FFI's to a csv table.

    This will enable us to inject WCS keywords from real FFI's into the sparse
    FFI's created by k2mosaic."""
    if ffi_store is None:
        ffi_store = os.path.join(os.getenv("K2DATA"), 'ffi')
    ffi_headers = []
    ffi_filenames = glob.glob(os.path.join(ffi_store, '*cal.fits'))
    with click.progressbar(ffi_filenames, label="Reading FFI files",
                           show_pos=True) as bar:
        for filename in bar:
            basename = os.path.basename(filename)
            # Extract the campaign number from the FFI filename
            campaign = int(re.match(".*c([0-9]+)_.*", basename).group(1))
            fts = fits.open(filename)
            for ext in range(1, 85):
                try:
                    keywords = OrderedDict()
                    keywords['campaign'] = campaign
                    keywords['filename'] = basename
                    keywords['extension'] = ext
                    for kw in WCS_KEYS:
                        keywords[kw] = fts[ext].header[kw]
                    ffi_headers.append(keywords)
                except KeyError:
                    pass
    # Convert to a pandas dataframe and then export to csv
    df = pd.DataFrame(ffi_headers)
    df = df.sort_values(["campaign", "filename"])
    columns = list(ffi_headers[0].keys())  # Keep column order as in FITS files
    df[columns].to_csv(output_fn, index=False)


def get_ffi_header(campaign=0, channel=1, FFI_HEADERS_FILE=FFI_HEADERS_FILE):
    try:
        df = pd.read_csv(FFI_HEADERS_FILE)
        row = df[(df['campaign'] == campaign) & (df['extension'] == channel)].iloc[0]
        return row.to_dict()
    except IndexError:  # Template not found
        return None


if __name__ == "__main__":
    export_ffi_headers()

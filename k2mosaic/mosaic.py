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

from astropy.io import fits
import fitsio
import numpy as np
import pandas as pd
import click

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
    def __init__(self, campaign=0, channel=1, cadenceno=1, data_store=None, shape=KEPLER_CHANNEL_SHAPE):
        self.campaign = campaign
        self.channel = channel
        self.cadenceno = cadenceno
        self.data_store = data_store
        self.header = fits.Header()
        self.data = np.empty(shape, dtype=np.float32)
        self.data[:] = np.nan

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
                    path = url.replace("http://archive.stsci.edu/missions/k2/target_pixel_files", self.data_store)
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
        tpf = fitsio.FITS(tpf_filename)
        self.add_pixels(tpf)
        tpf.close()

    def add_pixels(self, tpf, fluxcolumn='FLUX'):
        aperture_shape = tpf[1].read()[fluxcolumn][0].shape
        # Get the pixel coordinates of the corner of the aperture
        hdr_list = tpf[1].read_header_list()
        hdr = {elem['name']:elem['value'] for elem in hdr_list}
        col, row = int(hdr['1CRV5P']), int(hdr['2CRV5P'])
        height, width = aperture_shape[0], aperture_shape[1]
        # Fill the data
        mask = tpf[2].read() > 0
        idx = self.cadenceno - tpf[1].read()["CADENCENO"][0]
        self.data[row:row+height, col:col+width][mask] = tpf[1].read()[fluxcolumn][idx][mask]

    def to_fits(self):
        primary_hdu = fits.PrimaryHDU()
        image_hdu = fits.ImageHDU(self.data, self.header)
        hdulist = fits.HDUList([primary_hdu, image_hdu])
        return hdulist

    def writeto(self, output_fn, overwrite=True):
        self.to_fits().writeto(output_fn, overwrite=overwrite)


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

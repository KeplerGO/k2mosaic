"""Implements the `k2mosaic` command-line tool to stitch K2 data together.

Example usage
-------------
mos = KeplerChannelMosaic(campaign=6, channel=15, cadenceno=3051)
mos.gather_pixels()
mos.add_wcs()
mos.writeto("mymosaic.fits")
"""
import argparse
from collections import OrderedDict
import glob
import os
import re
import requests

from astropy.io import fits
import numpy as np
import pandas as pd
from tqdm import tqdm

from . import PACKAGEDIR

KEPLER_CHANNEL_SHAPE = (1070, 1132)  # (rows, cols)

FFI_HEADERS_FILE = os.path.join(PACKAGEDIR, 'data', 'k2-ffi-headers.csv')
WCS_KEYS = ['TELESCOP', 'INSTRUME', 'CHANNEL', 'MODULE', 'OUTPUT', 'RADESYS',
            'EQUINOX', 'WCSAXES', 'CTYPE1', 'CTYPE2', 'CRVAL1',
            'CRVAL2', 'CRPIX1', 'CRPIX2', 'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
            'A_ORDER', 'B_ORDER', 'A_2_0', 'A_0_2', 'A_1_1', 'B_2_0', 'B_0_2',
            'B_1_1', 'AP_ORDER', 'BP_ORDER', 'AP_1_0', 'AP_0_1', 'AP_2_0',
            'AP_0_2', 'AP_1_1', 'BP_1_0', 'BP_0_1', 'BP_2_0', 'BP_0_2', 'BP_1_1']
MAST_URL = 'http://archive.stsci.edu'
K2_TPF_URL = MAST_URL + '/missions/k2/target_pixel_files/'


class MosaicException(Exception):
    pass


class KeplerChannelMosaic(object):
    """Factory an artificial Kepler Full-Frame Channel Image."""
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
        urls = k2_tpf_urls_by_campaign(self.campaign, self.channel)
        print("Found {} target pixel files.".format(len(urls)))
        for url in tqdm(urls, desc="Reading target pixel files"):
            if self.data_store is not None:
                path = url.replace("http://archive.stsci.edu/missions/k2/target_pixel_files", self.data_store)
            else:
                path = url
            self.add_tpf(path)

    def add_wcs(self):
        """Injects the WCS keywords from an FFI of the same campaign."""
        ffi_hdr = get_ffi_header(self.campaign, self.channel)
        for kw in WCS_KEYS:
            self.header[kw] = ffi_hdr[kw]

    def add_tpf(self, tpf_filename):
        tpf = fits.open(tpf_filename)
        self.add_pixels(tpf)
        del tpf

    def add_pixels(self, tpf):
        aperture_shape = tpf[1].data["FLUX"][0].shape
        # Get the pixel coordinates of the corner of the aperture
        col, row = tpf[1].header["1CRV5P"], tpf[1].header["2CRV5P"]
        height, width = aperture_shape[0], aperture_shape[1]
        # Fill the data
        mask = tpf[2].data > 0
        self.data[row:row+height, col:col+width][mask] = \
            tpf[1].data["FLUX"][self.cadenceno][mask]

    def to_fits(self):
        primary_hdu = fits.PrimaryHDU()
        image_hdu = fits.ImageHDU(self.data, self.header)
        hdulist = fits.HDUList([primary_hdu, image_hdu])
        return hdulist

    def writeto(self, output_fn, clobber=True):
        self.to_fits().writeto(output_fn, clobber=clobber)


###
# Functions to query and retrieve target pixel files using MAST's API
###
def get_k2ids(campaign, channel=None, obsmode="LC"):
    """Returns a `Response` object."""
    url = MAST_URL + '/k2/data_search/search.php?'
    url += 'action=Search'
    url += '&max_records=123456789'
    url += '&selectedColumnsCsv=ktc_k2_id'
    url += '&outputformat=JSON'
    url += '&ktc_target_type={}'.format(obsmode)
    url += '&sci_campaign={:d}'.format(campaign)
    if channel is not None:
        url += '&sci_channel={:d}'.format(channel)
    return requests.get(url)


def k2_tpf_urls_by_campaign(campaign, channel=None, obsmode="LC", base_url=K2_TPF_URL):
    """Returns a list of URLs pointing to the TPF files of a given campaign/channel."""
    resp = get_k2ids(campaign, channel, obsmode)
    if resp.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET k2ids {}'.format(resp.status_code))
    try:
        urls = [k2_tpf_url(entry['K2 ID'], campaign, obsmode, base_url)
                for entry in resp.json()]
        return urls
    except ValueErroras:
        raise MosaicException("Error: no data found for these parameters.")


def k2_tpf_url(k2id, campaign, obsmode="LC", base_url=K2_TPF_URL):
    """Returns the URL of a TPF file given its k2id (i.e. EPIC id)."""
    k2id = str(k2id)
    fn_prefix = 'ktwo' + k2id + '-c' + '{0:02d}'.format(campaign)
    if obsmode == "LC":
        fn_suffix = "_lpd-targ.fits.gz"
    else:
        fn_suffix = "_spd-targ.fits.gz"
    url = base_url + 'c{0:d}/{1}00000/{2}000/{3}{4}'.format(
                        campaign, k2id[0:4], k2id[4:6], fn_prefix, fn_suffix)
    return url


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
    for filename in tqdm(ffi_filenames, desc="Reading FFI files"):
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
    df = pd.read_csv(FFI_HEADERS_FILE)
    row = df[(df['campaign'] == campaign) & (df['extension'] == channel)].iloc[0]
    return row.to_dict()


###
# Command line interface
###

def k2mosaic(campaign, channel, cadenceno, data_store, output_fn=None):
    mosaic = KeplerChannelMosaic(campaign, channel, cadenceno, data_store=data_store)
    mosaic.gather_pixels()
    mosaic.add_wcs()
    if output_fn is None:
        output_fn = "k2-mosaic-c{:02d}-ch{:02d}-cad{}.fits".format(
                                            campaign, channel, cadenceno)
    print("Writing " + output_fn)
    mosaic.writeto(output_fn)


def k2mosaic_main(args=None):
    """Exposes k2mosaic to the command line."""
    parser = argparse.ArgumentParser(
                    description='Creates a mosaic of all K2 target pixel files '
                                'in a given channel during a single cadence.',
                    epilog='This tool will look for data in the directory '
                           'specified by the --data_store parameter. '
                           'If that fails, it will look inside the directory '
                           'specified by the $K2DATA environment variable. '
                           'If this fails as well, then the data will be downloaded '
                           'from the archive on the fly.')
    parser.add_argument('campaign', help='Campaign number.', type=int)
    parser.add_argument('channel', help='Channel number (1-84).', type=int)
    parser.add_argument('cadence', help='Cadence number.', type=int)
    parser.add_argument('-d', '--data_store', metavar='PATH', type=str, default=None,
                        help='Path to the directory that contains a mirror of '
                             'the target pixel files directory in the K2 data archive, '
                             'i.e. a directory that contains a mirror of '
                             'http://archive.stsci.edu/missions/k2/target_pixel_files/.')
    args = parser.parse_args(args)
    if args.data_store is None and os.getenv("K2DATA") is not None:
        args.data_store = os.path.join(os.getenv("K2DATA"), 'target_pixel_files')
    try:
        k2mosaic(args.campaign, args.channel, args.cadence, data_store=args.data_store)
    except MosaicException as e:
        print(e)


if __name__ == "__main__":
    export_ffi_headers()

"""Exposes k2mosaic to the command line."""
import click

from astropy.io import fits
import numpy as np

from . import KEPLER_CHANNEL_SHAPE
from . import core, mast, __version__

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def k2mosaic_mosaic(tpf_filenames, cadencenumbers=None, output_prefix='', step=10):
    """Mosaic a set of TPF files for a set of cadences."""
    # First obtain the campaign, channel, and desired cadence numbers
    with fits.open(tpf_filenames[0]) as first_tpf:
        try:
            campaign = first_tpf[0].header['CAMPAIGN']
            is_k2 = True
        except KeyError:
            campaign = first_tpf[0].header['QUARTER']
            is_k2 = False
        if campaign == '':  # Hack to deal with C9 raw data
            campaign = 9
        channel = first_tpf[0].header['CHANNEL']
        if cadencenumbers is None:  # Obtain all cadence numbers
            cadences_to_mosaic = first_tpf[1].data['CADENCENO'][::step]
        else:
            if '..' in cadencenumbers:  # A range was given
                cadencerange = [int(r) for r in cadencenumbers.split("..")]
            else:  # A single cadence number was given
                cadencerange = [int(cadencenumbers), int(cadencenumbers)]
            cadences_to_mosaic = list(range(cadencerange[0], cadencerange[1] + 1, step))
            if (cadencerange[0] not in first_tpf[1].data['CADENCENO']
                or cadencerange[-1] not in first_tpf[1].data['CADENCENO']):
                print('Error: invalid cadence numbers '
                      '(ensure numbers are in the range {}-{})'.format(
                                first_tpf[1].data['CADENCENO'][0],
                                first_tpf[1].data['CADENCENO'][-1]))
                return
    # Start the mosaicking
    for count, cadenceno in enumerate(cadences_to_mosaic):
        if is_k2:
            letter = 'c'
        else:
            letter = 'q'
        output_fn = "{}k2mosaic-{}{:02d}-ch{:02d}-cad{}.fits".format(
                    output_prefix, letter, campaign, channel, cadenceno)
        click.echo("Writing {} (cadence {}/{})".format(output_fn, count+1, len(cadences_to_mosaic)))
        mosaic = core.KeplerChannelMosaic(campaign=campaign, channel=channel, cadenceno=cadenceno)
        with click.progressbar(tpf_filenames, label='Adding pixel files') as bar:
            for tpf in bar:
                mosaic.add_tpf(tpf)
        mosaic.add_wcs()
        mosaic.writeto(output_fn)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
def k2mosaic(**kwargs):
    pass


@k2mosaic.command(short_help='Identify target pixel files to mosaic.')
@click.argument('campaign', type=int)
@click.argument('channel', type=click.IntRange(0, 84))
@click.option('--sc/--lc', is_flag=True,
              help='Short cadence or long cadence? (default: lc)')
@click.option('--wget', is_flag=True,
              help='Output the wget commands to obtain the files')
def find(campaign, channel, sc, wget):
    """Prints the filenames or urls of the target pixel files
    observed during CAMPAIGN in CHANNEL.
    """
    try:
        urls = mast.k2_tpf_urls_by_campaign(campaign, channel, short_cadence=sc)
        if wget:
            WGET_CMD = 'wget -nH --cut-dirs=6 -c -N '
            print('\n'.join([WGET_CMD + url for url in urls]))
        else:
            print('\n'.join(urls))
    except mast.NoDataFoundException as e:
        click.echo(e)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-c', '--cadenceno', type=str, default=None, metavar='cadenceno1..cadenceno2',
              help='Cadence number range (default: all).')
@click.option('-s', '--step', type=int, default=1, metavar='<N>',
              help='Only mosaic every Nth cadence (default: 1).')
def mosaic(filelist, cadenceno, step):
    """Mosaic a set of target pixel files."""
    tpf_filenames = [path.strip() for path in filelist.read().splitlines()]
    k2mosaic_mosaic(tpf_filenames, cadencenumbers=cadenceno, step=step)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-e', '--ext', type=int, default=1,
              help='FITS extension number (default: 1)')
@click.option('-r', '--rows', type=str, default=None, metavar='row1..row2',
              help='Row range (default: crop to data)')
@click.option('-c', '--cols', type=str, default=None, metavar='col1..col2',
              help='Column range (default: crop to data)')
@click.option('--cut', type=str, default=None, metavar='min_cut..max_cut',
              help='Minimum/maximum cut levels')
#@click.option('-r', '--cadenceno', type=int, default=None,
#              help='Cadence number (default: all).')
def video(filelist, ext, rows, cols, cut, **kwargs):
    """Turn mosaics into a video or gif.

    FILELIST should be a text file specifying the mosaic files to include,
    one file or url per line."""
    mosaic_filenames = [path.strip() for path in filelist.read().splitlines()]

    if rows is None or cols is None:
        idx_not_nan = np.argwhere(-np.isnan(fits.open(mosaic_filenames[0])[1].data))

    if rows is None:
        rowrange = (np.min(idx_not_nan[:, 0]), np.max(idx_not_nan[:, 0]))
    elif rows.strip() == 'all':
        rowrange = (0, KEPLER_CHANNEL_SHAPE[0])
    else:
        rowrange = [int(r) for r in rows.split("..")]

    if cols is None:
        colrange = (np.min(idx_not_nan[:, 1]), np.max(idx_not_nan[:, 1]))
    elif cols.strip() == 'all':
        colrange = (0, KEPLER_CHANNEL_SHAPE[1])
    else:
        colrange = [int(c) for c in cols.split("..")]

    if cut is not None:
        cut = [int(c) for c in cut.split("..")]

    #from .video import make_video
    #make_video(mosaic_filenames, rowrange=rowrange, colrange=colrange)
    from .video import KeplerMosaicVideo
    kmv = KeplerMosaicVideo(mosaic_filenames, colrange=colrange, rowrange=rowrange)
    kmv.export_frames(extension=ext, cut=cut)


if __name__ == '__main__':
    k2mosaic()

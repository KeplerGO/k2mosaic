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
        campaign = first_tpf[0].header['CAMPAIGN']
        channel = first_tpf[0].header['CHANNEL']
        if cadencenumbers is None:  # Obtain all cadence numbers
            cadencenumbers = first_tpf[1].data['CADENCENO']
        elif isinstance(cadencenumbers, int):
            cadencenumbers = [cadencenumbers]
    cadences_to_mosaic = cadencenumbers[::step]
    # Start the mosaicking
    for count, cadenceno in enumerate(cadences_to_mosaic):
        output_fn = "{}k2mosaic-c{:02d}-ch{:02d}-cad{}.fits".format(
                    output_prefix, campaign, channel, cadenceno)
        click.echo("Writing {} (cadence {}/{})".format(output_fn, count+1, len(cadences_to_mosaic)))
        mosaic = core.KeplerChannelMosaic(campaign, channel, cadenceno)
        with click.progressbar(tpf_filenames) as bar:
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
def find(campaign, channel, sc):
    """Prints the filenames or urls of the target pixel files
    observed during CAMPAIGN in CHANNEL.
    """
    try:
        urls = mast.k2_tpf_urls_by_campaign(campaign, channel, short_cadence=sc)
        print('\r\n'.join(urls))
    except mast.NoDataFoundException as e:
        click.echo(e)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-c', '--cadenceno', type=int, default=None,
              help='Cadence number (default: all).')
@click.option('-s', '--step', type=int, default=1, metavar='<N>',
              help='Only mosaic every Nth cadence (default: 1).')
def mosaic(filelist, cadenceno, step):
    """Mosaic a set of target pixel files."""
    tpf_filenames = [path.strip() for path in filelist.read().splitlines()]
    k2mosaic_mosaic(tpf_filenames, cadencenumbers=cadenceno, step=step)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-r', '--rows', type=str, default=None, metavar='row1..row2',
              help='Row range (default: crop to data)')
@click.option('-c', '--cols', type=str, default=None, metavar='col1..col2',
              help='Column range (default: crop to data)')
#@click.option('-r', '--cadenceno', type=int, default=None,
#              help='Cadence number (default: all).')
def video(filelist, rows, cols, **kwargs):
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
        rowrange = rows.split("..")

    if cols is None:
        colrange = (np.min(idx_not_nan[:, 1]), np.max(idx_not_nan[:, 1]))
    elif cols.strip() == 'all':
        colrange = (0, KEPLER_CHANNEL_SHAPE[1])
    else:
        colrange = cols.split("..")

    #from .video import make_video
    #make_video(mosaic_filenames, rowrange=rowrange, colrange=colrange)
    from .video import KeplerMosaicVideo
    kmv = KeplerMosaicVideo(mosaic_filenames, colrange=colrange, rowrange=rowrange)
    kmv.export_frames()


if __name__ == '__main__':
    k2mosaic()

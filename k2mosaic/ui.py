"""Defines the k2mosaic command line tools.
"""
from astropy.io import fits
import click
from functools import partial
import numpy as np

from . import mast, __version__, KEPLER_CHANNEL_SHAPE
from .core import KeplerChannelMosaic

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def _parse_mosaic_request(tpf_filenames, cadence='all', step=10):
    """Parse the campaign/channel/cadence arguments passed to `k2mosaic mosaic`."""
    with fits.open(tpf_filenames[0]) as first_tpf:
        try:
            campaign = first_tpf[0].header['CAMPAIGN']
            mission = 'k2'
        except KeyError:
            campaign = first_tpf[0].header['QUARTER']
            mission = 'kepler'
        if campaign == '':  # Hack to deal with C9 raw data
            campaign = 9
        channel = first_tpf[0].header['CHANNEL']

        if cadence is None or cadence == 'all':  # Mosaic all cadences
            cadences_to_mosaic = first_tpf[1].data['CADENCENO'][::step]
        elif cadence == 'first':
            cadences_to_mosaic = [first_tpf[1].data['CADENCENO'][0]]
        elif cadence == 'last':
            cadences_to_mosaic = [first_tpf[1].data['CADENCENO'][-1]]
        else:
            if '..' in cadence:  # A range was given
                cadencerange = [int(r) for r in cadence.split("..")]
            else:  # A single cadence number was given
                cadencerange = [int(cadence), int(cadence)]
            # Allow for relative rather than absolute cadence numbers,
            # i.e. from 0 through n_cadences
            if cadencerange[1] < len(first_tpf[1].data['CADENCENO']):
                cadencerange = [first_tpf[1].data['CADENCENO'][cadencerange[0]],
                                first_tpf[1].data['CADENCENO'][cadencerange[1]]]
            cadences_to_mosaic = list(range(cadencerange[0], cadencerange[1] + 1, step))
            if (cadencerange[0] not in first_tpf[1].data['CADENCENO'] or
                    cadencerange[-1] not in first_tpf[1].data['CADENCENO']):
                click.echo('Error: invalid cadence numbers '
                           '(ensure numbers are in the range {}-{})'.format(
                                first_tpf[1].data['CADENCENO'][0],
                                first_tpf[1].data['CADENCENO'][-1]),
                           err=True)
                return
    return mission, campaign, channel, cadences_to_mosaic


def k2mosaic_mosaic(tpf_filenames, mission, campaign, channel, cadencelist,
                    output_prefix='', verbose=True, processes=None):
    """Mosaic a set of TPF files for a set of cadences."""
    task = partial(k2mosaic_mosaic_one, tpf_filenames=tpf_filenames,
                   campaign=campaign, channel=channel,
                   output_prefix=output_prefix, verbose=verbose)
    if processes is None or processes > 1:  # Use parallel processing
        from multiprocessing import Pool
        pool = Pool(processes=processes)
        with click.progressbar(pool.imap(task, cadencelist), label='Mosaicking', show_pos=True) as iterable:
            [job for job in iterable]
    else:  # Single process
        with click.progressbar(cadencelist, label='Mosaicking', show_pos=True) as iterable:
            [task(job) for job in iterable]


def k2mosaic_mosaic_one(cadenceno, tpf_filenames, campaign, channel, output_prefix='k2mosaic-c', progressbar=False, verbose=False):
    output_fn = "{}{:02d}-ch{:02d}-cad{}.fits".format(output_prefix, campaign, channel, cadenceno)
    if verbose:
        click.echo("Started writing {}".format(output_fn))
    mosaic = KeplerChannelMosaic(campaign=campaign, channel=channel, cadenceno=cadenceno)
    if progressbar:
        with click.progressbar(tpf_filenames, label='Reading TPFs', show_pos=True) as bar:
            [mosaic.add_tpf(tpf) for tpf in bar]
    else:
        [mosaic.add_tpf(tpf) for tpf in tpf_filenames]
    mosaic.add_wcs()
    mosaic.writeto(output_fn)
    if verbose:
        click.secho('Finished writing {}'.format(output_fn), fg='green')


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
def k2mosaic(**kwargs):
    pass


@k2mosaic.command(name='tpflist', short_help='List all target pixel files for a given campaign & CCD channel.')
@click.argument('campaign', type=str)
@click.argument('channel', type=click.IntRange(0, 84))
@click.option('--sc/--lc', is_flag=True,
              help='Short cadence or long cadence? (default: lc)')
@click.option('--wget', is_flag=True,
              help='Output the wget commands to obtain the files')
def tpflist(campaign, channel, sc, wget):
    """Prints the Target Pixel File URLS for a given CAMPAIGN/QUARTER and ccd CHANNEL.

    CAMPAIGN can refer to a K2 Campaign (e.g. 'C4') or a Kepler Quarter (e.g. 'Q4').
    """
    try:
        urls = mast.get_tpf_urls(campaign, channel=channel, short_cadence=sc)
        if wget:
            WGET_CMD = 'wget -nH --cut-dirs=6 -c -N '
            print('\n'.join([WGET_CMD + url for url in urls]))
        else:
            print('\n'.join(urls))
    except mast.NoDataFoundException as e:
        click.echo(e)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-c', '--cadence', type=str,
              default=None, metavar='cadenceno1..cadenceno2',
              help='Cadence number range (default: all).')
@click.option('-s', '--step', type=click.IntRange(min=1),
              default=1, metavar='<N>',
              help='Only mosaic every Nth cadence (default: 1).')
@click.option('-p', '--processes', type=click.IntRange(min=1),
              default=None, metavar='<CPUs>',
              help='Number of processes to use (default: #CPUs)')
def mosaic(filelist, cadence, step, processes):
    """Mosaic a list of target pixel files."""
    tpf_filenames = [path.strip() for path in filelist.read().splitlines()]
    if tpf_filenames[0].endswith('gz'):
        click.secho('Warning: some of your TPFs are gzip-compressed. '
                    'K2mosaic will perform much faster if you decompress them first.',
                    fg='yellow')
    # Parse the requested cadences
    mission, campaign, channel, cadencelist = \
        _parse_mosaic_request(tpf_filenames, cadence=cadence, step=step)
    if mission == 'k2':
        output_prefix = 'k2mosaic-c'
    else:
        output_prefix = 'k2mosaic-q'
    k2mosaic_mosaic(tpf_filenames, mission, campaign, channel, cadencelist,
                    output_prefix=output_prefix, processes=processes)


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-o', '--output', type=str, default='k2mosaic-movie.gif',
              help='.gif or .mp4 output filename (default: k2mosaic-movie.gif)')
@click.option('-r', '--rows', type=str, default=None, metavar='row1..row2',
              help='row range (default: crop to data)')
@click.option('-c', '--cols', type=str, default=None, metavar='col1..col2',
              help='column range (default: crop to data)')
@click.option('--fps', type=float, default=5, metavar='FPS',
              help='frames per second (default: 15)')
@click.option('--dpi', type=float, default=50, metavar='DPI',
              help='resolution of the output in dots per K2 pixel (default: 50)')
@click.option('--cut', type=str, default=None, metavar='min_cut..max_cut',
              help='minimum/maximum cut levels')
@click.option('--cmap', type=str, default='gray', metavar='colormap_name',
              help='matplotlib color map name (default: gray)')
@click.option('-e', '--ext', type=int, default=1,
              help='FITS extension number (default: 1)')
def movie(filelist, output, rows, cols, fps, dpi, cut, cmap, ext, **kwargs):
    """Turn mosaics into a movie or animated gif.

    FILELIST should be a text file listing the mosaics to animate,
    containing one path or url per line."""
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

    from .movie import KeplerMosaicMovie
    kmm = KeplerMosaicMovie(mosaic_filenames, colrange=colrange, rowrange=rowrange)
    click.echo('Started writing {}'.format(output))
    kmm.to_movie(output, extension=ext, fps=fps, dpi=dpi, cut=cut, cmap=cmap)
    click.secho('Finished writing {}'.format(output), fg='green')


if __name__ == '__main__':
    k2mosaic()

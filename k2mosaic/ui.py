"""Exposes k2mosaic to the command line."""
import click
from astropy.io import fits
from . import core, mast, __version__

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def k2mosaic_run(tpf_filenames, cadencenumbers=None, output_prefix='', step=10):
    """Mosaic a set of TPF files for a set of cadences."""
    with fits.open(tpf_filenames[0]) as first_tpf:
        campaign = first_tpf[0].header['CAMPAIGN']
        channel = first_tpf[0].header['CHANNEL']
        if cadencenumbers is None:
            cadencenumbers = first_tpf[1].data['CADENCENO']
        elif isinstance(cadencenumbers, int):
            cadencenumbers = [cadencenumbers]
    cadences_to_mosaic = cadencenumbers[::step]
    for count, cadenceno in enumerate(cadences_to_mosaic):
        output_fn = "{}k2mosaic-c{:02d}-ch{:02d}-cad{}.fits".format(
                    output_prefix, campaign, channel, cadenceno)
        click.echo("Writing {} ({}/{})".format(output_fn, count+1, len(cadences_to_mosaic)))
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


@k2mosaic.command()
@click.argument('filelist', type=click.File('r'))
@click.option('-c', '--cadenceno', type=int, default=None,
              help='Cadence number (default: all).')
@click.option('-s', '--step', type=int, default=1, metavar='<N>',
              help='Only mosaic every Nth cadence (default: 1).')
def run(filelist, cadenceno, step):
    """Mosaic a list of target pixel files."""
    tpf_filenames = [path.strip() for path in filelist.read().splitlines()]
    k2mosaic_run(tpf_filenames, cadenceno)


@k2mosaic.command(short_help='Select target pixel files to mosaic.')
@click.argument('campaign', type=int)
@click.argument('channel', type=click.IntRange(0, 84))
@click.option('--sc/--lc', is_flag=True,
              help='Short cadence or long cadence? (default: lc)')
def select(campaign, channel, sc):
    """Prints the filenames or urls of the target pixel files
    observed during CAMPAIGN in CHANNEL.
    """
    try:
        urls = mast.k2_tpf_urls_by_campaign(campaign, channel, short_cadence=sc)
        print('\r\n'.join(urls))
    except mast.NoDataFoundException as e:
        click.echo(e)


@k2mosaic.command()
@click.argument('filelist')
@click.option('--greeting', default='Goodbye', help='word to use for the greeting')
@click.option('--caps', is_flag=True, help='uppercase the output')
def visualize(**kwargs):
    """Turn mosaics into a video or animated gif."""
    pass


###
# Old code that has not been migrated from argparse to click yet, below:
###

def k2mosaic_video(filenames, rowrange=(0, 1070), colrange=(0, 1132), cmap='Greys_r'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as pl
    import matplotlib.image as mimg
    from astropy import visualization

    min_cut, max_cut = None, None
    for fn in tqdm(filenames, desc="Reading mosaics"):
        with fits.open(fn) as fts:
            if (-np.isnan(fts[1].data)).sum() == 0:
                continue
            image = fts[1].data[rowrange[0]:rowrange[1], colrange[0]:colrange[1]]
            if min_cut is None:
                min_cut, max_cut = np.percentile(image[-np.isnan(image)], [0.5, 99.5])
            image_scaled = visualization.scale_image(image, scale="asinh", min_cut=min_cut, max_cut=max_cut) #min_percent=0.5, max_percent=99.5)

        px_per_kepler_px = 15
        dimensions = [image.shape[0] * px_per_kepler_px, image.shape[1] * px_per_kepler_px]
        dpi = 300
        figsize = [dimensions[0]/dpi, dimensions[1]/dpi]
        dpi = 440 / float(figsize[0])
        fig = pl.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(1, 1, 1)
        ax.matshow(image_scaled, aspect='auto',
                   cmap=cmap, origin='lower',
                   interpolation='nearest')
        out_fn = "video-" + fn + ".png"
        #mimg.imsave(out_fn, image_scaled, cmap='Greys_r')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis('off')
        ax.set_axis_bgcolor('black')
        fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
        fig.canvas.draw()
        fig.savefig(out_fn, facecolor='black')
        pl.close(fig)


def k2mosaic_video_main(args=None):
    """Exposes k2mosaic-video to the command line."""
    parser = argparse.ArgumentParser(
                    description='Creates a video of K2 mosaics.')
    parser.add_argument('filelist', help='Text file containing a list of mosaic files, one path or url per line.', type=str)
    args = parser.parse_args(args)
    with open(args.filelist, 'r') as inputfile:
        mosaic_filenames = [path.strip() for path in inputfile.read().splitlines()]
    k2mosaic_video(mosaic_filenames, rowrange=[670, 900], colrange=[580, 790])


if __name__ == '__main__':
    k2mosaic()

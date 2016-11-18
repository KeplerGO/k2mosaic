"""Convert a set of mosaics into a video or animated gif."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pl
import matplotlib.image as mimg

import os
import click

from astropy import visualization
from astropy.io import fits
import imageio
import numpy as np

from . import KEPLER_CHANNEL_SHAPE


class InvalidFrameException(Exception):
    pass


class KeplerMosaicVideoFrame(object):

    def __init__(self, fits_filename):
        self.fits_filename = fits_filename

    def to_fig(self, rowrange, colrange, extension=1, cmap='Greys_r', cut=None, dpi=50):
        """Turns a fits file into a cropped and contrast-stretched matplotlib figure."""
        with fits.open(self.fits_filename) as fts:
            if (-np.isnan(fts[extension].data)).sum() == 0:
                raise InvalidFrameException()
            image = fts[extension].data[rowrange[0]:rowrange[1], colrange[0]:colrange[1]]
            if cut is None:
                cut = np.percentile(image[-np.isnan(image)], [10, 99.5])
            image_scaled = visualization.scale_image(image, scale="log",
                                                     min_cut=cut[0], max_cut=cut[1]) #min_percent=0.5, max_percent=99.5)

        px_per_kepler_px = 20
        dimensions = [image.shape[0] * px_per_kepler_px, image.shape[1] * px_per_kepler_px]
        figsize = [dimensions[1]/dpi, dimensions[0]/dpi]
        dpi = 440 / float(figsize[0])
        fig = pl.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(1, 1, 1, axisbg='green')
        ax.matshow(image_scaled, aspect='auto',
                   cmap=cmap, origin='lower',
                   interpolation='nearest')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis('off')
        #ax.set_axis_bgcolor('red')
        fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
        fig.canvas.draw()
        return fig


class KeplerMosaicVideo(object):

    def __init__(self, mosaic_filenames,
                 rowrange=(0, KEPLER_CHANNEL_SHAPE[0]),
                 colrange=(0, KEPLER_CHANNEL_SHAPE[1])):
        self.mosaic_filenames = mosaic_filenames
        self.rowrange = rowrange
        self.colrange = colrange

    def get_frame(self, frame_number=0):
        return KeplerMosaicVideoFrame(self.mosaic_filenames[frame_number])

    def export_frames(self, extension=1, cut=None):
        for fn in click.progressbar(self.mosaic_filenames, label="Reading mosaics", show_pos=True):
            try:
                frame = KeplerMosaicVideoFrame(fn)
                fig = frame.to_fig(rowrange=self.rowrange, colrange=self.colrange, extension=extension, cut=cut)
                out_fn = "videoframe-" + os.path.basename(fn) + ".png"
                fig.savefig(out_fn, cmap='Greys_r', facecolor='#333333')
                pl.close(fig)
            except InvalidFrameException:
                print("InvalidFrameException for {}".format(fn))

    def to_movie(self, output_fn, fps=15., dpi=50, cut=None, cmap='gray', extension=1):
        viz = []
        with click.progressbar(self.mosaic_filenames, label="Reading mosaics", show_pos=True) as bar:
            for fn in bar:
                try:
                    frame = KeplerMosaicVideoFrame(fn)
                    fig = frame.to_fig(rowrange=self.rowrange, colrange=self.colrange,
                                       dpi=dpi, cut=cut, cmap=cmap, extension=extension,)
                    img = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
                    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
                    pl.close(fig)  # Avoid memory leak!
                    viz.append(img)
                except InvalidFrameException:
                    print("InvalidFrameException for {}".format(fn))
                    # Save the output as a movie
        if output_fn.endswith('.gif'):
            kwargs = {'duration': 1. / fps}
        else:
            kwargs = {'fps': fps}
        imageio.mimsave(output_fn, viz, **kwargs)

    def save_movie(self, output_fn=None, start=None, stop=None, step=None,
                   fps=15., dpi=None, min_percent=1., max_percent=95.,
                   cmap='gray', time_format='ut', show_flags=False, raw=False,
                   ignore_bad_frames=True,):
        """Save an animation.

        Parameters
        ----------
        output_fn : str
            The filename of the output movie.  The type of the movie
            is determined from the filename (e.g. use '.gif' to save
            as an animated gif). The default is a GIF file with the same name
            as the input FITS file.

        start : int
            Number or time of the first frame to show.
            If `None` (default), the first frame will be the start of the data.

        stop : int
            Number or time of the last frame to show.
            If `None` (default), the last frame will be the end of the data.

        step : int
            Spacing between frames.  Default is to set the stepsize
            automatically such that the movie contains 100 frames between
            start and stop.

        fps : float (optional)
            Frames per second.  Default is 15.0.

        dpi : float (optional)
            Resolution of the output in dots per Kepler pixel.
            The default is to produce output which is 440px wide.

        min_percent : float, optional
            The percentile value used to determine the pixel value of
            minimum cut level.  The default is 1.0.

        max_percent : float, optional
            The percentile value used to determine the pixel value of
            maximum cut level.  The default is 95.0.

        cmap : str, optional
            The matplotlib color map name.  The default is 'gray',
            can also be e.g. 'gist_heat'.

        raw : boolean, optional
            If `True`, show the raw pixel counts rather than
            the calibrated flux. Default: `False`.

        show_flags : boolean, optional
            If `True`, annotate the quality flags if set.

        ignore_bad_frames : boolean, optional
             If `True`, any frames which cannot be rendered will be ignored
             without raising a ``BadKeplerFrame`` exception. Default: `True`.
        """
        if output_fn is None:
            output_fn = self.mosaic_filenames[0].split('/')[-1] + '.gif'
        # Determine cut levels for contrast stretching from a sample of pixels
        vmin, vmax = self.cut_levels(min_percent=min_percent,
                                     max_percent=max_percent,
                                     raw=raw)
        # Determine the first/last frame number and the step size
        frameno_start, frameno_stop = self._frameno_range(start, stop, time_format)
        if step is None:
            step = int((frameno_stop - frameno_start) / 100)
            if step < 1:
                step = 1
        # Create the movie frames
        print('Creating {0}'.format(output_fn))
        viz = []
        for frameno in click.progressbar(np.arange(frameno_start, frameno_stop + 1, step, dtype=int)):
            try:
                fig = self.create_figure(frameno=frameno, dpi=dpi,
                                         vmin=vmin, vmax=vmax, cmap=cmap,
                                         raw=raw, time_format=time_format,
                                         show_flags=show_flags)
                img = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
                img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
                pl.close(fig)  # Avoids memory leak!
                viz.append(img)
            except BadKeplerFrame as e:
                log.debug(e)
                if not ignore_bad_frames:
                    raise e
        # Save the output as a movie
        if output_fn.endswith('.gif'):
            kwargs = {'duration': 1. / fps}
        else:
            kwargs = {'fps': fps}
        imageio.mimsave(output_fn, viz, **kwargs)

    def to_gif(self):
        pass

    def to_mp4(self):
        pass

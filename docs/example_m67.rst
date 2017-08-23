Example: M67 mosaic
===================

The K2 mission observed the open cluster M67 as part of Campaign 5.
The data on the cluster is available only
as a series of Target Pixel Files (TPFs) that each cover only a part
of the cluster.
In this example we will mosaic these into single images.

First, we need to create a list of the Target Pixel Files (TPFs)
that we wish to mosaic.
The easiest way to do this is to use the ``k2mosaic list`` tool,
which outputs a list of TPF urls for a given channel and campaign.

We know that, during Campaign 5, M67 fell on CCD channel #13.
Let's run the tpflist tool to identify the TPFs on this channel
and save the output to ``list-of-target-pixel-files.txt``::

    $ k2mosaic tpflist 5 13 > list-of-target-pixel-files.txt

If you inspect the output, you will find that it simply contains a list
of TPF URLs, one per line::

    $ head list-of-target-pixel-files.txt 
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008644-c05_lpd-targ.fits.gz
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008645-c05_lpd-targ.fits.gz
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008646-c05_lpd-targ.fits.gz
    ...

If you have a local copy of the desired data, e.g. downloaded through the
archive's `K2 Data Search interface <https://archive.stsci.edu/k2/data_search/search.php>`_,
then you can simply build a list using the unix ``ls`` command, e.g.::

    $ ls /path/to/directory/*fits.gz > list-of-target-pixel-files.txt


Having obtained a list of input files, we can now hand this list
to the ``k2mosaic mosaic`` tool to combine them into single FITS images.

Caution: by default, the mosaic command will create a FITS image for
*each* cadence, of which there are typically several thousands.
This will be slow.
Let's start by creating a FITS image for a specific cadence first,
by providing the optional ``--cadence`` argument::

    $ k2mosaic mosaic --cadence 110000 list-of-tpf-urls.txt

The above command will download the required TPF files (if needed)
and create a new FITS images called ``k2mosaic-c05-ch13-cad110000.fits``,
where ``c05`` refers to the campaign number,
``ch13`` is the CCD channel number,
and ``cad110000`` refers to the unique K2 cadence number.
The result should look like this:

  TODO: insert image.

The range of cadence numbers for a given campaign can be obtained
from the `data release notes <http://keplerscience.arc.nasa.gov/k2-data-release-notes.html>`_.

You are now ready to produce images for all cadences, by running::

    $ k2mosaic mosaic list-of-tpf-urls.txt

This will create additional files called ``k2mosaic-c05-ch13-cadxxxxxx.fits``.

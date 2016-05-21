K2mosaic: Mosaic Kepler/K2 pixel data
=======================================
**Combine Target Pixel Files (TPFs) obtained by NASA's Kepler spacecraft into wide-field images.**

.. image:: http://img.shields.io/travis/barentsen/k2mosaic/master.svg
    :target: http://travis-ci.org/barentsen/k2mosaic
    :alt: Travis status

.. image:: http://img.shields.io/badge/license-MIT-blue.svg
    :target: https://github.com/barentsen/k2mosaic/blob/master/LICENSE
    :alt: MIT license


K2mosaic is a command-line tool that makes it easy to combine
CCD pixel data obtained by `NASA's Kepler space telescope <http://keplerscience.nasa.gov>`_ into wide-field images.
The need for this tool arises from the fact that the two-wheeled extended Kepler mission, K2,
observed large clusters and moving targets (e.g. planets, comets, and asteroids).
The data for these is easier to inspect and analyze in a mosaicked form.

The tool takes Kepler's *Target Pixel Files (TPF)* as input
and turns them into more traditional per-cadence/per-CCD FITS images.
It also contains a feature to turn the mosaics into contrast-stretched animated gifs or MPEG-4 movies.
The *TPF files* are publically available from the 
`Kepler archive <https://archive.stsci.edu/missions/kepler/target_pixel_files/>`_
and the `K2 archive <https://archive.stsci.edu/missions/k2/target_pixel_files/>`_.


Example
-------
The K2 mission observed the open cluster M67 as part of Campaign 5.
The data on the cluster is available only
as a series of Target Pixel Files (TPFs) that each cover only a part
of the cluster. Let's mosaic those into a single image!

First, we need to create a list of the K2 Target Pixel Files (TPFs)
that we wish to mosaic.
The easiest way to do this is to use the `k2mosaic find` tool,
which outputs a list of TPF urls for a given channel and campaign.

We know that M67 fell on CCD channel #13 during Campaign 5,
so let's run this tool and save the output to ``list-of-target-pixel-files.txt``::

    $ k2mosaic find 5 13 > list-of-target-pixel-files.txt

If you inspect the output, you will find that it simply contains a list
of URLs to the data archive, specifying one TPF per line::

    $ head list-of-target-pixel-files.txt 
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008644-c05_lpd-targ.fits.gz
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008645-c05_lpd-targ.fits.gz
    http://archive.stsci.edu/missions/k2/target_pixel_files/c5/200000000/08000/ktwo200008646-c05_lpd-targ.fits.gz
    ...

If you have a local copy of the desired data, e.g. downloaded through the
archive's [K2 Data Search interface](https://archive.stsci.edu/k2/data_search/search.php),
then you can simply build a list using the unix ``ls`` command, e.g.::

    $ ls /path/to/directory/*fits.gz > list-of-target-pixel-files.txt


Having obtained a list of input files, we can now hand this list
to the ``k2mosaic mosaic`` tool to combine them into single FITS images.

Caution! By default, the mosaic command will create a FITS image for
*each* cadence contained in the first TPF file,
of which there are typically ~4000.  This will be slow.
Let's start by creating a FITS image for a specific cadence first,
by providing the optional ``--cadenceno`` argument::

    $ k2mosaic mosaic --cadenceno 110000 list-of-tpf-urls.txt

The above command will download the required TPF files (if needed)
and create a new FITS images called ``k2mosaic-c05-ch13-cad110000.fits``,
where ``c05`` refers to the campaign number,
``ch13`` is the CCD channel number,
and ``cad110000`` refers to the unique K2 cadence number.
The result should look like this:

  TODO: insert image.

The range of cadence numbers for a given campaign can be obtained
from the [data release notes](http://keplerscience.arc.nasa.gov/k2-data-release-notes.html).

You are now ready to produce images for all cadences, by running::

    $ k2mosaic mosaic list-of-tpf-urls.txt

This will create additional files called ``k2mosaic-cxx-chxx-cadxxxxxx.fits``.


Installation
------------
You need to have a working version of Python 3 installed
(Python 2 may work but is untested for now.)
If this requirement is met, you can install the latest stable version
of ``k2mosaic`` using pip::

    pip install k2mosaic

If you have a previous version installed, you can upgrade it using::

    pip install k2mosaic --upgrade

Or you can install the most recent development version
from the git repository as follows::

    git clone https://github.com/barentsen/k2mosaic.git
    cd k2mosaic
    python setup.py install

The ``setup.py`` script will automatically take care of installing the dependencies
and add the ``k2mosaic`` tool to the command line.


Usage
-----

``k2mosaic`` is a command-line tool that provides three sub-commands,
``find``, ``mosaic``, and ``video``,
which takes care of the following three operations:

* ``k2mosaic find`` allows the user to query the archive to identify a list of Target Pixel Files (TPFs) to mosaic, that is, it allows the user to list all TPFs for a given campaign and channel.
* ``k2mosaic mosaic`` takes a list of TPF files and produces FITS images that combine all the pixels in those TPFs. The list of input file can either by generated by `k2mosaic find` tool, or can simply be generated using e.g. the unix ``ls`` command. 
* ``k2mosaic video`` takes a list of mosaics produced in the previous step and collates them into an MPEG-4 movie or animated gif to produce a quicklook animation.


Attribution
-----------
Created by Geert Barentsen at the NASA Kepler/K2 Guest Observer Office.

If this tool aided your research, please cite it. Get in touch for instructions.

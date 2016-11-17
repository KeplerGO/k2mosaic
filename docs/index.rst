K2mosaic: Mosaic Kepler Pixel Data
==================================

**Mosaic Target Pixel Files (TPFs)
obtained by NASA's Kepler/K2 missions
into CCD-sized images and movies.**

K2mosaic is a command-line tool which allows the
postage stamp-sized pixel masks obtained by
`NASA's Kepler and K2 missions <http://keplerscience.nasa.gov>`_
to be stitched together into CCD-sized mosaics and movies.
The principal use is to take a set of *Target Pixel Files* (TPF)
and turn them into more traditional FITS image files --
one per CCD channel and per cadence.
K2mosaic can also be used
to create fancy animations from these mosaics.

The need for this tool arises from the fact
that the analysis of certain Kepler/K2 targets,
such as clusters and asteroids,
is more easily performed on mosaicked data.
Moreover such mosaics are useful to reveal the context
of single-star observations,
e.g. they enable users to check for the presence of instrumental noise
or nearby bright objects.


Basic usage
-----------

To create a mosaic of all pixels
obtained on CCD channel #65 during K2 Campaign 7,
you would run:

.. code-block:: shell

    $ pip install k2mosaic
    $ k2mosaic tpflist 7 65 > list-of-target-pixel-files.txt
    $ k2mosaic mosaic list-of-target-pixel-files.txt --cadence 119456

This will create a file called `k2mosaic-c07-ch65-cad119456.fits <_static/k2mosaic-c07-ch65-cad119456.png>`_.

User guide
----------

.. toctree::
   :maxdepth: 2

   installation
   commands
   example_pluto
   example_m67


License & Attribution
---------------------

Copyright 2016 Geert Barentsen and contributors.

K2mosaic is free software made available under the MIT License.
For details see `LICENSE <https://github.com/barentsen/k2mosaic/blob/master/LICENSE>`_.

If this tool aided your research, please cite it. Get in touch for instructions.

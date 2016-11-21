Commands
========

``k2mosaic`` is a command-line tool that provides three sub-commands:
``tpflist``, ``mosaic``, and ``movie``.
These take care of the following three operations:

* ``k2mosaic tpflist {{CAMPAIGN}} {{CHANNEL}}`` lists all the Target Pixel Files (TPFs) for a given campaign and channel.
* ``k2mosaic mosaic {{TPF_LIST}}`` takes a list of TPF files and turns them into a mosaicked image, producing one FITS file per cadence for a given channel.
* ``k2mosaic movie {{MOSAIC_LIST}}`` takes a list of mosaics produced in the previous step and collates them into an MPEG-4 movie or animated gif.

Use the ``--help`` option on each of these commands to learn more
about their usage.

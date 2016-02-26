# k2mosaic [![PyPI](http://img.shields.io/pypi/v/k2mosaic.svg)](https://pypi.python.org/pypi/K2ephem/) [![PyPI](http://img.shields.io/pypi/dm/k2mosaic.svg)](https://pypi.python.org/pypi/K2ephem/) [![Travis status](https://travis-ci.org/barentsen/k2mosaic.svg)](https://travis-ci.org/barentsen/k2mosaic)
***Create mosaics of pixel data observed by [NASA's K2 mission](http://keplerscience.arc.nasa.gov).***


## Installation
You need to have a working version of Python installed.
If this requirement is met, you can install the latest stable version
of `k2mosaic` using pip:
```
$ pip install k2mosaic
```
If you have a previous version installed, you can upgrade it using:
```
pip install k2mosaic --upgrade
```
Or you can install the most recent development version
from the git repository as follows:
```
$ git clone https://github.com/barentsen/k2mosaic.git
$ cd k2mosaic
$ python setup.py install
```
The `setup.py` script will automatically take care of installing the dependencies.

## Usage
After installation, you can call `k2mosaic` from the command line.
For example, to create a mosaic of campaign 6, channel 50, cadence 100:
```
$ k2mosaic 6 50 100
```

Or you can type `K2ephem --help` to see the detailed usage instructions:
```
$ k2mosaic --help                         
usage: k2mosaic [-h] [-d PATH] campaign channel cadence

Creates a mosaic of all K2 target pixel files in a given channel during a
single cadence.

positional arguments:
  campaign              Campaign number.
  channel               Channel number (1-84).
  cadence               Cadence number.

optional arguments:
  -h, --help            show this help message and exit
  -d PATH, --data_store PATH
                        Path to the directory that contains a mirror of http:/
                        /archive.stsci.edu/missions/k2/target_pixel_files/
```

## Attribution
Created by Geert Barentsen at the NASA Kepler/K2 Guest Observer Office.

If this tool aided your research, please cite it. (Get in touch for instructions.)
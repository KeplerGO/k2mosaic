# k2mosaic
***Create mosaics of pixel data observed by [NASA's K2 mission](http://keplerscience.arc.nasa.gov).***


## Installation
You need to have a working version of Python installed.
If this requirement is met, you can install the latest stable version
of `k2mosaic` using pip:
```
pip install k2mosaic
```
If you have a previous version installed, you can upgrade it using:
```
pip install k2mosaic --upgrade
```
Or you can install the most recent development version
from the git repository as follows:
```
git clone https://github.com/barentsen/k2mosaic.git
cd k2mosaic
python setup.py install
```
The `setup.py` script will automatically take care of installing the dependencies.

## Usage
After installation, you can call `k2mosaic` from the command line.
For example, to create a mosaic of cadence number 100 in channel 50 of campaign 6,
you may execute:
```
k2mosaic 6 50 100
```

Or you can type `k2mosaic --help` to see the detailed usage instructions:
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
                        Path to the directory that contains a mirror of the
                        target pixel files directory in the K2 data archive,
                        i.e. a directory that contains a mirror of http://arch
                        ive.stsci.edu/missions/k2/target_pixel_files/.

This tool will look for data in the directory specified by the --data_store
parameter. If that fails, it will look inside the directory specified by the
$K2DATA environment variable. If this fails as well, then the data will be
downloaded from the archive on the fly.
```

## Attribution
Created by Geert Barentsen at the NASA Kepler/K2 Guest Observer Office.

If this tool aided your research, please cite it. Get in touch for instructions.

#!/usr/bin/env python
import os
import sys
from setuptools import setup

# Prepare and send a new release to PyPI
if "release" in sys.argv[-1]:
    os.system("python setup.py sdist")
    os.system("twine upload dist/*")
    os.system("rm -rf dist/k2mosaic*")
    sys.exit()

# Load the __version__ variable without importing the package
exec(open('k2mosaic/version.py').read())

entry_points = {'console_scripts':
                ['k2mosaic = k2mosaic.ui:k2mosaic']}

setup(name='k2mosaic',
      version=__version__,
      description="Mosaic Target Pixel Files (TPFs) "
                  "obtained by NASA's Kepler/K2 missions "
                  "into CCD-sized images and movies.",
      long_description=open('README.rst').read(),
      author='Geert Barentsen',
      author_email='hello@geert.io',
      license='MIT',
      url='https://k2mosaic.geert.io',
      packages=['k2mosaic'],
      package_data={'k2mosaic': ['data/*.csv']},
      install_requires=['astropy>=2.0.8',
                        'numpy>=1.16',
                        'pandas',
                        'click',
                        'requests',
                        'imageio>=1',
                        'fitsio'],
      entry_points=entry_points,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Intended Audience :: Science/Research",
          "Topic :: Scientific/Engineering :: Astronomy",
          ],
      )

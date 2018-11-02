#!/usr/bin/env python
import os
import sys
from setuptools import setup

if "testpublish" in sys.argv[-1]:
    os.system("python setup.py sdist upload -r pypitest")
    sys.exit()
elif "publish" in sys.argv[-1]:
    os.system("python setup.py sdist upload -r pypi")
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
                        'numpy',
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

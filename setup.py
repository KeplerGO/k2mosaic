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
      description='Creates a mosaic of all K2 target pixel files '
                  'in a given channel during a single cadence.',
      author='Geert Barentsen',
      author_email='hello@geert.io',
      url='https://github.com/barentsen/k2mosaic',
      packages=['k2mosaic'],
      package_data={'k2mosaic': ['data/*.csv']},
      install_requires=['astropy>=0.4',
                        'numpy',
                        'pandas',
                        'tqdm',
                        'click',
                        'requests',
                        'imageio>=1'],
      entry_points=entry_points,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Intended Audience :: Science/Research",
          "Topic :: Scientific/Engineering :: Astronomy",
          ],
      )

from __future__ import (division, absolute_import)
import os

from .version import __version__

PACKAGEDIR = os.path.dirname(os.path.abspath(__file__))
KEPLER_CHANNEL_SHAPE = (1070, 1132)  # (rows, cols)

from .core import *

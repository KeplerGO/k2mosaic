import pytest

import k2mosaic
from k2mosaic import ui


def test_commands():
    """Check if the command-line tools can be run without crash."""
    # If a command runs successfully it will raise a SystemExit at the end
    with pytest.raises(SystemExit):
        ui.k2mosaic()
    # Also check the sub-commands:
    with pytest.raises(SystemExit):
        ui.mosaic()
    with pytest.raises(SystemExit):
        ui.movie()
    with pytest.raises(SystemExit):
        ui.tpflist()


def test_has_version_variable():
    k2mosaic.__version__

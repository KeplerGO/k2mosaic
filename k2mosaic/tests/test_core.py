import pytest

from k2mosaic import ui

def test_main():
    with pytest.raises(SystemExit):
        ui.k2mosaic()

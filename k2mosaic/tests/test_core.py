import pytest

import k2mosaic

def test_main():
    with pytest.raises(SystemExit):
        k2mosaic.k2mosaic_main()

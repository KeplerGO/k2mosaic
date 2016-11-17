from k2mosaic import mast


def test_kepler_tpf_url():
    url = mast.tpf_url('KPLR004912785-2010078095331')
    assert(url == 'https://archive.stsci.edu/missions/kepler/target_pixel_files/'
                  '0049/004912785/kplr004912785-2010078095331_lpd-targ.fits.gz')


def test_k2_tpf_url():
    url = mast.tpf_url('KTWO210854069-C04')
    assert(url == 'https://archive.stsci.edu/missions/k2/target_pixel_files/'
                  'c4/210800000/54000/ktwo210854069-c04_lpd-targ.fits.gz')

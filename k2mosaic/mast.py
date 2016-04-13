"""Query and retrieve target pixel files from the MAST archive's API.
"""
import requests

MAST_URL = 'http://archive.stsci.edu'
K2_TPF_URL = MAST_URL + '/missions/k2/target_pixel_files/'


class NoDataFoundException(Exception):
    pass


def generate_mast_query_url(campaign, channel=None, obsmode="LC"):
    url = MAST_URL + '/k2/data_search/search.php?'
    url += 'action=Search'
    url += '&max_records=123456789'
    url += '&selectedColumnsCsv=ktc_k2_id'
    url += '&outputformat=JSON'
    url += '&ktc_target_type={}'.format(obsmode)
    url += '&sci_campaign={:d}'.format(campaign)
    if channel is not None:
        url += '&sci_channel={:d}'.format(channel)
    return url


def get_k2ids(campaign, channel=None, obsmode="LC"):
    """Returns a `Response` object."""
    return requests.get(generate_mast_query_url(campaign, channel, obsmode))


def k2_tpf_urls_by_campaign(campaign, channel=None, short_cadence=False, base_url=K2_TPF_URL):
    """Returns a list of URLs pointing to the TPF files of a given campaign/channel."""
    if short_cadence:
        obsmode = 'SC'
    else:
        obsmode = 'LC'
    resp = get_k2ids(campaign, channel, obsmode)
    if resp.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET k2ids {}'.format(resp.status_code))
    try:
        urls = [k2_tpf_url(entry['K2 ID'], campaign, obsmode, base_url)
                for entry in resp.json()]
        return urls
    except ValueError:
        raise NoDataFoundException("Error: no data found for these parameters.")


def k2_tpf_url(k2id, campaign, obsmode="LC", base_url=K2_TPF_URL):
    """Returns the URL of a TPF file given its k2id (i.e. EPIC id)."""
    k2id = str(k2id)
    fn_prefix = 'ktwo' + k2id + '-c' + '{0:02d}'.format(campaign)
    if obsmode == "LC":
        fn_suffix = "_lpd-targ.fits.gz"
    else:
        fn_suffix = "_spd-targ.fits.gz"
    url = base_url + 'c{0:d}/{1}00000/{2}000/{3}{4}'.format(
                        campaign, k2id[0:4], k2id[4:6], fn_prefix, fn_suffix)
    return url

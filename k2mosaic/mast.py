"""Query Target Pixel Files from the Kepler/K2 archive at MAST.
"""
import requests

MAST_URL = 'https://archive.stsci.edu'


class NoDataFoundException(Exception):
    pass


class ApiError(Exception):
    pass


def data_search_url(campaign, mission='k2', channel=None, obsmode='LC'):
    """Returns a query URL to search target pixel files using the MAST API."""
    url = '{}/{}/data_search/search.php?'.format(MAST_URL, mission)
    url += 'action=Search'
    url += '&max_records=123456789'
    url += '&selectedColumnsCsv=sci_data_set_name'
    url += '&outputformat=JSON'
    url += '&ktc_target_type={}'.format(obsmode)
    if mission == 'k2':
        url += '&sci_campaign={:d}'.format(campaign)
    else:  # Kepler
        url += '&sci_data_quarter={:d}'.format(campaign)
    if channel is not None:
        url += '&sci_channel={:d}'.format(channel)
    return url


def data_search(campaign, mission='k2', channel=None, obsmode="LC"):
    """Returns a `Response` object."""
    return requests.get(data_search_url(campaign, mission=mission, channel=channel, obsmode=obsmode))


def get_tpf_urls(quarter_or_campaign, channel=None, short_cadence=False):
    """Returns a list of URLs pointing to the TPF files of a given campaign/channel.

    Parameters
    ----------
    quarter_or_campaign : str
        e.g. 'C4', 'Q4', or '4'.
    """
    prefix = quarter_or_campaign.lower()[0]
    if prefix == 'c':
        mission = 'k2'
        campaign = int(quarter_or_campaign[1:])
    elif prefix == 'q':
        mission = 'kepler'
        campaign = int(quarter_or_campaign[1:])
    else:  # Just a number?
        mission = 'k2'
        campaign = int(quarter_or_campaign)
    if short_cadence:
        obsmode = 'SC'
    else:
        obsmode = 'LC'
    resp = data_search(campaign, mission=mission, channel=channel, obsmode=obsmode)
    if resp.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET data_search {}'.format(resp.status_code))
    try:
        urls = [tpf_url(entry['Dataset Name'], obsmode) for entry in resp.json()]
        return urls
    except ValueError:
        raise NoDataFoundException("Error: no data found for these parameters.")


def tpf_url(data_set_name, obsmode='LC'):
    """Returns the URL of a Target Pixel File file given its data set name.

    Parameters
    ----------
    data_set_name : str
        Data identifier in the MAST archive,
        e.g. ''KTWO210854069-C04' or KPLR004912785-2010078095331'.
    """
    name = data_set_name.lower()
    if name.startswith('kplr'):
        return tpf_url_kepler(data_set_name, obsmode)
    else:
        return tpf_url_k2(data_set_name, obsmode)


def tpf_url_kepler(data_set_name, obsmode='LC'):
    """Given a Kepler data set name, return the URL of the Target Pixel File.

    Parameters
    ----------
    data_set_name : str
        e.g. 'KTWO210854069-C04'.

    obsmode : str
        Must be 'LC' (long cadence) or 'SC' (short cadence).
    """
    name = data_set_name.lower()
    if obsmode == "LC":  # long cadence
        suffix = "_lpd-targ.fits.gz"
    else:  # short cadence
        suffix = "_spd-targ.fits.gz"
    url = MAST_URL + '/missions/kepler/target_pixel_files/'
    url += '{}/{}/{}{}'.format(name[4:8], name[4:13], name, suffix)
    return url


def tpf_url_k2(data_set_name, obsmode='LC'):
    """Given a K2 data set name, return the URL of the Target Pixel File.

    Parameters
    ----------
    data_set_name : str
        e.g. 'KTWO210854069-C04'.

    obsmode : str
        Must be 'LC' (long cadence) or 'SC' (short cadence).
    """
    name = data_set_name.lower()
    if obsmode == "LC":  # long cadence
        suffix = "_lpd-targ.fits.gz"
    else:  # short cadence
        suffix = "_spd-targ.fits.gz"
    campaign_dir = 'c{:01d}'.format(int(name.split('-c')[1]))  # remove leading zeros
    url = MAST_URL + '/missions/k2/target_pixel_files/'
    url += '{}/{}00000/{}000/'.format(campaign_dir, name[4:8], name[8:10])
    url += '{}{}'.format(name, suffix)
    return url

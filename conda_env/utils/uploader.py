try:
    from binstar_client.utils import get_binstar
except ImportError:
    get_binstar = None


def is_installed():
    """
    is Binstar-cli installed?
    :return: True/False
    """
    return get_binstar is not None

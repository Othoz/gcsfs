# flake8: noqa
from pkg_resources import get_distribution, DistributionNotFound

from ._gcsfs import GCSFS

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass

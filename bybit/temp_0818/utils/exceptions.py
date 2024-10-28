"""
This utility is used to handle errors.
"""


class OpenMarketError(Exception):
    """
    This error is raised when the market is open.
    """
    pass


class CloseMarketError(Exception):
    """
    This error is raised when the market is closed.
    """
    pass

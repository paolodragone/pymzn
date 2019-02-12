"""Logging configuration."""

import logging


__all__ = ['debug', 'logger']


logger = logging.getLogger(__package__)

_debug_handler = None
logger.addHandler(logging.NullHandler())


def debug(dbg=True):
    """Enables or disables debugging messages on the standard output."""
    global _debug_handler
    if dbg and _debug_handler is None:
        _debug_handler = logging.StreamHandler()
        logger.addHandler(_debug_handler)
        logger.setLevel(logging.DEBUG)
    elif not dbg and _debug_handler is not None:
        logger.removeHandler(_debug_handler)
        _debug_handler = None
        logger.setLevel(logging.WARNING)


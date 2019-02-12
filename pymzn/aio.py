
try:
    from .mzn.aio import *
except SyntaxError as err:
    raise ImportError(
        'You need Python 3.6 or higher to use the pymzn.aio package.'
    ) from err


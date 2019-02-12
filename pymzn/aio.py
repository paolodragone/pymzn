
try:
    from .mzn import aio as _aio
    from .mzn.aio import *
    __all__ = _aio.__all__
except SyntaxError as err:
    raise ImportError(
        'You need Python 3.6 or higher to use the pymzn.aio package.'
    ) from err


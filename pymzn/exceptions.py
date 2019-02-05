
class MiniZincError(RuntimeError):
    """Generic error for the MiniZinc functions."""

    def __init__(self, msg=None):
        super().__init__(msg)
        self._mzn_file = None
        self._stderr = None

    @property
    def stderr(self):
        return self._stderr

    @property
    def mzn_file(self):
        """str: the mzn file that generated the error."""
        return self._mzn_file

    def _set(self, _mzn_file, _stderr):
        self._mzn_file = _mzn_file
        self._stderr = _stderr
        self.args = ('{}: {}'.format(
            self._mzn_file, self.args[0] + '\n{}'.format(_stderr)
        ),)


class MiniZincUnsatisfiableError(MiniZincError):
    """Error raised when a minizinc problem is found to be unsatisfiable."""

    def __init__(self):
        super().__init__('The problem is unsatisfiable.')


class MiniZincUnknownError(MiniZincError):
    """Error raised when minizinc returns no solution (unknown)."""

    def __init__(self):
        super().__init__('The solution of the problem is unknown.')


class MiniZincUnboundedError(MiniZincError):
    """Error raised when a minizinc problem is found to be unbounded."""

    def __init__(self):
        super().__init__('The problem is unbounded.')


class MiniZincUnsatOrUnboundedError(MiniZincError):
    """Error raised when a minizinc problem is found to be unsatisfiable or
    unbounded.
    """

    def __init__(self):
        super().__init__('The problem is unsatisfiable or unbounded.')


class MiniZincGenericError(MiniZincError):
    """Error raised when an error occurs but it is none of the above."""

    def __init__(self):
        super().__init__('The problem raised an error.')


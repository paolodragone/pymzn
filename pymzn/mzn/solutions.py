

class Solutions:
    """Represents a solution stream from the `minizinc` function.

    This class populates lazily but can be referenced and iterated as a list.

    Attributes
    ----------
    complete : bool
        Whether the stream includes the complete set of solutions. This means
        the stream contains all solutions in a satisfiability problem, or it
        contains the global optimum for maximization/minimization problems.
    """

    # TODO: add option to not save solutions

    def __init__(self, stream):
        self._stream = stream
        self._solns = []
        self.complete = False
        self._iter = None
        self._stats = None

    @property
    def statistics(self):
        self._fetch_all()
        return self._stats

    def _fetch(self):
        try:
            solution = next(self._stream)
            self._solns.append(solution)
            return solution
        except StopIteration as stop:
            complete, stats = stop.value
            self.complete = complete
            if stats:
                self._stats = stats
            self._stream = None
        return None

    def _fetch_all(self):
        while self._stream:
            self._fetch()

    def __len__(self):
        self._fetch_all()
        return len(self._solns)

    def __next__(self):
        if self._stream:
            return self._fetch()
        else:
            if not self._iter:
                self._iter = iter(self._solns)
            try:
                return next(self._iter)
            except StopIteration:
                self._iter = iter(self._solns)
                raise

    def __iter__(self):
        if not self._stream:
            self._iter = iter(self._solns)
        return self

    def __getitem__(self, key):
        self._fetch_all()
        return self._solns[key]

    def __repr__(self):
        self._fetch_all()
        return repr(self._solns)

    def __str__(self):
        self._fetch_all()
        return str(self._solns)




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
    def __init__(self, queue *, keep=True):
        self._queue = queue
        self._keep = keep
        self._solns = [] if keep else None
        self._n_solns = 0
        self.complete = False
        self.stats = None

    @property
    def statistics(self):
        return self.stats

    def _fetch(self):
        while not self.queue.empty():
            soln = self.queue.get_nowait()
            if self._keep:
                self._solns.append(soln)
            self._n_solns += 1
            yield soln

    def _fetch_all(self):
        for soln in self._fetch():
            pass

    def __len__(self):
        return self._n_solns

    def __iter__(self):
        if self._keep:
            self._fetch_all()
            return iter(self._solns)
        else:
            return self._fetch()

    def __getitem__(self, key):
        if not self._keep:
            raise RuntimeError(
                'Cannot address directly if keep_solutions is False'
            )
        self._fetch_all()
        return self._solns[key]

    def __repr__(self):
        if self._keep:
            self._fetch_all()
            return repr(self._solns)
        else:
            return repr(self)

    def __str__(self):
        if self._keep:
            self._fetch_all()
            return str(self._solns)
        else:
            return str(self)


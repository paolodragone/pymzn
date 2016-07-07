import os.path


class _Config(object):

    def __init__(self):
        self._mzn2fzn_cmd = 'mzn2fzn'
        self._solns2out_cmd = 'solns2out'
        self._gecode_cmd = 'gecode'
        self._optimatsat_cmd = 'optimatsat'

    @property
    def mzn2fzn_cmd(self):
        return self._mzn2fzn_cmd

    @mzn2fzn_cmd.setter
    def mzn2fzn_cmd(self, cmd):
        if os.path.exists(cmd):
            self._mzn2fzn_cmd = cmd
        else:
            raise ValueError('The file does not exist: {}'.format(cmd))

    @property
    def solns2out_cmd(self):
        return self._solns2out_cmd

    @solns2out_cmd.setter
    def solns2out_cmd(self, cmd):
        if os.path.exists(cmd):
            self._solns2out_cmd = cmd
        else:
            raise ValueError('The file does not exist: {}'.format(cmd))

    @property
    def gecode_cmd(self):
        return self._gecode_cmd

    @gecode_cmd.setter
    def gecode_cmd(self, cmd):
        if os.path.exists(cmd):
            self._gecode_cmd = cmd
        else:
            raise ValueError('The file does not exist: {}'.format(cmd))

    @property
    def optimatsat_cmd(self):
        return self._optimatsat_cmd

    @optimatsat_cmd.setter
    def optimatsat_cmd(self, cmd):
        if os.path.exists(cmd):
            self._optimatsat_cmd = cmd
        else:
            raise ValueError('The file does not exist: {}'.format(cmd))


_config = _Config()

mzn2fzn_cmd = _config.mzn2fzn_cmd
solns2out_cmd = _config.solns2out_cmd
gecode_cmd = _config.gecode_cmd
optimatsat_cmd = _config.optimatsat_cmd

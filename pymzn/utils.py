
import os
import time
import signal
import logging
import subprocess

from subprocess import Popen, PIPE, TimeoutExpired, CalledProcessError


class Process:

    def __init__(self, args):
        self.args = args
        self._process = None
        self.start_time = None
        self.end_time = None
        self.timeout = None
        self.stdout_data = None
        self.stderr_data = None
        self.expired = False

    @property
    def running_time(self):
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def stdout(self):
        return self._process.stdout

    def _check_alive(self):
        self.returncode = retcode = self._process.poll()
        if retcode is None:
            return
        self.end_time = time.time()
        if retcode:
            if self._process.stderr.closed:
                stderr = self.stderr_data
            else:
                self.stderr_data = stderr = self._process.stderr.read()
            raise CalledProcessError(retcode, self.args, None, stderr)
        self.complete = True

    def _check_timeout(self):
        if not self.timeout:
            return
        if self.running_time > self.timeout:
            self.end_time = time.time()
            self.stderr_data = stderr = self._process.stderr.read()
            self.kill()
            self.expired = True
            raise TimeoutExpired(self.args, self.timeout, None, stderr)

    def kill(self):
        if not self._process:
            raise RuntimeError('The process has not started yet')
        self._process.kill()
        self._process.stdout.close()
        self._process.stderr.close()

    def lines(self):
        if not self._process:
            raise RuntimeError('The process has not started yet')
        stdout = self._process.stdout
        while not stdout.closed:
            self._check_alive()
            self._check_timeout()
            line = stdout.readline()
            if line == '':
                break
            yield line
        return

    def __iter__(self):
        return self.lines()

    def run_async(self, stdin=None, timeout=None):
        if self._process:
            raise RuntimeError('Process already started')
        self.timeout = timeout
        self.start_time = time.time()
        self._process = subprocess.Popen(
            self.args, bufsize=0, universal_newlines=True, stdin=stdin,
            stdout=PIPE, stderr=PIPE
        )
        return self

    def run(self, input=None, timeout=None):
        if self._process:
            raise RuntimeError('Process already started')

        self.start_time = time.time()
        self.timeout = timeout
        with subprocess.Popen(
                self.args, bufsize=1, universal_newlines=True,
                stdin=PIPE, stdout=PIPE, stderr=PIPE
        ) as self._process:
            try:
                self.stdout_data, self.stderr_data = \
                        self._process.communicate(input, timeout)
                self._check_alive()
            except KeyboardInterrupt:
                self.kill()
                self.returncode = 0
            except TimeoutExpired:
                self.stdout_data, self.stderr_data = self._process.communicate()
                self.kill()
                self._check_alive()
                raise TimeoutExpired(
                    self.args, self.timeout, self.stdout_data, self.stderr_data
                )
            finally:
                self.end_time = time.time()
        return self

    def close(self):
        self._check_alive()
        self.kill()


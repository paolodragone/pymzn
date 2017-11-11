
from threading import Thread, Lock
from time import monotonic as _time
from subprocess import Popen, PIPE, TimeoutExpired, CalledProcessError


__all__ = ['Process']


class Process:

    def __init__(self, args):
        self.args = args
        self.returncode = None
        self.timeout = None
        self.stdout_data = None
        self.stderr_data = None
        self.expired = False
        self.interrupted = False
        self.async = False
        self._start = None
        self._end = None
        self._process = None
        self._process_lock = Lock()
        self._waiter_thread = None

    @property
    def started(self):
        return self._process is not None

    @property
    def alive(self):
        return self.returncode is None

    @property
    def completed(self):
        return self.returncode == 0

    @property
    def runtime(self):
        end = self._end or _time()
        return end - self._start

    @property
    def stdout(self):
        return self._process.stdout

    @property
    def stderr(self):
        return self._process.stderr

    def _check_started(self):
        if self.started:
            raise RuntimeError('Process already started')

    def run(self, input=None, timeout=None):
        self._check_started()
        popenkwargs = {'bufsize': 1, 'universal_newlines': True,
                       'stdin': PIPE, 'stdout': PIPE, 'stderr': PIPE}
        self._process_lock.acquire()
        self.timeout = timeout
        self._start = _time()
        with Popen(self.args, **popenkwargs) as self._process:
            try:
                stdout, stderr = self._process.communicate(input, timeout)
                self.stdout_data, self.stderr_data = stdout, stderr
            except KeyboardInterrupt:
                self._process.kill()
                self._process.wait()
                self.interrupted = True
            except TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate()
                self.stdout_data, self.stderr_data = stdout, stderr
                self.expired = True
                raise TimeoutExpired(self.args, timeout, stdout, stderr)
            except:
                self._process.kill()
                self._process.wait()
                raise
            finally:
                self._end = _time()
                self.returncode = retcode = self._process.poll()
                self._process_lock.release()
                if not (self.expired or self.interrupted) and self.returncode:
                    stdout, stderr = self.stdout_data, self.stderr_data
                    raise CalledProcessError(retcode, self.args, stdout, stderr)
        return self

    def _wait(self):
        remaining = None
        if self.timeout:
            remaining = self.timeout + self._start - _time()
        try:
            self._process.wait(remaining)
        except KeyboardInterrupt:
            self._process_lock.acquire()
            self._process.kill()
            self._process.wait()
            self._process_lock.release()
            self.interrupted = True
        except TimeoutExpired:
            self._process_lock.acquire()
            self._process.kill()
            stdout, stderr = self._process.communicate()
            self._process_lock.release()
            self.stdout_data, self.stderr_data = stdout, stderr
            self.expired = True
            raise TimeoutExpired(self.args, timeout, stdout, stderr)
        except:
            self._process_lock.acquire()
            self._process.kill()
            self._process.wait()
            self._process_lock.release()
            raise
        finally:
            self._end = _time()
            self.returncode = retcode = self._process.poll()
            self._cleanup()
            if not (self.expired or self.interrupted) and self.returncode:
                stdout, stderr = self.stdout_data, self.stderr_data
                raise CalledProcessError(retcode, self.args, stdout, stderr)

    def start(self, stdin=None, timeout=True):
        self._check_started()
        popenkwargs = {'bufsize': 0, 'universal_newlines': True,
                       'stdin': stdin, 'stdout': PIPE, 'stderr': PIPE}
        self._process_lock.acquire()
        if not self.started:
            self.async = True
            self.timeout = timeout
            self._start = _time()
            self._process = Popen(self.args, **popenkwargs)
            self._waiter_thread = Thread(target=self._wait)
            self._waiter_thread.start()
            self._process_lock.release()
        else:
            self._process_lock.release()
            raise RuntimeError('Process already started')
        return self

    def _cleanup(self):
        if self._process.stdout:
            self._process.stdout.close()
        if self._process.stderr:
            self._process.stderr.close()
        if self._process.stdin:
            self._process.stdin.close()

    def stop(self):
        if not self._process or not self.alive:
            return
        self._process_lock.acquire()
        self._process.kill()
        self._waiter_thread.join()
        self._process_lock.release()

    def readlines(self):
        if not self.started or not self.async:
            raise RuntimeError('The process has not been started.')
        stdout = self._process.stdout
        try:
            while not stdout.closed:
                try:
                    line = ''
                    self._process_lock.acquire()
                    if not stdout.closed:
                        line = stdout.readline()
                    self._process_lock.release()
                    if line == '':
                        break
                    yield line
                finally:
                    if self._process_lock.locked():
                        self._process_lock.release()
        finally:
            self._waiter_thread.join()

    def __iter__(self):
        return self.readlines()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.alive:
            self.stop()


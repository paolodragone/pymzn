
from time import monotonic as _time
from asyncio.subprocess import create_subprocess_exec, PIPE


__all__ = ['start_process']


class ProcessWrapper:

    def __init__(self, proc):
        self._proc = proc
        self.start_time = _time()
        self.end_time = None
        self.stdout_data = None
        self.stderr_data = None
        self._finalized = False

    def __repr__(self):
        return repr(self._proc)

    @property
    def returncode(self):
        return self._proc.returncode

    async def wait(self):
        return await self._proc.wait()

    def send_signal(self, signal):
        self._proc.send_signal(signal)

    def terminate(self):
        self._proc.terminate()

    def kill(self):
        self._proc.kill()

    @property
    def stdout(self):
        return self._stdout_stream

    @property
    def stderr(self):
        return self._stderr_stream

    async def read(self):
        if self._finalized:
            return self.stdout_data

        try:
            stdout, stderr = await self._proc.communicate()
            self.stdout_data = stdout
            self.stderr_data = stderr
        except:
            if self.returncode is None:
                try:
                    self.terminate()
                    await self.wait()
                except:
                    self.kill()
                    raise
            raise
        finally:
            self.end_time = _time()
            self._finalized = True

    async def readlines(self):
        try:
            while not self._proc.stdout.at_eof():
                yield await self._proc.stdout.readline()
            _, stderr = await self._proc.communicate()
            self.stderr_data = stderr
        except:
            try:
                self.terminate()
                await self.wait()
            except:
                self.kill()
                raise
            raise
        finally:
            self.end_time = _time()
            self._finalized = True


async def start_process(*args, stdin=PIPE):
    return ProcessWrapper(await create_subprocess_exec(
        *args, stdin=stdin, stdout=PIPE, stderr=PIPE
    ))


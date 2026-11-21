"""TestClient harness for sandboxes which deny socketpair.send().

Asyncio normally wakes its selector by writing to a local socket. The managed
workspace permits socket creation but denies that write with EPERM. A periodic
test-only timer lets queued cross-thread callbacks run without network access.
This changes no application, model, auth, database, or provider behavior.
"""
import asyncio

from fastapi.testclient import TestClient as StarletteTestClient


class PollingTestLoop(asyncio.SelectorEventLoop):
    def run_forever(self):
        timer = None

        def tick():
            nonlocal timer
            timer = self.call_later(0.01, tick)

        tick()
        try:
            return super().run_forever()
        finally:
            if timer:
                timer.cancel()


class TestClient(StarletteTestClient):
    __test__ = False

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("backend_options", {"loop_factory": PollingTestLoop})
        super().__init__(*args, **kwargs)

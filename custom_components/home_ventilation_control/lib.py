"""Library to connect to HomeVentilationControl devices."""

import asyncio
import socket, errno, json, time
from asyncio.exceptions import TimeoutError, CancelledError

class HomeVentilationControlException(BaseException):
    pass
class HomeVentilationControlTimeoutException(HomeVentilationControlException):
    pass

class HomeVentilationControlDevice:
    REQUEST_TIMEOUT = 5
    KEEPALIVE_INTERVAL = 303
    UPDATE_TIMEOUT = 910
    DEFAULT_PORT = 38866

    @staticmethod
    def _recvfrom(s, unique_id = None):
        while True:
            try:
                data, peer = s.recvfrom(2048)
                data = json.loads(data)["HomeVentilationControl"]
                if data["unique_id"] == unique_id or unique_id is None:
                    return data, peer
            except OSError as ex:
                if ex.errno == errno.EWOULDBLOCK:
                    return None, None
                raise
            except (json.decoder.JSONDecodeError, KeyError):
                pass

    @classmethod
    async def _async_recvfrom(cls, s, unique_id = None, timeout: float = REQUEST_TIMEOUT):
        async def _recv():
            while True:
                data, peer = cls._recvfrom(s, unique_id)
                if data:
                    return data, peer
                await asyncio.sleep(0.1)
        try:
            return await asyncio.wait_for(_recv(), timeout)
        except TimeoutError as ex:
            if unique_id is not None:
                raise HomeVentilationControlTimeoutException(f"no answer from device '{unique_id}'") from ex
        except OSError as ex:
            raise HomeVentilationControlException("error with socket communication") from ex
        return None, None

    @classmethod
    async def discover(cls, discovery_address, unique_id = None, broadcast = False) -> dict[str, '__class__']:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(False)
        if broadcast:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.sendto(json.dumps({"HomeVentilationControl": {}}).encode(), discovery_address)
        except BaseException as ex:
            s.close()
            raise HomeVentilationControlException(f"Cannot connect to {discovery_address}: {ex}") from ex

        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 0)
        replies = [await cls._async_recvfrom(s, unique_id)]
        if replies[-1][0] and not unique_id:
            await asyncio.sleep(1)
            while replies[-1][0]:
                replies.append(cls._recvfrom(s))

        discovered = {}
        for data, peer in replies:
            peer = peer if broadcast else discovery_address
            if data and (u := data["unique_id"]) not in discovered:
                discovered[u] = cls(data, peer, s)
                s = None
        if s:
            s.close()
        return discovered

    def __init__(self, data, peer, socket_):
        self.socket = socket_ or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self.socket.connect(peer)
        self.unique_id = data["unique_id"]
        self.data = data
        self.peer = peer
        self._time_updated = time.time()
        self._time_keepalive = 0

    def send(self, request = {}):
        self.socket.send(json.dumps({"HomeVentilationControl": request | {"unique_id": self.unique_id}}).encode())
        self._time_keepalive = time.time()

    def force_update(self):
        self.send({"udp_force_update": 1})
        # FIXME: Wait for response?

    def recv(self):
        while self.socket:
            data, peer = self._recvfrom(self.socket, self.unique_id)
            if not data:
                break
            self.data = data
            self._time_updated = time.time()

    async def wait(self):
        data, peer = await self._async_recvfrom(self.socket, self.unique_id)
        self.data = data
        self._time_updated = time.time()

    def keep_alive(self):
        if self._time_keepalive < time.time() - self.KEEPALIVE_INTERVAL:
            self.send()

    def timeout(self):
        return self._time_updated < time.time() - self.UPDATE_TIMEOUT

    def get(self, path):
        try:
            d = self.data
            for component in path.split("."):
                d = d[component]
            return d
        except:
            return None

    def close(self):
        self.socket.close()

    @property
    def name(self):
        return self.get("conf.name") or self.unique_id

# CLI test code.
if __name__ == "__main__":
    import asyncio

    async def main():
        devices = None
        while True:
            if not devices:
                print("discovering...")
                try:
                    devices = await HomeVentilationControlDevice.discover(("255.255.255.255", 38866), broadcast = True)
                except BaseException as ex:
                    print("Error in discovery:", ex)
            for device in devices.values():
                device.keep_alive()
                device.recv()
                try:
                    print(device.get("clock"), "| c0 =", device.get("0.controller.millivolts"), "mV")
                except BaseException as ex:
                    print(ex)
            await asyncio.sleep(5)

    asyncio.run(main())

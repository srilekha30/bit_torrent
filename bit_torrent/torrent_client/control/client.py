import asyncio
import logging   # for event logging system
from typing import Callable, TypeVar #to simplify complex type signatures (specifies format)

from torrent_client.control.manager import ControlManager
from torrent_client.control.server import ControlServer


__all__ = ['ControlClient']


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


T = TypeVar('T')


class ControlClient:
    def __init__(self):
        self._reader = None  # type: asyncio.StreamReader
        self._writer = None  # type: asyncio.StreamWriter

    async def connect(self):
        #if port is in range(6995 to 6999)
        for port in ControlServer.PORT_RANGE:
            try:
                self._reader, self._writer = await asyncio.open_connection(host=ControlServer.HOST, port=port)

                message = await self._reader.readexactly(len(ControlServer.HANDSHAKE_MESSAGE))
                if message != ControlServer.HANDSHAKE_MESSAGE:
                    raise RuntimeError('Unknown control server protocol')
            except Exception as e:
                self.close()
                self._reader = None
                self._writer = None
                logger.debug('failed to connect to port %s: %r', port, e)    # else connection fails with given port no
            else:
                break
        else:
            raise RuntimeError('Failed to connect to a control server') 

    async def execute(self, action: Callable[[ControlManager], T]) -> T:
        ControlServer.send_object(action, self._writer)
        result = await ControlServer.receive_object(self._reader)

        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        if self._writer is not None:
            self._writer.close()

    async def __aenter__(self) -> 'ControlClient':
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()

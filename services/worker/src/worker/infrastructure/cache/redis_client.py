from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse


class RedisError(RuntimeError):
    pass


@dataclass
class _RedisEndpoint:
    host: str
    port: int


def _parse_redis_endpoint(url: str) -> _RedisEndpoint:
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise RedisError(f"Unsupported Redis URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise RedisError("Redis URL missing hostname")
    return _RedisEndpoint(host=parsed.hostname, port=int(parsed.port or 6379))


class AsyncRedisClient:
    _CRLF: Final[bytes] = b"\r\n"

    def __init__(self, url: str) -> None:
        self._url = url
        self._endpoint = _parse_redis_endpoint(url)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def _ensure_conn(self) -> None:
        if self._writer is not None and not self._writer.is_closing():
            return
        self._reader, self._writer = await asyncio.open_connection(
            self._endpoint.host, self._endpoint.port
        )

    async def aclose(self) -> None:
        async with self._lock:
            if self._writer is not None:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                finally:
                    self._writer = None
                    self._reader = None

    async def _read_line(self) -> bytes:
        assert self._reader is not None
        line = await self._reader.readline()
        if not line:
            raise RedisError("Redis connection closed")
        if not line.endswith(self._CRLF):
            raise RedisError("Malformed Redis response")
        return line[:-2]

    async def _read_resp(self):
        line = await self._read_line()
        if not line:
            raise RedisError("Empty Redis response")

        prefix = line[:1]
        rest = line[1:]

        if prefix == b"+":
            return rest.decode("utf-8", errors="replace")
        if prefix == b"-":
            raise RedisError(rest.decode("utf-8", errors="replace"))
        if prefix == b":":
            return int(rest)
        if prefix == b"$":
            n = int(rest)
            if n == -1:
                return None
            assert self._reader is not None
            data = await self._reader.readexactly(n + 2)
            if not data.endswith(self._CRLF):
                raise RedisError("Malformed bulk string")
            return data[:-2].decode("utf-8", errors="replace")
        if prefix == b"*":
            count = int(rest)
            if count == -1:
                return None
            return [await self._read_resp() for _ in range(count)]

        raise RedisError(f"Unknown RESP prefix: {prefix!r}")

    async def _execute(self, *parts: str) -> object:
        async with self._lock:
            await self._ensure_conn()
            assert self._writer is not None

            buf = bytearray()
            buf.extend(f"*{len(parts)}".encode("utf-8"))
            buf.extend(self._CRLF)
            for p in parts:
                b = p.encode("utf-8")
                buf.extend(f"${len(b)}".encode("utf-8"))
                buf.extend(self._CRLF)
                buf.extend(b)
                buf.extend(self._CRLF)

            self._writer.write(bytes(buf))
            await self._writer.drain()
            return await self._read_resp()

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        if ex is None:
            await self._execute("SET", key, value)
        else:
            await self._execute("SET", key, value, "EX", str(int(ex)))


def build_redis_client() -> AsyncRedisClient:
    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("Missing required env var: REDIS_URL")
    return AsyncRedisClient(url)

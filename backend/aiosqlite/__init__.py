"""
Minimal aiosqlite-compatible shim.

This environment runs Python 3.14 and the upstream aiosqlite build available
here can deadlock under asyncio. To keep `sqlite+aiosqlite` usable for tests,
we provide a small subset of the aiosqlite API that SQLAlchemy relies on.

Implementation notes:
- All sqlite3 calls run synchronously in the event loop thread.
- Every public async method yields once (`await asyncio.sleep(0)`) so the ASGI
  test transport doesn't deadlock on body-carrying requests (PATCH/POST).
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

# Re-export DBAPI attributes expected by SQLAlchemy's aiosqlite dialect.
DatabaseError = sqlite3.DatabaseError
Error = sqlite3.Error
IntegrityError = sqlite3.IntegrityError
NotSupportedError = sqlite3.NotSupportedError
OperationalError = sqlite3.OperationalError
ProgrammingError = sqlite3.ProgrammingError
sqlite_version = sqlite3.sqlite_version
sqlite_version_info = sqlite3.sqlite_version_info


class Cursor:
    def __init__(self, conn: "Connection") -> None:
        self._conn = conn
        self._cursor: sqlite3.Cursor | None = None
        self._closed = False

        self.arraysize = 1
        self.rowcount = -1
        self.lastrowid = -1
        self.description = None

    async def __aenter__(self) -> "Cursor":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_cursor(self) -> None:
        await asyncio.sleep(0)
        await self._conn._open()
        if self._cursor is None:
            assert self._conn._conn is not None
            self._cursor = self._conn._conn.cursor()

    async def close(self) -> None:
        await asyncio.sleep(0)
        if self._closed:
            return
        self._closed = True
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None

    async def execute(self, operation: Any, parameters: Optional[Sequence[Any]] = None) -> Any:
        await self._ensure_cursor()
        assert self._cursor is not None

        if parameters is None:
            self._cursor.execute(operation)
        else:
            self._cursor.execute(operation, parameters)

        self.description = self._cursor.description
        self.rowcount = self._cursor.rowcount
        self.lastrowid = self._cursor.lastrowid
        return self

    async def executemany(self, operation: Any, parameters: Iterable[Sequence[Any]]) -> Any:
        await self._ensure_cursor()
        assert self._cursor is not None

        self._cursor.executemany(operation, list(parameters))
        self.description = self._cursor.description
        self.rowcount = self._cursor.rowcount
        self.lastrowid = self._cursor.lastrowid
        return self

    async def fetchone(self) -> Any:
        await asyncio.sleep(0)
        await self._ensure_cursor()
        assert self._cursor is not None
        return self._cursor.fetchone()

    async def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        await asyncio.sleep(0)
        await self._ensure_cursor()
        assert self._cursor is not None
        n = self.arraysize if size is None else size
        return self._cursor.fetchmany(n)

    async def fetchall(self) -> list[Any]:
        await asyncio.sleep(0)
        await self._ensure_cursor()
        assert self._cursor is not None
        return self._cursor.fetchall()

    async def setinputsizes(self, sizes: Sequence[Any]) -> None:
        await asyncio.sleep(0)
        return None

    def setoutputsize(self, size: Any, column: Any) -> None:
        return None

    async def callproc(self, procname: str, parameters: Sequence[Any] = ()) -> Any:
        raise NotSupportedError("callproc is not supported for sqlite")

    async def nextset(self) -> Optional[bool]:
        await asyncio.sleep(0)
        return None

    def __aiter__(self):
        raise NotSupportedError("server-side cursors are not supported for sqlite")


class Connection:
    # SQLAlchemy sets this attribute on the object returned by connect().
    daemon: bool = False

    def __init__(self, connector) -> None:
        self._connector = connector
        self._conn: sqlite3.Connection | None = None

    def __await__(self):
        return self._open().__await__()

    async def __aenter__(self) -> "Connection":
        return await self._open()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _open(self) -> "Connection":
        await asyncio.sleep(0)
        if self._conn is None:
            self._conn = self._connector()
        return self

    async def cursor(self, *args: Any, **kwargs: Any) -> Cursor:
        await asyncio.sleep(0)
        await self._open()
        return Cursor(self)

    async def create_function(self, *args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(0)
        await self._open()
        assert self._conn is not None
        self._conn.create_function(*args, **kwargs)

    async def commit(self) -> None:
        await asyncio.sleep(0)
        await self._open()
        assert self._conn is not None
        self._conn.commit()

    async def rollback(self) -> None:
        await asyncio.sleep(0)
        await self._open()
        assert self._conn is not None
        self._conn.rollback()

    async def close(self) -> None:
        await asyncio.sleep(0)
        if self._conn is None:
            return
        self._conn.close()
        self._conn = None

    def __getattr__(self, key: str) -> Any:
        if self._conn is None:
            raise AttributeError(key)
        return getattr(self._conn, key)


def connect(
    database: str | Path,
    *,
    iter_chunk_size: int = 64,  # kept for compatibility, unused
    loop: Any | None = None,  # kept for compatibility, unused
    **kwargs: Any,
) -> Connection:
    if isinstance(database, str):
        loc = database
    else:
        loc = str(database)

    def _connector() -> sqlite3.Connection:
        return sqlite3.connect(loc, **kwargs)

    return Connection(_connector)


__all__ = [
    "connect",
    "Connection",
    "Cursor",
    "DatabaseError",
    "Error",
    "IntegrityError",
    "NotSupportedError",
    "OperationalError",
    "ProgrammingError",
    "sqlite_version",
    "sqlite_version_info",
]


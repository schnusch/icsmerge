"""
icsmerge
Copyright (C) 2023  schnusch

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import asyncio
import logging
import os
import stat
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncIterator, BinaryIO, Optional, Tuple

import aiohttp
from icalendar import Calendar  # type: ignore

CHUNK_SIZE = 16 * 1024

logger = logging.getLogger(__name__)


def add_exec_bit(mode: int) -> int:
    assert stat.S_IRUSR == stat.S_IXUSR << 2
    assert stat.S_IRGRP == stat.S_IXGRP << 2
    assert stat.S_IROTH == stat.S_IXOTH << 2
    return mode | ((mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)) >> 2)


class FileTooLargeError(Exception):
    pass


def is_valid_ics(ical: bytes) -> bool:
    try:
        Calendar.from_ical(ical)
        return True
    except Exception:
        return False


@asynccontextmanager
async def _write_ics_to_disk(
    dest: str,
    resp: aiohttp.ClientResponse,
    maxsize: int,
    filemode: int,
    dirmode: int,
) -> AsyncIterator[Tuple[str, int]]:
    tmp = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(dest),
        prefix=".tmp.",
    )
    try:
        data = b""
        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
            data += chunk
            if maxsize > 0 and len(data) >= maxsize:
                raise FileTooLargeError
            tmp.write(chunk)

        tmp.seek(0)
        is_valid_ics(tmp.read())

        tmp.flush()
        os.chmod(tmp.fileno(), filemode)
        tmp.seek(0)

        yield (tmp.name, tmp.fileno())
    finally:
        # if everything is successful it will have been moved
        try:
            tmp.close()
        except FileNotFoundError:
            pass


async def download_ics(
    url: str,
    directory: str,
    *,
    filename: str = "calendar.ics",
    maxsize: int = 0,
    mode: int = stat.S_IRUSR | stat.S_IWUSR,
    dirmode: Optional[int] = None,
    client: Optional[aiohttp.ClientSession] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> BinaryIO:
    if client is None:
        async with aiohttp.ClientSession() as client:
            return await download_ics(
                url,
                directory,
                filename=filename,
                maxsize=maxsize,
                mode=mode,
                dirmode=dirmode,
                client=client,
                loop=loop,
            )

    if dirmode is None:
        dirmode = add_exec_bit(mode)
    if loop is None:
        loop = asyncio.get_running_loop()
    dest = os.path.join(directory, filename)
    async with client.get(url) as resp:
        fd = -1
        try:
            resp.raise_for_status()
            os.makedirs(directory, mode=dirmode, exist_ok=True)
            async with _write_ics_to_disk(
                dest,
                resp,
                maxsize=maxsize,
                filemode=mode,
                dirmode=dirmode,
            ) as (name, tmpfd):
                os.replace(name, dest)
                fd = os.dup(tmpfd)
        except BaseException:
            logger.exception(
                "failed to download %s, trying local file %r...",
                url,
                dest,
            )
        try:
            return open(dest if fd < 0 else fd, "rb")
        except BaseException:
            if fd >= 0:
                os.close(fd)
            raise


if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser()
    p.add_argument("-o", "--output-directory", required=True)
    p.add_argument("url")
    args = p.parse_args()
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-8s %(name)s %(message)s",
        level=logging.INFO,
        stream=sys.stderr,
    )
    with asyncio.run(download_ics(args.url, args.output_directory)) as fp, open(
        sys.stdout.fileno(), "wb", closefd=False
    ) as stdout:
        while True:
            buf = fp.read(CHUNK_SIZE)
            if not buf:
                break
            stdout.write(buf)

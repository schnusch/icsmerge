"""
icsmerge
Copyright (C) 2026  schnusch

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

import io
import logging
from typing import Optional  # noqa: F401
from typing import Any, Dict
from urllib.parse import quote, urljoin, urlparse, urlunparse

import aiohttp
from icalendar import Calendar, vBinary  # type: ignore[import-untyped]

from ..config.util import ConfigPath, str_option_path
from ..download import FileTooLargeError
from ..ics import as_str, iter_property_items
from . import CalendarProcessor

logger = logging.getLogger(__name__)


class Processor(CalendarProcessor):
    webdav: str
    username: str
    password: str
    remove_prefix: str
    maxsize: int

    def __init__(self, args: Dict[str, Any], path: ConfigPath):
        if "webdav" not in args or not isinstance(args["webdav"], str):
            raise ValueError(
                "option %s: must be a string" % str_option_path(*path, "webdav")
            )
        if "username" not in args or not isinstance(args["username"], str):
            raise ValueError(
                "option %s: must be a string" % str_option_path(*path, "username")
            )
        if "password" in args and not isinstance(args["password"], str):
            raise ValueError(
                "option %s: must be a string" % str_option_path(*path, "password")
            )
        if "remove_prefix" in args and not isinstance(args["remove_prefix"], str):
            raise ValueError(
                "option %s: must be a string" % str_option_path(*path, "remove_prefix")
            )
        if "maxsize" in args and not isinstance(args["maxsize"], int):
            raise ValueError(
                "option %s: must be an integer" % str_option_path(*path, "maxsize")
            )
        webdav = urlparse(args["webdav"])
        if webdav.scheme not in ("http", "https"):
            raise ValueError(
                "option %s: must be a http:// or https:// URL"
                % str_option_path(*path, "webdav")
            )
        self.webdav = urlunparse(
            (
                webdav.scheme,
                webdav.netloc.rsplit("@", 1)[-1],  # remove auth from URL
                webdav.path.rstrip("/") + "/",  # end with / for urljoin later
                "",  # parameters
                "",  # query
                "",  # fragment
            )
        )
        self.username = args["username"]
        self.password = args.get("password", "")
        self.remove_prefix = args.get("remove_prefix", "")
        self.maxsize = args.get("maxsize", -1)

    async def run(self, cal: Calendar) -> None:
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password),
        ) as session:
            for event in cal.walk("vevent"):
                if "image" in event:
                    continue

                for comp, name, value in iter_property_items(event, recursive=False):
                    if name.upper() != "ATTACH" or "filename" not in value.params:
                        continue

                    # check if filename matches
                    filename = as_str(value.params["filename"])
                    if not filename.startswith(self.remove_prefix):
                        continue
                    filename = filename[len(self.remove_prefix) :]

                    # get MIME type and skip if not an image/*
                    try:
                        fmttype = as_str(value.params["fmttype"])  # type: Optional[str]
                    except KeyError:
                        fmttype = None
                    else:
                        if not fmttype.startswith("image/"):
                            continue

                    url = urljoin(
                        self.webdav,
                        quote(filename.lstrip("/"), safe="/"),
                    )
                    try:
                        # download the attachment
                        out = io.BytesIO()
                        async with session.get(url) as resp:
                            resp.raise_for_status()
                            if fmttype is None:
                                fmttype = resp.content_type.split(";", 1)[0]
                                if not fmttype.startswith("image/"):
                                    logger.debug(
                                        "skipping %s due to its Content-Type: %s",
                                        url,
                                        resp.content_type,
                                    )
                                    continue
                            size = 0
                            async for chunk in resp.content.iter_any():
                                size += len(chunk)
                                if self.maxsize >= 0 and size > self.maxsize:
                                    raise FileTooLargeError(
                                        "file is larger than %d bytes" % self.maxsize
                                    )
                                out.write(chunk)
                        # add IMAGE:
                        value = vBinary(out.getvalue())
                        value.params["fmttype"] = fmttype
                        event["image"] = value
                        logger.debug("added image %s", url)
                    except Exception:
                        logger.exception("cannot download %s", url)
                    else:
                        break

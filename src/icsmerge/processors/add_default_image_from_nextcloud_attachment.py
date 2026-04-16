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

import logging
from typing import Optional  # noqa: F401
from typing import Any, Dict
from urllib.parse import quote, urljoin

from icalendar import Calendar, vText  # type: ignore[import-untyped]

from ..config.util import ConfigPath, str_option_path
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
        if "remove_prefix" in args and not isinstance(args["remove_prefix"], str):
            raise ValueError(
                "option %s: must be a string" % str_option_path(*path, "remove_prefix")
            )
        self.webdav = args["webdav"].rstrip("/") + "/"
        self.remove_prefix = args.get("remove_prefix", "")

    async def run(self, cal: Calendar) -> None:
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
                # add IMAGE:
                value = vText(url)
                value.params["VALUE"] = "URI"
                event["image"] = value
                logger.debug("added image %s", url)

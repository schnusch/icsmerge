"""
icsmerge
Copyright (C) 2023-2024  schnusch

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

import importlib
from typing import Any, Dict, Type  # noqa: F401

from icalendar import Calendar  # type: ignore

from ..config.util import ConfigPath


class CalendarProcessor:
    def __init__(self, args: Any, path: ConfigPath):
        raise NotImplementedError

    async def run(self, calendar: Calendar) -> None:
        raise NotImplementedError


all_processors = dict(
    (name, importlib.import_module("." + name, __name__).Processor)
    for name in [
        "add_default_property",
        "add_default_timezone",
        "filter_out",
        "mod_uid",
        "strip_emoji",
    ]
)  # type: Dict[str, Type[CalendarProcessor]]

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

from typing import Final  # noqa: F401
from typing import List  # noqa: F401
from typing import Any, Dict

from icalendar import Calendar  # type: ignore

from ..config.util import ConfigPath, str_option_path
from . import CalendarProcessor


class Processor(CalendarProcessor):
    def __init__(self, args: Dict[str, Any], path: ConfigPath):
        self.properties = {}  # type: Final[Dict[str, str]]
        errors = []  # type: List[str]
        for prop in ("url", "location"):
            if prop in args:
                if isinstance(args[prop], str):
                    self.properties[prop] = args[prop]
                else:
                    errors.append(
                        "option %s: must be a string" % str_option_path(*path, prop)
                    )
        if not self.properties and not errors:
            errors.append("option %s: no properties given" % str_option_path(*path))
        if errors:
            raise ValueError("\n".join(errors))

    async def run(self, cal: Calendar) -> None:
        for event in cal.walk("vevent"):
            for prop, value in self.properties.items():
                if prop not in event:
                    event.add(prop, value)

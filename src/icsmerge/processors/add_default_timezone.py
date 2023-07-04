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

from datetime import datetime, timezone
from typing import Any, Dict, Final, Optional  # noqa: F401

from icalendar import Calendar, Timezone  # type: ignore

from ..config.util import ConfigPath, str_option_path
from ..ics import as_str, iter_property_items
from . import CalendarProcessor


class Processor(CalendarProcessor):
    def __init__(self, args: Dict[str, Any], path: ConfigPath):
        if "utc" in args:
            if not isinstance(args["utc"], bool) or not args["utc"]:
                raise ValueError(
                    "option %s: must be true" % str_option_path(*path, "utc")
                )
            default_tz = None
            default_tzid = None
        elif "vtimezone" in args:
            if not isinstance(args["vtimezone"], str):
                raise ValueError(
                    "option %s: must be a string" % str_option_path(*path, "vtimezone")
                )
            default_tz = Timezone.from_ical(args["vtimezone"])
            default_tzid = as_str(default_tz.decoded("tzid"))
        else:
            raise ValueError(
                "missing option %s or %s"
                % (str_option_path(*path, "utc"), str_option_path(*path, "vtimezone"))
            )
        self.default_tz = default_tz  # type: Final[Optional[Timezone]]
        self.default_tzid = default_tzid  # type: Final[Optional[str]]

    async def run(self, cal: Calendar) -> None:
        add_tz = False

        for event in cal.walk("vevent"):
            for comp, name, value in iter_property_items(event):
                dt = comp._decode(name, value)
                if (
                    # TODO also handle TIME
                    isinstance(dt, datetime)
                    and dt.tzinfo is None
                    and "tzid" not in value.params
                ):
                    if self.default_tz is None:
                        comp[name] = comp._encode(name, dt.replace(tzinfo=timezone.utc))
                    else:
                        value.params["tzid"] = self.default_tzid
                        add_tz = True

        if add_tz:
            for tz in cal.walk("vtimezone"):
                if as_str(tz.decoded("tzid")) == self.default_tzid:
                    # timezone was already defined
                    add_tz = False
                    break

        if add_tz:
            cal.add_component(self.default_tz)

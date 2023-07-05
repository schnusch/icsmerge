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

import re
from typing import List  # noqa: F401
from typing import Any, Dict, Literal, TypedDict, cast

from icalendar import Calendar  # type: ignore

from ..config.util import ConfigPath, str_option_path
from ..ics import as_str
from . import CalendarProcessor

ConditionalProperty = Literal["summary"]


class Condition(TypedDict, total=False):
    match: re.Pattern


class Processor(CalendarProcessor):
    def __init__(self, args: Dict[str, Any], path: ConfigPath):
        self.conditions = {}  # type: Dict[ConditionalProperty, Condition]
        errors = []  # type: List[str]

        for prop, subargs in args.items():
            if prop in ("summary",):
                if isinstance(subargs, dict):
                    for op, cond in subargs.items():
                        if op == "match":
                            if isinstance(cond, str):
                                try:
                                    pat = re.compile(cond)
                                except re.error as e:
                                    errors.append(
                                        "option %s: is not a valid regular expression: %s"
                                        % (str_option_path(*path, prop, op), e)
                                    )
                                else:
                                    self.conditions.setdefault(
                                        cast(ConditionalProperty, prop),
                                        {},
                                    )["match"] = pat
                            else:
                                errors.append(
                                    "option %s: must be a string"
                                    % str_option_path(*path, prop, op)
                                )
                else:
                    errors.append(
                        "option %s: must be a table" % str_option_path(*path, prop)
                    )
            else:
                errors.append("unknown option %s" % str_option_path(*path, prop))

        empty = True
        if errors or self.conditions:
            empty = False
        else:
            for condition in self.conditions.values():
                if condition:
                    empty = False
                    break
        if empty:
            errors.append("option %s: no conditions given" % str_option_path(*path))

        if errors:
            raise ValueError("\n".join(errors))

    async def run(self, cal: Calendar) -> None:
        remove = []  # type: List[int]
        for i, event in enumerate(cal.subcomponents):
            if event.name == "VEVENT":
                for prop, conditions in self.conditions.items():
                    try:
                        value = event.decoded(prop)
                    except KeyError:
                        continue
                    if "match" in conditions and conditions["match"].fullmatch(
                        as_str(value)
                    ):
                        remove.append(i)
        for i in reversed(remove):
            cal.subcomponents.pop(i)

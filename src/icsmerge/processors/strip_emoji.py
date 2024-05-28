"""
icsmerge
Copyright (C) 2024  schnusch

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

import emoji
from icalendar import Calendar  # type: ignore

from ..config.util import ConfigPath, str_option_path
from ..ics import as_str
from . import CalendarProcessor


class EmojiStripper(object):
    def __init__(self, text: str):
        self.found = []  # type: List[int]
        self.i = 0
        self.old_text = text
        self.new_text = emoji.replace_emoji(self.old_text, self.repl)
        # self.new_text is self.old_text with emojis replaces by a space
        # self.found is the positions of the emojis
        for j in reversed(self.found):
            # leading space
            i = j
            while i > 0 and self.old_text[i - 1].isspace():
                i -= 1
            # trailing space
            k = j + 1
            while k < len(self.old_text) and self.old_text[k].isspace():
                k += 1
            # self.old_text[i:k] is the emoji with surrounding whitespace
            # self.old_text[j] is the emoji
            span = self.old_text[i:k]
            if k - i == 1:
                space = ""
            elif "\n" in span or "\r" in span:
                space = "\n"
            elif "\t" in span:
                space = "\t"
            else:
                space = " "
            self.new_text = self.new_text[:i] + space + self.new_text[k:]

    def repl(self, e: str, data: Dict[str, str]) -> str:
        self.i = self.old_text.find(e, self.i)
        self.found.append(self.i)
        self.i += 1
        return " "


def strip_emoji(text: str) -> str:
    return EmojiStripper(text).new_text


class Processor(CalendarProcessor):
    def __init__(self, args: Dict[str, Any], path: ConfigPath):
        self.properties = []  # type: Final[List[str]]
        if "properties" not in args:
            pass
        elif not isinstance(args["properties"], list):
            raise ValueError(
                "option %s: expected a list of property names"
                % str_option_path(*path, "properties")
            )
        else:
            errors = []  # type: List[str]
            for i, prop in enumerate(args["properties"]):
                if isinstance(prop, str):
                    self.properties.append(prop)
                else:
                    errors.append(
                        "option %s: expected a string"
                        % str_option_path(*path, "properties", i)
                    )
            if errors:
                raise ValueError("\n".join(errors))
        if not self.properties:
            raise ValueError(
                "option %s: no properties given" % str_option_path(*path, "properties")
            )

    async def run(self, cal: Calendar) -> None:
        for event in cal.walk("vevent"):
            for prop in self.properties:
                try:
                    old_value = as_str(event.decoded(prop))
                except KeyError:
                    continue
                new_value = strip_emoji(old_value)
                if new_value != old_value:
                    del event[prop]
                    event.add(prop, new_value)

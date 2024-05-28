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

import unittest
from typing import ClassVar, Tuple

from icalendar import Calendar, Event  # type: ignore

from icsmerge.ics import as_str
from icsmerge.processors.strip_emoji import Processor


def create_calendar(summary: str) -> Tuple[Calendar, Event]:
    cal = Calendar()
    ev = Event()
    ev.add("summary", summary)
    cal.add_component(ev)
    return (cal, ev)


class EmojiTest(unittest.IsolatedAsyncioTestCase):
    proc: ClassVar[Processor]

    @classmethod
    def setUpClass(cls) -> None:
        cls.proc = Processor({"properties": ["summary"]}, ())

    async def test_emoji_start_no_space(self) -> None:
        cal, ev = create_calendar("\U0001F43B" "lorem  ipsum")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

    async def test_emoji_start_one_space(self) -> None:
        cal, ev = create_calendar("\U0001F43B lorem  ipsum")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

    async def test_emoji_start_many_space(self) -> None:
        cal, ev = create_calendar("\U0001F43B  lorem  ipsum")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

    async def test_emoji_mid_no_space(self) -> None:
        cal, ev = create_calendar("lorem" "\U0001F43B" "ipsum")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "loremipsum")

    async def test_emoji_mid_space(self) -> None:
        cal, ev = create_calendar("lorem \U0001F43B  ipsum")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem ipsum")

    async def test_emoji_end_no_space(self) -> None:
        cal, ev = create_calendar("lorem  ipsum" "\U0001F43B")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

    async def test_emoji_end_one_space(self) -> None:
        cal, ev = create_calendar("lorem  ipsum \U0001F43B")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

    async def test_emoji_end_many_space(self) -> None:
        cal, ev = create_calendar("lorem  ipsum  \U0001F43B")
        await self.proc.run(cal)
        self.assertEqual(as_str(ev.decoded("summary")), "lorem  ipsum")

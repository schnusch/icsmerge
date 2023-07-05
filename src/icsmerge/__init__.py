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

import argparse
import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from icalendar import Calendar  # type: ignore

from .config import CalendarSource, Config, load_config
from .download import download_ics
from .ics import PRODID, as_str, list_of_dict_events, merge

logger = logging.getLogger(__name__)


async def load_calendar(
    calsrc: CalendarSource,
    directory: str,
    maxsize: int,
) -> Calendar:
    try:
        with await download_ics(calsrc.url, directory, maxsize=maxsize) as fp:
            ics = fp.read()
    except FileNotFoundError:
        ics = b"\r\n".join(
            [
                b"BEGIN:VCALENDAR",
                b"PRODID:" + as_str(PRODID).encode("utf-8", "surrogateescape"),
                b"VERSION:2.0",
                b"END:VCALENDAR",
            ]
        )
    try:
        cal = Calendar.from_ical(ics)
    except ValueError:
        raise ValueError("cannot parse %s" % directory)
    for processor in calsrc.processors:
        await processor.run(cal)
    return cal


def write_ics(destdir: str, cal: Calendar) -> None:
    os.makedirs(destdir, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(dir=destdir, prefix=".tmp.", suffix=".ics")
    try:
        tmp.write(cal.to_ical())
        tmp.flush()
        os.replace(tmp.name, os.path.join(destdir, "calendar.ics"))
    finally:
        # if everything is successful it will have been moved
        try:
            tmp.close()
        except FileNotFoundError:
            pass


def write_json(
    destdir: str,
    cal: Calendar,
    after: datetime,
    before: datetime,
) -> None:
    os.makedirs(destdir, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destdir,
        prefix=".tmp.",
        suffix=".json",
    )
    try:
        events = list_of_dict_events(
            cal,
            after=after,
            before=before,
        )
        json.dump(events, tmp, ensure_ascii=False, indent=2, separators=(",", ": "))
        tmp.write("\n")
        tmp.flush()
        os.replace(tmp.name, os.path.join(destdir, "calendar.json"))
    finally:
        # if everything is successful it will have been moved
        try:
            tmp.close()
        except FileNotFoundError:
            pass


async def run(config: Config) -> None:
    assert config.calendars, "no calendar sources specified"
    calsrcs = list(config.calendars.items())
    logger.debug("downloading %d calendars...", len(calsrcs))
    cals = await asyncio.gather(
        *(
            load_calendar(
                calsrc,
                os.path.join(config.workdir, name),
                maxsize=config.maxsize,
            )
            for name, calsrc in calsrcs
        )
    )
    logger.debug("merging %d calendars...", len(calsrcs))
    now = datetime.now(timezone.utc) - timedelta(hours=12)
    merged = merge(cals, now=now)
    write_ics(config.destdir, merged)
    write_json(
        config.destdir,
        merged,
        after=now,
        before=now + timedelta(weeks=4, days=1),
    )


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description="TODO")
    p.add_argument("-c", "--config", required=True, help="configuration file")
    args = p.parse_args(argv)

    config = load_config(args.config)
    asyncio.run(run(config))

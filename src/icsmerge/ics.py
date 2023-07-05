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

import itertools
from collections.abc import Iterable
from datetime import date, datetime, time, timezone
from typing import Any, Dict, Iterator, List, NewType, Optional, Set, Tuple, Union

from dateutil.rrule import rrulestr  # type: ignore
from icalendar import Calendar, Event, Timezone  # type: ignore
from icalendar.cal import Component  # type: ignore

PRODID = "-//icsmerge"


def as_str(x: Union[bytes, str]) -> str:
    if isinstance(x, bytes):
        return x.decode("utf-8", "surrogateescape")
    else:
        assert isinstance(x, str)
        return x


def iter_property_items(
    component: Component,
    recursive: bool = True,
) -> Iterator[Tuple[Component, str, Any]]:
    for key in component.keys():
        yield (component, key, component[key])
    if recursive:
        for subcomponent in component.subcomponents:
            yield from iter_property_items(subcomponent)


def get_dtend(event: Event) -> Union[date, datetime, time]:
    try:
        dtend = event.decoded("dtend")
        if isinstance(dtend, list) and dtend:
            dtend = dtend[0]
    except KeyError:
        dtstart = event.decoded("dtstart")
        if isinstance(dtstart, list) and dtstart:
            dtstart = dtstart[0]
        duration = event.decoded("duration")
        if isinstance(duration, list) and duration:
            duration = duration[0]
        dtend = dtstart + duration
    if not isinstance(dtend, (date, datetime, time)):
        raise TypeError
    return dtend


def _with_dtstart(event: Event) -> Tuple[Union[None, datetime], Event]:
    dtstart = None
    try:
        dtstart = event.decoded("dtstart")
    except KeyError:
        pass
    else:
        if isinstance(dtstart, list) and dtstart:
            dtstart = dtstart[0]
        if isinstance(dtstart, date):
            dtstart = datetime.combine(dtstart, time.min)
        else:
            assert isinstance(dtstart, datetime)
    return (dtstart, event)


def event_has_passed(
    event: Event,
    now: Optional[datetime] = None,
) -> bool:
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        dtend = get_dtend(event)
    except (KeyError, TypeError):
        # keep malformed events
        return False
    if isinstance(dtend, time) or dtend >= (
        now if isinstance(dtend, datetime) else now.date()
    ):
        return False

    try:
        dtstart = event.decoded("dtstart")
    except KeyError:
        # keep malformed events
        return False
    if not isinstance(dtstart, (date, datetime)):
        # we don't know how to proceed with time events, so keep them
        return False

    try:
        recur = event["rrule"]
    except KeyError:
        return True
    # rrule converts dtstart to datetime, so we don't have to handle dates like above
    rrule = rrulestr(as_str(recur.to_ical()), dtstart=dtstart)
    duration = dtend - dtstart
    if rrule.after(now - duration, inc=True) is not None:
        return False

    return True


def sorted_events(
    events: Iterable[Event],
    *,
    now: Optional[datetime] = None,
) -> List[Event]:
    if now is None:
        now = datetime.now(timezone.utc)
    events_with_dtstart = (
        (
            # so we never compare localized and non-localized datetime
            dtstart.tzinfo is not None,
            dtstart,
            # so we never compare icalendar.Event
            i,
            event,
        )
        for i, (dtstart, event) in enumerate(map(_with_dtstart, events))
        if dtstart is not None and not event_has_passed(event, now)
    )
    return [ev for _, _, _, ev in sorted(events_with_dtstart)]


TZID = NewType("TZID", str)


def timezones_by_tzid(timezones: Iterable[Timezone]) -> Dict[TZID, Timezone]:
    by_tzid = {}  # type: Dict[TZID, Timezone]
    for tz in timezones:
        try:
            tzid = tz.decoded("tzid")
        except KeyError:
            continue
        if isinstance(tzid, list):
            if not tzid:
                continue
            tzid = tzid[0]
        saved_tz = by_tzid.setdefault(TZID(as_str(tzid)), tz)
        if saved_tz is not tz:
            pass  # TODO see if the same
    return by_tzid


def get_used_tzids(event: Event) -> Set[TZID]:
    tzids = set()
    for _, prop, value in iter_property_items(event):
        for value in value if isinstance(value, list) else [value]:
            try:
                tzid = value.params["tzid"]
            except KeyError:
                continue
            tzids.add(TZID(as_str(tzid)))
    return tzids


def merge(
    calendars: Iterable[Calendar],
    *,
    prodid: Union[bytes, str] = PRODID,
    now: Optional[datetime] = None,
) -> Calendar:
    if now is None:
        now = datetime.now(timezone.utc)
    events = sorted_events(
        itertools.chain.from_iterable(cal.walk("vevent") for cal in calendars),
        now=now,
    )

    timezones = timezones_by_tzid(
        itertools.chain.from_iterable(cal.walk("vtimezone") for cal in calendars)
    )
    tzids = set()
    for event in events:
        tzids |= get_used_tzids(event)

    merged = Calendar()
    merged.add("prodid", prodid)
    merged.add("version", "2.0")
    for tzid in sorted(tzids):
        if tzid not in timezones:
            raise NotImplementedError("missing timezone %r" % tzid)
        merged.add_component(timezones[tzid])
    for event in events:
        merged.add_component(event)

    return merged


if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Merge iCalendar files")
    p.add_argument("file", nargs="+")
    args = p.parse_args()

    cals = []  # type: List[Calendar]
    for name in args.file:
        with open(name, "rb") as fp:
            ical = fp.read()
            try:
                cal = Calendar.from_ical(ical)
            except ValueError:
                raise ValueError("cannot parse %r" % name)
            cals.append(cal)
    merged = merge(cals)
    with open(sys.stdout.fileno(), "wb", closefd=False) as stdout:
        stdout.write(merged.to_ical())

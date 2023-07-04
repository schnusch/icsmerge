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

import os.path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

try:
    import tomllib  # type: ignore
except ImportError:
    import tomli as tomllib  # type: ignore

from ..processors import CalendarProcessor, all_processors
from .util import ConfigPath, parse_size, str_option_path


@dataclass
class CalendarSource:
    url: str
    processors: List[CalendarProcessor] = field(default_factory=list)


@dataclass
class Config:
    destdir: str
    workdir: str
    maxsize: int
    calendars: Dict[str, CalendarSource]


class ConfigError(Exception):
    pass


def _is_abspath(x: Any) -> bool:
    return isinstance(x, str) and os.path.isabs(x)


def _init_processor(
    errors: List[str],
    processor: Any,
    path: ConfigPath,
) -> Optional[CalendarProcessor]:
    name = None  # type: Optional[str]
    args = {}  # type: Dict[str, Any]

    if isinstance(processor, str):
        name = processor
    elif isinstance(processor, dict):
        if "name" not in processor:
            errors.append("missing option %s" % str_option_path(*path, "name"))
        elif not isinstance(processor["name"], str):
            errors.append(
                "option %s: must be a string" % str_option_path(*path, "name")
            )
        else:
            name = processor["name"]

        if "args" in processor:
            if isinstance(processor["args"], dict):
                args = processor["args"]
            else:
                errors.append(
                    "option %s: must be a table" % str_option_path(*path, "args")
                )
    else:
        errors.append("option %s: must be a string or a table" % str_option_path(*path))

    if name is not None:
        proc = all_processors.get(name)
        if proc is None:
            errors.append(
                "option %s: unknown processor %r" % (str_option_path(*path), name)
            )
        else:
            try:
                return proc(args, (*path, "args"))
            except ValueError as e:
                errors.append(str(e))

    return None


def _get_calendar_source(
    errors: List[str],
    x: Any,
    path: ConfigPath,
) -> Optional[CalendarSource]:
    url = None  # type: Optional[str]
    processors = []  # type: List
    if not isinstance(x, dict):
        errors.append("%s must be a table" % str_option_path(*path))
    else:
        if "url" not in x:
            errors.append("missing option %s" % str_option_path(*path, "url"))
        elif not isinstance(x["url"], str):
            errors.append("option %s: must be a string" % str_option_path(*path, "url"))
        else:
            url = x["url"]

        if "processors" in x:
            if isinstance(x["processors"], list):
                for i, processor in enumerate(x["processors"]):
                    proc = _init_processor(
                        errors,
                        processor,
                        (*path, "processors", i),
                    )
                    if proc is not None:
                        processors.append(proc)
            else:
                errors.append(
                    "option %s: must be a list of processors to apply"
                    % str_option_path(*path, "processors")
                )

    if url is None:
        return None
    else:
        return CalendarSource(url=url, processors=processors)


def load_config(name: Union[bytes, str]) -> Config:
    with open(name, "rb") as fp:
        config = tomllib.load(fp)

    errors = []  # type: List[str]
    calendars = {}  # type: Dict[str, CalendarSource]
    maxsize = 16 * 1024 * 1024

    for option in ("destdir", "workdir"):
        if option not in config:
            errors.append("missing option %r" % option)
        elif not _is_abspath(config[option]):
            errors.append("option %r: must be an absolute path" % option)

    if "maxsize" in config:
        try:
            maxsize = parse_size(config["maxsize"])
        except ValueError as e:
            errors.append("option %r: %s" % ("maxsize", e))

    if "calendars" not in config:
        errors.append("missing option %r" % "calendars")
    elif not isinstance(config["calendars"], dict):
        errors.append("option %r: must be a table" % "calendars")
    else:
        for key, value in config["calendars"].items():
            if os.path.isabs(key):
                errors.append(
                    "the option named %r.%r must not be an absolute path"
                    % ("calendars", key)
                )
            calsrc = _get_calendar_source(errors, value, ("calendars", key))
            if calsrc is not None:
                calendars[key] = calsrc

    if errors:
        errors.insert(0, "The config file %r contains following error(s):" % name)
        raise ConfigError("\n".join(errors))

    return Config(
        destdir=config["destdir"],
        workdir=config["workdir"],
        maxsize=maxsize,
        calendars=calendars,
    )

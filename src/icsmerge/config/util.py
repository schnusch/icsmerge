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

from typing import Any, Tuple, Union

ConfigPath = Tuple[Union[int, str], ...]


def parse_size(x: Any) -> int:
    if isinstance(x, int):
        return x
    elif isinstance(x, str) and x:
        suffixes = [
            ("K", 10, 3),
            ("Ki", 1024, 1),
            ("M", 10, 6),
            ("Mi", 1024, 2),
            ("G", 10, 9),
            ("Gi", 1024, 3),
            ("T", 10, 12),
            ("Ti", 1024, 4),
            ("P", 10, 15),
            ("Pi", 1024, 5),
        ]
        for suffix, base, exp in suffixes:
            for suffix in (suffix, suffix + "B"):
                if x.endswith(suffix):
                    return int(x[: -len(suffix)], 10) * base**exp
        try:
            return int(x, 10)
        except ValueError:
            raise ValueError(
                "integer with optionally one of these suffixes %s expected"
                % ", ".join(
                    "%s (%d^%d)" % (suffix, base, exp)
                    for suffix, base, exp in suffixes[:-1]
                )
            ) from None
    else:
        raise ValueError("must be string or integer")


def str_option_path(*path: Union[int, str]) -> str:
    return ".".join(repr(x) for x in path)

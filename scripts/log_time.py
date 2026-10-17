#!/usr/bin/env python3
"""log_time.py: the execution log's timestamp rule (Wire 4.4.3).

`specs/utils/execution_log.md`: every Timestamp is written in UTC with a `Z`
suffix, `YYYY-MM-DD HH:MMZ` (for example `2026-10-17 14:05Z`). Rows written
before 4.4.3 have no suffix. They stay valid and are read as "zone unknown":
they were written in whatever zone the writer's clock used, and nothing here
guesses which.

Ordering (rule 6, status-sync Step 4f) compares two rows:

- both UTC, or both zone unknown: on the values written;
- one UTC and one zone unknown: the unknown row could be in any zone from
  UTC-12 to UTC+14, so the pair is out of order only when no zone in that
  range puts it in order, in order only when every zone does, and
  `zone_unknown` otherwise (not a defect; reported for information).

Stdlib only. Imported by `ticket_delivery.py` and the tests; also runnable:

    python3 log_time.py now          print the current time in the log form
    python3 log_time.py check <log>  ordering report for an execution_log.md
"""

import datetime as _dt
import json
import re
import sys
from pathlib import Path

UTC_FORMAT = "%Y-%m-%d %H:%MZ"
PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})(Z?)$")
# How far a clock with no zone can be from UTC: UTC+14 (ahead) to UTC-12.
AHEAD = _dt.timedelta(hours=14)
BEHIND = _dt.timedelta(hours=12)


class Stamp:
    """A parsed log timestamp. `value` is the time as written (naive);
    `utc` is True for the `Z` form and False when the zone is unknown."""

    __slots__ = ("text", "value", "utc")

    def __init__(self, text, value, utc):
        self.text, self.value, self.utc = text, value, utc

    def __repr__(self):
        return f"Stamp({self.text!r})"


def parse(text):
    """A Stamp for `YYYY-MM-DD HH:MMZ` or `YYYY-MM-DD HH:MM`, else None."""
    m = PATTERN.match(str(text or "").strip())
    if not m:
        return None
    try:
        value = _dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return Stamp(m.group(0), value, bool(m.group(2)))


def format_utc(moment):
    """The log form of a datetime. A naive datetime is taken as UTC."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return moment.strftime(UTC_FORMAT)


def now():
    """The current time in the log form."""
    return format_utc(_dt.datetime.now(_dt.timezone.utc))


def order(previous, current):
    """`in_order`, `out_of_order` or `zone_unknown` for two Stamps, the
    `current` row written below the `previous` one."""
    if previous.utc == current.utc:
        return "in_order" if current.value >= previous.value else "out_of_order"
    if current.utc:
        # The previous row's real UTC time lies in [P - AHEAD, P + BEHIND].
        low, high = previous.value - AHEAD, previous.value + BEHIND
        if current.value >= high:
            return "in_order"
        return "out_of_order" if current.value < low else "zone_unknown"
    # The current row's real UTC time lies in [C - AHEAD, C + BEHIND].
    low, high = current.value - AHEAD, current.value + BEHIND
    if low >= previous.value:
        return "in_order"
    return "out_of_order" if high < previous.value else "zone_unknown"


def not_before(last, new):
    """The Timestamp to write for a row appended below a row stamped `last`:
    `new` (a UTC stamp), or `last` when `last` is in the same form and
    later, so the log never goes backwards. A `last` with no zone below a UTC
    `new` cannot be compared reliably and is never copied: the new row keeps
    `new`, and status-sync Step 4f reports the pair if it is out of order."""
    sl, sn = parse(last), parse(new)
    if sl is not None and sn is not None and sl.utc == sn.utc and sl.value > sn.value:
        return sl.text
    return new


SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")


def table_rows(text):
    """Rows of an execution log in file order: {line, cells, stamp, columns}.
    The header and separator rows are skipped."""
    rows = []
    for line_no, line in enumerate((text or "").splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|") or SEPARATOR.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and cells[0].lower() == "timestamp":
            continue
        rows.append({"line": line_no, "cells": cells, "stamp": parse(cells[0] if cells else ""),
                     "columns": len(cells)})
    return rows


def check(text):
    """Ordering report for a log (status-sync Step 4f)."""
    rows = table_rows(text)
    out_of_order, zone_unknown, unparseable = [], [], []
    previous = None
    for row in rows:
        if row["stamp"] is None:
            unparseable.append(row["line"])
            continue
        if previous is not None:
            pair = {"row": row["line"], "previous_row": previous["line"],
                    "timestamp": row["cells"][0], "previous_timestamp": previous["cells"][0]}
            result = order(previous["stamp"], row["stamp"])
            if result == "out_of_order":
                out_of_order.append(pair)
            elif result == "zone_unknown":
                zone_unknown.append(pair)
        previous = row
    parsed = [r for r in rows if r["stamp"] is not None]
    drift = "log_out_of_order" if (out_of_order or unparseable) else "in_sync"
    return {
        "drift": drift,
        "out_of_order": out_of_order,
        "zone_unknown": zone_unknown,
        "unparseable": unparseable,
        "utc_rows": sum(r["stamp"].utc for r in parsed),
        "zone_unknown_rows": sum(not r["stamp"].utc for r in parsed),
        "legacy_rows": sum(r["columns"] < 6 for r in rows),
        "current_rows": sum(r["columns"] >= 6 for r in rows),
        "repair": None if drift == "in_sync" else "report_both_rows",
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["now"]:
        print(now())
        return 0
    if len(args) == 2 and args[0] == "check":
        print(json.dumps(check(Path(args[1]).read_text(encoding="utf-8")), indent=2))
        return 0
    print("usage: log_time.py now | log_time.py check <execution_log.md>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

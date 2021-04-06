import datetime
import re

# Code below is a modified version of duration calculation of isodate package.
# (https://github.com/gweis/isodate)
# Original copyright notice:
##############################################################################
# Copyright 2009, Gerhard Weis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT
##############################################################################

ISO8601_PERIOD_REGEX = re.compile(
    r"^(?P<sign>[+-])?"
    r"P(?!\b)"
    r"(?P<years>[0-9]+([,.][0-9]+)?Y)?"
    r"(?P<months>[0-9]+([,.][0-9]+)?M)?"
    r"(?P<weeks>[0-9]+([,.][0-9]+)?W)?"
    r"(?P<days>[0-9]+([,.][0-9]+)?D)?"
    r"((?P<separator>T)(?P<hours>[0-9]+([,.][0-9]+)?H)?"
    r"(?P<minutes>[0-9]+([,.][0-9]+)?M)?"
    r"(?P<seconds>[0-9]+([,.][0-9]+)?S)?)?$"
)
# regular expression to parse ISO duartion strings.


def parse_duration(datestring):
    """
    Parses an ISO 8601 durations into datetime.datetime.timedelta.
    The implementation handles a year's duration as 365 days and a
    month's duration as 30 days.

    The following duration formats are supported:
      -PnnW                  duration in weeks
      -PnnYnnMnnDTnnHnnMnnS  complete duration specification

    The '-' is optional.

    Limitations:  ISO standard defines some restrictions about where to use
      fractional numbers and which component and format combinations are
      allowed. This parser implementation ignores all those restrictions and
      returns something when it is able to find all necessary components.
      In detail:
        it does not check, whether only the last component has fractions.
        it allows weeks specified with all other combinations
    """
    if not isinstance(datestring, str):
        raise TypeError("Expecting a string %r" % datestring)
    match = ISO8601_PERIOD_REGEX.match(datestring)
    if not match:
        raise ValueError(
            "Expecting ISO8601 duration format, which is not %r" % datestring
        )
    groups = match.groupdict()
    for key, val in groups.items():
        if key not in ("separator", "sign"):
            if val is None:
                groups[key] = "0n"
            groups[key] = float(groups[key][:-1].replace(",", "."))
    ret = datetime.timedelta(
        days=groups["days"] + (groups["years"] * 365) + (groups["months"] * 30),
        hours=groups["hours"],
        minutes=groups["minutes"],
        seconds=groups["seconds"],
        weeks=groups["weeks"],
    )
    if groups["sign"] == "-":
        ret = datetime.timedelta(0) - ret
    return ret

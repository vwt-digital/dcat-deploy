import json
import sys
import datetime
import re

from google.cloud import datastore

json_file = open(sys.argv[1], 'r')
catalog = json.load(json_file)


def gather_bucket_lifecycle(temporal):
    if temporal and temporal.startswith('P'):
        duration = parse_duration(temporal)
        return duration.days
    else:
        return {}


def datastore_auto_delete(dataset):
    temporal_days = gather_bucket_lifecycle(entry['temporal'])
    if temporal_days and temporal_days > 0 and 'distribution' in dataset:
        for distribution in dataset['distribution']:
            if 'datastore-kind' in distribution['format'] \
                    and 'deploymentProperties' in distribution \
                    and 'kind' in distribution['deploymentProperties'] \
                    and 'keyField' in distribution['deploymentProperties']:
                kind = distribution['deploymentProperties']['kind']
                field = distribution['deploymentProperties']['keyField']

                db_client = datastore.Client()
                batch = db_client.batch()
                query = db_client.query(kind=kind)

                time_delta = (datetime.datetime.now() - datetime.timedelta(
                    days=temporal_days)).isoformat()
                query.add_filter(field, "<=", time_delta)
                query.keys_only()
                entities = list(query.fetch())

                if len(entities) > 0:
                    print("Auto-deleting {} entities older than {} days".format(kind, temporal_days))

                    batch.begin()
                    batch_count = 0
                    batch_count_total = 0

                    for entity in entities:
                        if batch_count == 500:
                            batch.commit()
                            batch = db_client.batch()
                            batch.begin()
                            batch_count = 0

                        batch.delete(entity.key)
                        batch_count += 1
                        batch_count_total += 1

                    batch.commit()
                    print("Deleted total of {} {} entities".format(batch_count_total, kind))
                else:
                    print("No deletable {} entities found".format(kind))
    else:
        print("Temporal for {} is invalid".format(dataset['identifier']))


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
    r"(?P<seconds>[0-9]+([,.][0-9]+)?S)?)?$")
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
        raise ValueError("Expecting ISO8601 duration format, which is not %r"
                         % datestring)
    groups = match.groupdict()
    for key, val in groups.items():
        if key not in ('separator', 'sign'):
            if val is None:
                groups[key] = '0n'
            groups[key] = float(groups[key][:-1].replace(',', '.'))
    ret = datetime.timedelta(days=groups["days"] +
                             (groups['years']*365) +
                             (groups['months']*30),
                             hours=groups["hours"],
                             minutes=groups["minutes"],
                             seconds=groups["seconds"],
                             weeks=groups["weeks"])
    if groups["sign"] == '-':
        ret = datetime.timedelta(0) - ret
    return ret


# Entry steps
if 'dataset' in catalog and len(catalog['dataset']) > 0:
    for entry in catalog['dataset']:
        if 'temporal' in entry:
            datastore_auto_delete(entry)
else:
    sys.exit(0)

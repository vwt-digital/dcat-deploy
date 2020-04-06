import sys
import time
import logging

from google.cloud import monitoring_v3

project = sys.argv[1]

client = monitoring_v3.MetricServiceClient()
project_name = client.project_path(project)
interval = monitoring_v3.types.TimeInterval()
now = time.time()
interval.end_time.seconds = int(now)
interval.start_time.seconds = int(now)
aggregation = monitoring_v3.types.Aggregation()
aggregation.alignment_period.seconds = 1200
aggregation.per_series_aligner = (
    monitoring_v3.enums.Aggregation.Aligner.ALIGN_MEAN)

results = client.list_time_series(
    project_name,
    'metric.type = "cloudsql.googleapis.com/database/disk/bytes_used"',
    interval,
    monitoring_v3.enums.ListTimeSeriesRequest.TimeSeriesView.FULL,
    aggregation)

for result in results:
    for point in result.points:
        # Compare with size in bytes of an empty cloudsql database
        size = int(point.value.double_value)
        if size < 1221918195:
            raise Exception('Cloudsql database is empty! The size is {} bytes'.format(size))
        else:
            logging.info(' + Cloudsql database OK! The size is {} bytes'.format(size))

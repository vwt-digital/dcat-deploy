import sys
import time

from google.cloud import monitoring_v3

project = sys.argv[1]
metric = sys.argv[2]

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
    'metric.type = "{}"'.format(metric),
    interval,
    monitoring_v3.enums.ListTimeSeriesRequest.TimeSeriesView.FULL,
    aggregation)

for result in results:
    for point in result.points:
        print(int(point.value.double_value))

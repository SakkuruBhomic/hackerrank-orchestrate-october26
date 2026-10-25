import csv, json
from collections import defaultdict
from datetime import datetime

system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

# Group deletion worker events into sub-batches
# Notice how within each run, events for each user occur in close sequence
worker_acts = [a for a in system_activity if a['source_system'] == 'deletion_worker']

# Let's inspect the timestamps of activities 3525 to 3545
for a in worker_acts:
    num = int(a['activity_id'].split('_')[1])
    if 3528 <= num <= 3546:
        print(f"{a['activity_id']} | {a['event_time']} | {a['target_system']:20} | {a['resource_id']:18} | {a['event_type']:18} | {a['reported_result']}")

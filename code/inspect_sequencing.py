import csv, json
from collections import defaultdict
from datetime import datetime

system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))
worker_acts = [a for a in system_activity if a['source_system'] == 'deletion_worker']

# Each user's deletion workflow begins with an account_service DELETE_RECORD event,
# followed by downstream systems (search, analytics, support, integration, backup, identity)
# Let's inspect the order of events
for i, a in enumerate(worker_acts[100:130]):
    print(f"{a['activity_id']} | {a['event_time']} | {a['target_system']:20} | {a['resource_id']:18} | {a['event_type']} | {a['reported_result']}")

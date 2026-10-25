import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if '2026-09-01' in row['event_time'] and row['source_system'] == 'deletion_worker':
            print(f"{row['event_time']} | {row['target_system']:18} | {row['resource_id']:15} | {row['details']}")

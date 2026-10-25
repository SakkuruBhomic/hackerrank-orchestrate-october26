import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    print("Columns:", reader.fieldnames)
    for row in reader:
        if '2026-09-09' in row['event_time']:
            print(f"{row['activity_id']} {row['event_time']} {row['event_type']:20} {row['source_system']:15} {row['target_system']:18} {row['resource_id']:20} {row['details'][:80]}")

import csv
import json
from pathlib import Path

sample_out = csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))
target_audits = set()
for r in sample_out:
    steps = json.loads(r['steps_json'])
    for s in steps:
        if 'audit_record' in s['resource_id']:
            target_audits.add(s['resource_id'])

print("Searching for", len(target_audits), "audit records across repo...")

locations = {a: [] for a in target_audits}

# Check system_activity.csv
with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        for a in target_audits:
            if a in str(row):
                locations[a].append(f"system_activity: {row['activity_id']} {row['event_time']} {row['event_type']} {row['resource_id']}")

# Check all files in dataset/evidence
for p in Path('dataset/evidence').rglob('*.*'):
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        for a in target_audits:
            if a in txt:
                locations[a].append(f"evidence: {p.name}")
    except:
        pass

for a in sorted(target_audits):
    print(f"{a:22} : {locations[a]}")

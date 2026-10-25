import csv
import json

sample_out = csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))
for r in sample_out:
    cid = r['case_id']
    steps = json.loads(r['steps_json'])
    for s in steps:
        if 'audit_record' in s['resource_id']:
            print(f"{cid:8} | {s['resource_id']:20} | ev: {s['evidence_id']}")

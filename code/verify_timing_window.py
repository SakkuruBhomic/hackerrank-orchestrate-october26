import csv, json
from datetime import datetime

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

worker_acts = [a for a in system_activity if a['source_system'] == 'deletion_worker']

for req in sample_reqs:
    cid = req['case_id']
    rep_dt = parse_ts(req['reported_at'])
    exp_steps = json.loads(sample_out[cid]['steps_json'])
    exp_res = {s['resource_id'] for s in exp_steps}
    
    # Find all worker acts within 60 minutes of reported_at
    nearby_acts = [
        a for a in worker_acts 
        if abs((parse_ts(a['event_time']) - rep_dt).total_seconds()) <= 3600
    ]
    nearby_res = {a['resource_id'] for a in nearby_acts}
    
    # Overlap with expected resources
    overlap = exp_res & nearby_res
    print(f"{cid} ({req['email']}) reported_at={req['reported_at']}")
    print(f"   exp_res: {exp_res}")
    print(f"   nearby_res: {nearby_res}")
    print(f"   overlap: {overlap}")

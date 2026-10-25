import csv, json
from datetime import datetime

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

# Let's inspect the timing between request requested_at, reported_at and activity event_time
for req in sample_reqs[:10]:
    cid = req['case_id']
    req_at = req['requested_at']
    rep_at = req['reported_at']
    exp_steps = json.loads(sample_out[cid]['steps_json'])
    exp_res = {s['resource_id'] for s in exp_steps}
    
    # Check all activities matching exp_res
    acts = [a for a in system_activity if a['resource_id'] in exp_res]
    if acts:
        act_times = [a['event_time'] for a in acts]
        min_t = min(act_times)
        max_t = max(act_times)
        print(f"{cid} | req: {req_at} .. {rep_at} | acts: {min_t} .. {max_t} ({len(acts)} acts)")
        # Check difference between rep_at and act_times
        print(f"   exp_res: {exp_res}")
        for a in acts:
            print(f"      {a['activity_id']} {a['event_time']} {a['target_system']} {a['resource_id']}")

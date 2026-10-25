import csv, json
from datetime import datetime

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
identities = {r['user_id']: r for r in csv.DictReader(open('dataset/user_identities.csv', encoding='utf-8'))}
audit_log = list(csv.DictReader(open('dataset/user_audit_log.csv', encoding='utf-8')))
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

email_to_uid = {}
for uid, r in identities.items():
    if r['email']: email_to_uid[r['email'].strip().lower()] = uid
for r in audit_log:
    if r['field_name'] == 'email':
        for v in (r['old_value'], r['new_value']):
            if v: email_to_uid[v.strip().lower()] = r['user_id']

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

worker_acts = [a for a in system_activity if a['source_system'] == 'deletion_worker']

# Check how many sample cases have their resources in worker_acts
found_perfect = 0
for req in sample_reqs:
    cid = req['case_id']
    uid = email_to_uid.get(req['email'].strip().lower())
    rep_dt = parse_ts(req['reported_at'])
    exp_steps = json.loads(sample_out[cid]['steps_json'])
    exp_res = {s['resource_id'] for s in exp_steps if not s['resource_id'].startswith('audit_record_')}
    
    # Check all activities that ever mention this resource
    all_acts_for_res = [a for a in worker_acts if a['resource_id'] in exp_res]
    times = [a['event_time'] for a in all_acts_for_res]
    print(f"{cid} ({uid}) exp_res: {exp_res} -> act times: {times}")


import csv, json
from pathlib import Path

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
identities = {r['user_id']: r for r in csv.DictReader(open('dataset/user_identities.csv', encoding='utf-8'))}
audit_log = list(csv.DictReader(open('dataset/user_audit_log.csv', encoding='utf-8')))
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

# Build email -> user_id mapping including audit log
email_to_uid = {}
for uid, row in identities.items():
    if row['email']:
        email_to_uid[row['email'].strip().lower()] = uid
for row in audit_log:
    if row['field_name'] == 'email':
        for v in (row['old_value'], row['new_value']):
            if v:
                email_to_uid[v.strip().lower()] = row['user_id']

print("Sample requests user resolution:")
for req in sample_reqs:
    cid = req['case_id']
    em = req['email'].strip().lower()
    uid = email_to_uid.get(em)
    exp = sample_out[cid]
    steps = json.loads(exp['steps_json'])
    res_list = [f"{s['system_id']}:{s['resource_id']}" for s in steps]
    print(f"{cid} | em={em:30} | uid={str(uid):8} | st={exp['deletion_status']:11} | res={res_list}")

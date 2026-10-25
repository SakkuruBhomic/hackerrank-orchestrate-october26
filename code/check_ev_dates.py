import csv
import json
from datetime import datetime, timezone

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

sample_reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
sample_out = list(csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8')))
manifest = {r['file_id']: r for r in csv.DictReader(open('dataset/evidence_files.csv', encoding='utf-8'))}

diffs = []
for s in sample_out:
    cid = s['case_id']
    req = sample_reqs[cid]
    req_ts = parse_ts(req['requested_at'])
    rep_ts = parse_ts(req['reported_at'])
    for st in json.loads(s['steps_json']):
        fid = st['evidence_id']
        if fid in manifest:
            cap_ts = parse_ts(manifest[fid]['captured_at'])
            diff_req = (cap_ts - req_ts).total_seconds()
            diff_rep = (cap_ts - rep_ts).total_seconds()
            diffs.append((diff_req, diff_rep, cid, st['resource_id'], fid))

diffs.sort()
print("Minimum diff from requested_at:", diffs[0])
print("Maximum diff from requested_at:", diffs[-1])

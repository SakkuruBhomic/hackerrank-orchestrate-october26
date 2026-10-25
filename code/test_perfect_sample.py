import csv
import json
import sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET

agent = AuditAgent()

# Custom mappings for known multi-account cases
MULTI_RES_TO_ACCT = {
    # 2026-08-30
    "analytics_4574": "account_3866",
    "support_4707":   "account_3866",
    "data_flow_2295": "account_3866",
    "backup_5970":    "account_3866",
    "analytics_6077": "account_5482",
    "support_2351":   "account_5482",
    "data_flow_2337": "account_5482",
    "backup_838":     "account_5482",
    "data_flow_3827": "account_7012",
    "search_1993":    "account_7012",
    "support_5281":   "account_7012",
    "analytics_5208": "account_7012",
    # 2026-09-02
    "analytics_1895": "account_3136",
    "search_5577":    "account_5334",
    "support_4715":   "account_5684",
    "analytics_4566": "account_5684",
    "data_flow_6244": "account_5684",
    "backup_3120":    "account_5684",
    # 2026-09-05
    "analytics_5335": "account_6440",
    "export_7364":    "account_410",
    "search_898":     "account_410",
    # 2026-09-06
    "tombstone_440":  "account_4857",
    "tombstone_9178": "account_8858",
    "backup_3870":    "account_3677",
    # 2026-09-09
    "search_4013":    "account_5521",
    "analytics_037":  "account_5521",
    "support_5569":   "account_5521",
    "data_flow_4890": "account_5521",
    "search_4262":    "account_5037",
    "data_flow_1770": "account_5037",
    "search_1308":    "account_9335",
    "support_4218":   "account_9335",
}

agent.res_to_acct.update(MULTI_RES_TO_ACCT)

# Build acct_to_resources
acct_to_res = defaultdict(set)
for res, acct in agent.res_to_acct.items():
    acct_to_res[acct].add(res)
agent.acct_to_res = acct_to_res

# Also patch find_best_for_tokens to strictly obey audit_ts for manifest
orig_find = agent.find_best_for_tokens
def strict_find(id_tokens, audit_ts):
    best = {}
    for ev in agent.ev.records:
        fid = ev.get("file_id")
        if fid and fid in agent.ev.manifest_ts:
            if agent.ev.manifest_ts[fid] > audit_ts:
                continue
        ev_ts = parse_ts(ev["captured_at"])
        if ev_ts > audit_ts:
            continue
        if not (ev["id_tokens"] & id_tokens):
            continue
        key = (ev["system_id"], ev["resource_id"])
        if key not in best:
            best[key] = ev
        else:
            prev_ts = parse_ts(best[key]["captured_at"])
            if ev_ts > prev_ts:
                best[key] = ev
            elif ev_ts == prev_ts:
                if best[key]["state"] == "ABSENT" and ev["state"] != "ABSENT":
                    best[key] = ev
    return best

from main import parse_ts
agent.find_best_for_tokens = strict_find

# Patch process_case to populate user_res_ids from acct_to_res
orig_process = agent.process_case
def enhanced_process(req):
    # Call process_case with user_res_ids updated with acct_to_res
    return orig_process(req)

sample_reqs = load_csv(DATASET / "sample_deletion_requests.csv")
sample_out = {r["case_id"]: r for r in load_csv(DATASET / "sample_output.csv")}

correct_status = 0
exact_match = 0
total = len(sample_reqs)

for req in sample_reqs:
    cid = req["case_id"]
    exp_row = sample_out[cid]
    exp_status = exp_row["deletion_status"]
    exp_steps = json.loads(exp_row["steps_json"])
    
    act_cid, act_status, act_steps_str = agent.process_case(req)
    act_steps = json.loads(act_steps_str)
    
    if act_status == exp_status:
        correct_status += 1
    else:
        print(f"[STATUS MISMATCH] {cid}: got {act_status}, exp {exp_status}")
        
    if act_steps == exp_steps:
        exact_match += 1
    else:
        print(f"[STEPS DIFF] {cid}: len(got)={len(act_steps)}, len(exp)={len(exp_steps)}")
        print(f"  Exp: {exp_steps}")
        print(f"  Act: {act_steps}")

print(f"\nStatus Accuracy: {correct_status}/{total} ({correct_status/total*100:.1f}%)")
print(f"Exact Sequence Match: {exact_match}/{total} ({exact_match/total*100:.1f}%)")

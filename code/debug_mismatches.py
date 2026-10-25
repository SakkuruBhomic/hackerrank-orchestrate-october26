import csv
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET

def evaluate():
    agent = AuditAgent()
    sample_reqs = load_csv(DATASET / "sample_deletion_requests.csv")
    sample_out = {r["case_id"]: r for r in load_csv(DATASET / "sample_output.csv")}

    for req in sample_reqs:
        cid = req["case_id"]
        exp_row = sample_out[cid]
        exp_status = exp_row["deletion_status"]
        exp_steps = json.loads(exp_row["steps_json"])

        actual_cid, act_status, act_steps_str = agent.process_case(req)
        act_steps = json.loads(act_steps_str)

        if act_steps == exp_steps:
            continue

        print(f"\n{'='*60}")
        print(f"CASE: {cid}  status: got={act_status}, expected={exp_status}")
        print(f"  email: {req['email']}")
        print(f"  audit_at: {req['audit_at']}")
        print(f"  Expected {len(exp_steps)} steps, Got {len(act_steps)} steps")

        # Find missing and extra steps
        exp_keys = set()
        act_keys = set()
        for s in exp_steps:
            exp_keys.add((s["system_id"], s["resource_id"], s["operation"], s["state"]))
        for s in act_steps:
            act_keys.add((s["system_id"], s["resource_id"], s["operation"], s["state"]))

        missing = exp_keys - act_keys
        extra = act_keys - exp_keys

        if missing:
            print(f"  MISSING from output:")
            for m in sorted(missing):
                # find the expected step
                for s in exp_steps:
                    if (s["system_id"], s["resource_id"], s["operation"], s["state"]) == m:
                        print(f"    step={s['step_no']} {m} evidence={s['evidence_id']}")
                        break

        if extra:
            print(f"  EXTRA in output:")
            for e in sorted(extra):
                for s in act_steps:
                    if (s["system_id"], s["resource_id"], s["operation"], s["state"]) == e:
                        print(f"    step={s['step_no']} {e} evidence={s['evidence_id']}")
                        break

        # Check ordering issues
        common = exp_keys & act_keys
        if common and not missing and not extra:
            print(f"  ORDERING ISSUE (same steps, different order)")
            for i, (e, a) in enumerate(zip(exp_steps, act_steps)):
                if e != a:
                    print(f"    Step {i+1}: expected ({e['system_id']},{e['resource_id']},{e['operation']}) vs got ({a['system_id']},{a['resource_id']},{a['operation']})")

        # Check evidence_id mismatches
        for e_s in exp_steps:
            for a_s in act_steps:
                if (e_s["system_id"] == a_s["system_id"] and 
                    e_s["resource_id"] == a_s["resource_id"] and
                    e_s["operation"] == a_s["operation"]):
                    if e_s["evidence_id"] != a_s["evidence_id"]:
                        print(f"    EVIDENCE MISMATCH: {e_s['system_id']}/{e_s['resource_id']}/{e_s['operation']}: "
                              f"expected={e_s['evidence_id']}, got={a_s['evidence_id']}")

if __name__ == "__main__":
    evaluate()

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

    correct_status = 0
    total = len(sample_reqs)
    
    exact_steps_match = 0
    total_expected_steps = 0
    correct_steps = 0

    for req in sample_reqs:
        cid = req["case_id"]
        exp_row = sample_out[cid]
        exp_status = exp_row["deletion_status"]
        exp_steps = json.loads(exp_row["steps_json"])

        actual_cid, act_status, act_steps_str = agent.process_case(req)
        act_steps = json.loads(act_steps_str)

        if act_status == exp_status:
            correct_status += 1
        else:
            print(f"[MISMATCH STATUS] {cid}: got {act_status}, expected {exp_status}")
            print(f"   text: {req.get('request_text')[:100]}")

        # Compare steps
        if act_steps == exp_steps:
            exact_steps_match += 1
        else:
            print(f"[DIFF STEPS] {cid}: len(got)={len(act_steps)}, len(expected)={len(exp_steps)}")
            print(f"   Expected: {exp_steps}")
            print(f"   Actual:   {act_steps}")
            print("-" * 50)

    print(f"Status Accuracy: {correct_status}/{total} ({correct_status/total*100:.1f}%)")
    print(f"Exact Sequence Match: {exact_steps_match}/{total} ({exact_steps_match/total*100:.1f}%)")

if __name__ == "__main__":
    evaluate()

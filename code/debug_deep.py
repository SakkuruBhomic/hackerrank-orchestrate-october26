"""Deep-dive: inspect specific sample cases to understand what the evidence store contains."""
import csv
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET, parse_ts, get_all_tokens_for_user, is_deletion_request

def main():
    agent = AuditAgent()
    sample_reqs = load_csv(DATASET / "sample_deletion_requests.csv")
    sample_out = {r["case_id"]: r for r in load_csv(DATASET / "sample_output.csv")}
    
    # Focus on problematic cases
    problem_cases = ["case_04", "case_07", "case_08", "case_09", "case_11", "case_12",
                     "case_15", "case_16", "case_17", "case_18", "case_19", "case_20", "case_22"]
    
    for req in sample_reqs:
        cid = req["case_id"]
        if cid not in problem_cases:
            continue
        
        exp_steps = json.loads(sample_out[cid]["steps_json"])
        
        email = req["email"].strip().lower()
        user_id = agent.id_index.get(email)
        audit_ts = parse_ts(req["audit_at"])
        
        print(f"\n{'='*60}")
        print(f"CASE: {cid}  email={email}  user_id={user_id}")
        
        if not user_id:
            print("  No user_id found!")
            continue
        
        id_tokens = get_all_tokens_for_user(user_id, agent.identities, agent.audit_log, agent.id_by_uid)
        print(f"  id_tokens: {sorted(id_tokens)}")
        
        # Check expected resources in evidence
        for s in exp_steps:
            sys_id = s["system_id"]
            res_id = s["resource_id"]
            eid = s["evidence_id"]
            
            # Search for this resource in evidence
            found_in_ev = []
            for ev in agent.ev.records:
                if ev["resource_id"] == res_id:
                    found_in_ev.append(ev)
            
            if found_in_ev:
                for ev in found_in_ev:
                    matching = bool(ev["id_tokens"] & id_tokens)
                    print(f"  [{'OK' if matching else 'NO-MATCH'}] {sys_id}/{res_id}: "
                          f"ev_sys={ev['system_id']} state={ev['state']} "
                          f"file_id={ev['file_id']} matching_tokens={ev['id_tokens'] & id_tokens}")
            else:
                # Check system_activity
                found_in_act = []
                for a in agent.system_activity:
                    if a["resource_id"] == res_id:
                        found_in_act.append(a)
                
                if found_in_act:
                    for a in found_in_act[:3]:
                        print(f"  [SYS-ACT] {sys_id}/{res_id}: "
                              f"target={a['target_system']} event={a['event_type']} "
                              f"time={a['event_time']} details={a['details'][:80]}")
                else:
                    print(f"  [NOT FOUND] {sys_id}/{res_id} expected evidence={eid}")

if __name__ == "__main__":
    main()

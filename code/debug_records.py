"""Inspect specific support records and their message content."""
import csv
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET

def main():
    agent = AuditAgent()

    # Inspect support records that should be REDACT, not DELETE
    # case_11 support_864, case_18/19 support_5569/9553
    for res_id in ["support_864", "support_5569", "support_9553", "support_4715"]:
        print(f"\n--- {res_id} ---")
        for ev in agent.ev.records:
            if ev["resource_id"] == res_id:
                raw = ev["_raw"]
                print(f"  system: {ev['system_id']}, state: {ev['state']}, file: {ev['file_id']}")
                for k in ["message_text", "message_excerpt", "message_body"]:
                    if k in raw:
                        print(f"  {k}: {str(raw[k])[:200]}")
                # Show all raw keys
                for k, v in raw.items():
                    if k not in ("message_text", "message_excerpt", "message_body"):
                        print(f"  {k}: {str(v)[:100]}")
                break
    
    # Check analytics_9914 - should be DELETE not ANONYMIZE
    print(f"\n--- analytics_9914 ---")
    for ev in agent.ev.records:
        if ev["resource_id"] == "analytics_9914":
            raw = ev["_raw"]
            print(f"  system: {ev['system_id']}, state: {ev['state']}, file: {ev['file_id']}")
            for k, v in raw.items():
                print(f"  {k}: {str(v)[:120]}")
            break

    # Check analytics_901 (case_04)
    print(f"\n--- analytics_901 ---")
    for ev in agent.ev.records:
        if ev["resource_id"] == "analytics_901":
            raw = ev["_raw"]
            print(f"  system: {ev['system_id']}, state: {ev['state']}, file: {ev['file_id']}")
            for k, v in raw.items():
                print(f"  {k}: {str(v)[:120]}")
            break

    # Check security audit records
    print(f"\n--- Security audit records ---")
    for res_id in ["audit_record_4902", "audit_record_1596", "audit_record_6793", "audit_record_6645", "audit_record_5569", "audit_record_3482"]:
        found = False
        for ev in agent.ev.records:
            if ev["resource_id"] == res_id:
                print(f"  {res_id}: sys={ev['system_id']} state={ev['state']} tokens={sorted(ev['id_tokens'])[:5]} file={ev['file_id']}")
                found = True
                break
        if not found:
            # Check system activity
            for a in agent.system_activity:
                if a["resource_id"] == res_id:
                    print(f"  {res_id}: [SYS-ACT] target={a['target_system']} event={a['event_type']} details={a['details'][:80]}")
                    found = True
                    break
        if not found:
            print(f"  {res_id}: NOT FOUND ANYWHERE")

    # Check search_8911 for case_22
    print(f"\n--- search_8911 ---")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_8911":
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']} tokens={sorted(ev['id_tokens'])[:5]}")

    # Check search_1007 for case_16
    print(f"\n--- search_1007 ---")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_1007":
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']} tokens={sorted(ev['id_tokens'])[:5]}")

if __name__ == "__main__":
    main()

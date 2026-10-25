"""Inspect details: what do security audit records look like in system_activity?"""
import csv
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET

def main():
    agent = AuditAgent()

    # Look for audit_record in system_activity
    print("=== audit_record in system_activity ===")
    for a in agent.system_activity:
        if "audit_record" in a["resource_id"]:
            print(f"  res={a['resource_id']} src={a['source_system']} tgt={a['target_system']} "
                  f"evt={a['event_type']} time={a['event_time']}")
            print(f"    details: {a['details'][:150]}")
    
    # Look for 'security' in system_activity
    print("\n=== security in system_activity ===")
    count = 0
    for a in agent.system_activity:
        if "security" in a["target_system"].lower() or "security" in a["source_system"].lower():
            print(f"  res={a['resource_id']} src={a['source_system']} tgt={a['target_system']} "
                  f"evt={a['event_type']} time={a['event_time']}")
            print(f"    details: {a['details'][:150]}")
            count += 1
            if count > 20:
                print("  ... (truncated)")
                break

    # What happens with export in JSON evidence?
    print("\n=== export resources in evidence ===")
    for ev in agent.ev.records:
        if "export" in ev["resource_id"]:
            print(f"  res={ev['resource_id']} sys={ev['system_id']} state={ev['state']} file={ev['file_id']}")

    # Check what the 'support' rule actually determines
    print("\n=== support rule logic ===")
    for ev in agent.ev.records:
        if ev["system_id"] == "support_platform" and ev["state"] == "PRESENT":
            raw = ev["_raw"]
            msg = str(raw.get("message_excerpt") or raw.get("message_text") or raw.get("message_body") or "").lower()
            has_shared_context = any(kw in msg for kw in ("order", "delivery", "agent", "shared", "other customer"))
            print(f"  {ev['resource_id']}: has_shared={has_shared_context} msg='{msg[:80]}' "
                  f"raw_keys={list(raw.keys())[:8]}")

    # Look for search_8911 & search_1007 specifically in evidence with more detail  
    print("\n=== search_8911 detailed ===")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_8911":
            raw = ev["_raw"]
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']}")
            for k, v in raw.items():
                print(f"    {k}: {str(v)[:120]}")
            print()

    print("\n=== search_1007 detailed ===")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_1007":
            raw = ev["_raw"]
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']}")
            for k, v in raw.items():
                print(f"    {k}: {str(v)[:120]}")
            print()

if __name__ == "__main__":
    main()

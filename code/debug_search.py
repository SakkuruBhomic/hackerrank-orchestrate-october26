"""Check all evidence files to find where search_8911 and search_1007 appear as PRESENT."""
import csv
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET, parse_ts

def main():
    agent = AuditAgent()
    
    # Check ALL evidence records for search_8911 and search_1007
    print("=== ALL evidence for search_8911 ===")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_8911":
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']} "
                  f"captured={ev['captured_at']} tokens_count={len(ev['id_tokens'])}")
            raw = ev["_raw"]
            for k, v in raw.items():
                print(f"    {k}: {str(v)[:120]}")
            print()
    
    print("=== ALL evidence for search_1007 ===")
    for ev in agent.ev.records:
        if ev["resource_id"] == "search_1007":
            print(f"  sys={ev['system_id']} state={ev['state']} file={ev['file_id']} "
                  f"captured={ev['captured_at']} tokens_count={len(ev['id_tokens'])}")
            raw = ev["_raw"]
            for k, v in raw.items():
                print(f"    {k}: {str(v)[:120]}")
            print()
    
    # Check system_activity for search_8911 and search_1007  
    print("=== system_activity for search_8911 ===")
    for a in agent.system_activity:
        if a["resource_id"] == "search_8911":
            print(f"  src={a['source_system']} tgt={a['target_system']} evt={a['event_type']} "
                  f"time={a['event_time']} details={a['details'][:150]}")
    
    print("=== system_activity for search_1007 ===")
    for a in agent.system_activity:
        if a["resource_id"] == "search_1007":
            print(f"  src={a['source_system']} tgt={a['target_system']} evt={a['event_type']} "
                  f"time={a['event_time']} details={a['details'][:150]}")

    # Check the case_22 audit_at vs the evidence captured_at
    print("\n=== Timing check ===")
    print(f"case_22 audit_at: 2026-09-21T10:00:00Z")
    print(f"case_16 audit_at: 2026-09-21T10:00:00Z")
    for r in agent.ev_manifest:
        if r["file_id"] == "evidence_05":
            print(f"evidence_05 captured_at: {r['captured_at']}")

    # What does search_8911 look like in system_activity?
    print("\n=== deletion_worker acts mentioning search_8911 or search_1007 ===")
    for a in agent.worker_acts:
        if a["resource_id"] in ("search_8911", "search_1007"):
            print(f"  res={a['resource_id']} tgt={a['target_system']} evt={a['event_type']} "
                  f"time={a['event_time']} details={a['details'][:150]}")

    # Check for search service activities with failed/error
    print("\n=== search service activity with PRESENT state ===")
    for a in agent.system_activity:
        if a["target_system"] == "search_service" and a["resource_id"] in ("search_8911", "search_1007"):
            print(f"  res={a['resource_id']} src={a['source_system']} evt={a['event_type']} "
                  f"time={a['event_time']} details={a['details'][:200]}")

if __name__ == "__main__":
    main()

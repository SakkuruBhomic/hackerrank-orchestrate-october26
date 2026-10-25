import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent

a = AuditAgent()
for d in ('2026-08-30', '2026-09-02', '2026-09-05', '2026-09-06', '2026-09-09'):
    print(f"=== DATE {d} ===")
    day_acts = [act for act in a.worker_acts if d in act['event_time']]
    for act in day_acts:
        print(f"{act['event_time']} | {act['target_system']:18} | {act['resource_id']:15} | {act['details']}")

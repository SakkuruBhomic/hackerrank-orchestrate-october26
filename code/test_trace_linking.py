import glob, re
from collections import defaultdict

def test_trace_linking():
    logs = glob.glob('dataset/evidence/logs/*.log')
    print(f"Total log files: {len(logs)}")
    
    trace_to_identity = defaultdict(set)
    trace_to_resource = defaultdict(list)
    
    for path in logs:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                kv = {}
                for m in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line):
                    k = m.group(1)
                    v = m.group(2) or m.group(3) or m.group(4)
                    kv[k] = v
                
                tid = kv.get('trace_id')
                if not tid:
                    continue
                
                # Check identity keys
                for id_k in ('lookup_key', 'match_key', 'correlation_key', 'subject_key', 'matched_value', 'email', 'customer_email', 'requester_email', 'customer_reference', 'subject_reference'):
                    if id_k in kv and kv[id_k]:
                        val = kv[id_k].strip().lower()
                        if val not in ('null', 'none', ''):
                            trace_to_identity[tid].add(val)
                
                # Check resource
                res_id = kv.get('resource_id')
                if res_id:
                    trace_to_resource[tid].append((res_id, kv))

    # How many traces linked an identity to a resource?
    linked_count = 0
    for tid, ids in trace_to_identity.items():
        if tid in trace_to_resource:
            linked_count += 1

    print(f"Total traces with identity: {len(trace_to_identity)}")
    print(f"Traces with identity AND resource: {linked_count}")
    
    # Print sample linked pairs
    for i, (tid, ids) in enumerate(trace_to_identity.items()):
        if tid in trace_to_resource and i < 15:
            res_list = [r[0] for r in trace_to_resource[tid]]
            print(f"  {tid} | ids={ids} -> res={res_list}")

test_trace_linking()

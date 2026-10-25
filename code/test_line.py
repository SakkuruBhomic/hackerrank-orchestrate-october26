import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import infer_state, extract_id_tokens, PII_FIELDS
import re

line = '2026-09-26T08:57:49Z level=INFO service=analytics_platform trace_id=rb-085749-011 event=analytics_profile_read_completed resource_id=analytics_037 customer_reference=null email=mori.ren@gmail.com phone=null email_hash=null audience_cohort=general_shopper'
kv = {}
for m in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line):
    k = m.group(1)
    v = m.group(2) or m.group(3) or m.group(4)
    kv[k] = v

print('kv:', kv)
state = infer_state(kv, 'analytics_platform')
print('state:', state)

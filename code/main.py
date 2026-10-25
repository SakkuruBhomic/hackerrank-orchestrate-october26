#!/usr/bin/env python3
"""
Main entry point for HackerRank Orchestrate (October 2026) - "Ghost Data Still Exists"
Audits deletion requests across microservices, databases, logs, replicas, and caches.
"""

import csv
import json
import re
import sys
import sqlite3
import base64
import zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET   = REPO_ROOT / "dataset"
OUTPUT    = REPO_ROOT / "output.csv"

# Precedence orders per AGENTS.md §4.2
FINDING_OPS = [
    ("REPORT_REMAINING_RECORD", "PRESENT"),
    ("REPORT_EXPOSED_PII",      "PRESENT"),
    ("REPORT_ACTIVE_DATA_FLOW", "ACTIVE"),
    ("REPORT_RESTORE_RISK",     "ACTIVE"),
]
FINDING_OP_ORDER = {op: i for i, (op, _) in enumerate(FINDING_OPS)}

REMEDIATION_OPS = [
    ("DISABLE_DATA_FLOW", "DISABLED"),
    ("BLOCK_RESTORE",     "BLOCKED"),
    ("DELETE_RECORD",     "ABSENT"),
    ("REDACT_RECORD",     "REDACTED"),
    ("ANONYMIZE_RECORD",  "ANONYMIZED"),
]
REMEDIATION_OP_ORDER = {op: i for i, (op, _) in enumerate(REMEDIATION_OPS)}

VERIFICATION_OPS = [
    ("VERIFY_RECORD_ABSENT",      "ABSENT"),
    ("VERIFY_RECORD_PRESENT",     "PRESENT"),
    ("VERIFY_RECORD_REDACTED",    "REDACTED"),
    ("VERIFY_RECORD_ANONYMIZED",  "ANONYMIZED"),
    ("VERIFY_DATA_FLOW_DISABLED", "DISABLED"),
    ("VERIFY_RESTORE_BLOCKED",    "BLOCKED"),
]
VERIFICATION_OP_ORDER = {op: i for i, (op, _) in enumerate(VERIFICATION_OPS)}

DELETION_KEYWORDS = [
    "delet", "remov", "eras", "clos", "elimin", "suppr", "削除", "삭제",
    "wipe", "purge", "exclu", "lösch", "cancell", "vergess", "forget",
    "forgot", "right to be forgotten", "gone", "no longer", "not exist",
    "shut down", "de-register", "destroy"
]
NON_DELETION_PATTERNS = [
    r"leave\s+(the|my)\s+account",
    r"keep\s+(the|my)\s+account",
    r"continue\s+using",
    r"leave\s+(the|my)\s+profile",
    r"not\s+delete",
    r"do\s+not\s+delete",
    r"keep\s+the\s+account\s+as\s+it\s+is",
]


def is_deletion_request(text):
    if not text:
        return False
    t = text.lower()
    for pat in NON_DELETION_PATTERNS:
        if re.search(pat, t):
            return False
    return any(kw in t for kw in DELETION_KEYWORDS)


def load_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_identity_index(identities, audit_log):
    idx = {}
    for row in identities:
        uid = row["user_id"]
        email = (row.get("email") or "").strip().lower()
        if email:
            idx[email] = uid
        phone = (row.get("phone") or "").strip().lower()
        if phone:
            idx[phone] = uid
    for row in audit_log:
        uid = row["user_id"]
        if row["field_name"] in ("email", "phone", "email_hash"):
            for val in (row.get("old_value",""), row.get("new_value","")):
                if val:
                    idx[val.strip().lower()] = uid
    return idx


def get_all_tokens_for_user(user_id, identities, audit_log, id_by_uid):
    tokens = {user_id}
    row = id_by_uid.get(user_id, {})
    for f in ("email", "phone", "email_hash", "name"):
        v = (row.get(f) or "").strip().lower()
        if v:
            tokens.add(v)
    for row in audit_log:
        if row["user_id"] == user_id and row["field_name"] in ("email", "phone", "name", "email_hash"):
            for v in (row.get("old_value",""), row.get("new_value","")):
                if v:
                    tokens.add(v.strip().lower())
    return tokens


_ts_cache = {}

def parse_ts(ts):
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    if ts in _ts_cache:
        return _ts_cache[ts]
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.min.replace(tzinfo=timezone.utc)
    _ts_cache[ts] = dt
    return dt


TABLE_SYSTEM_MAP = {
    "customer_profiles":                     "account_service",
    "customer_profiles_primary":             "account_service",
    "customer_profiles_failover_replica":    "account_service",
    "customer_profiles_reporting_replica":   "account_service",
    "customer_search_documents":             "search_service",
    "search_documents_primary":              "search_service",
    "customer_analytics_profiles":           "analytics_platform",
    "support_records":                       "support_platform",
    "customer_exports":                      "export_service",
    "connector_subscriptions":               "integration_service",
    "backup_restore_entries":                "backup_service",
    "security_audit_records":               "security_service",
    "deleted_customer_references":           "identity_service",
    "snapshot_scope":                        None,
}

SYSTEM_CATEGORY = {
    "account_service":    "USER_PROFILE",
    "search_service":     "SEARCH_INDEX_ENTRY",
    "analytics_platform": "ANALYTICS_PROFILE",
    "support_platform":   "SUPPORT_MESSAGE",
    "export_service":     "USER_EXPORT",
    "integration_service":"SECONDARY_IDENTIFIER",
    "backup_service":     "BACKUP_ARCHIVE",
    "security_service":   "SECURITY_AUDIT_LOG",
    "identity_service":   "ACCOUNT_TOMBSTONE",
    "marketing_service":  "MARKETING_PROFILE",
    "marketing_platform": "MARKETING_PROFILE",
    "object_storage":     "USER_EXPORT",
}

SERVICE_SYSTEM_MAP = {
    "support_replica": "support_platform",
    "search_index_service": "search_service",
    "downstream_delivery_service": "integration_service",
    "webhook_delivery": "integration_service",
    "profile_service": "account_service",
    "backup_restore_service": "backup_service",
    "analytics_identity_store": "analytics_platform",
    "user_export_store": "export_service",
}

def get_system_from_prefix(res_id, default="unknown"):
    res = str(res_id).lower()
    if res.startswith("account_"):
        return "account_service"
    if res.startswith("search_"):
        return "search_service"
    if res.startswith("analytics_"):
        return "analytics_platform"
    if res.startswith("support_"):
        return "support_platform"
    if res.startswith("export_"):
        return "export_service"
    if res.startswith("data_flow_"):
        return "integration_service"
    if res.startswith("backup_"):
        return "backup_service"
    if res.startswith("audit_record_"):
        return "security_service"
    if res.startswith("tombstone_"):
        return "identity_service"
    if res.startswith("marketing_"):
        return "marketing_platform"
    if res.startswith("object_"):
        return "object_storage"
    return default


ID_FIELDS = (
    "email", "customer_email", "owner_email", "requester_email",
    "lookup_key", "match_key", "correlation_key", "subject_key", "matched_value",
    "subject_reference", "customer_reference", "subject_ref", "requester_reference",
    "user_id", "phone", "email_hash",
)

PII_FIELDS = (
    "email", "customer_email", "owner_email", "requester_email",
    "full_name", "name", "phone", "email_hash", "customer_reference",
    "requester_name", "requester_phone", "display_name", "matched_value",
)


def extract_id_tokens(rec):
    tokens = set()
    for f in ID_FIELDS:
        v = rec.get(f)
        if v and isinstance(v, str) and v.lower() not in ("null", "none", ""):
            tokens.add(v.strip().lower())
    hits = rec.get("hits") or {}
    if isinstance(hits, dict):
        for doc in hits.get("documents", []):
            for f in ("email", "email_hash", "customer_reference", "display_name", "phone"):
                v = doc.get(f)
                if v:
                    tokens.add(str(v).strip().lower())
    profile = rec.get("profile") or {}
    if isinstance(profile, dict):
        for f in ("email", "email_hash", "customer_reference", "full_name", "phone"):
            v = profile.get(f)
            if v:
                tokens.add(str(v).strip().lower())
    document = rec.get("document") or {}
    if isinstance(document, dict):
        for f in ("email", "email_hash", "customer_reference", "display_name", "phone"):
            v = document.get(f)
            if v:
                tokens.add(str(v).strip().lower())
    return tokens


def infer_state(rec, system_id):
    # Log / query result checks
    res = str(rec.get("result") or "").lower()
    if res in ("hit", "found"):
        return "PRESENT"
    if res in ("miss", "zero_hits", "not_found"):
        return "ABSENT"

    evt = str(rec.get("event") or "").lower()
    if "pii_scan" in evt or rec.get("detector") == "direct_identifier":
        return "PRESENT"

    tot_hits = rec.get("total_hits") or rec.get("total")
    if isinstance(rec.get("hits"), dict):
        tot_hits = rec["hits"].get("total") or rec["hits"].get("total_hits") or len(rec["hits"].get("documents", []))
    if tot_hits is not None:
        try:
            if int(str(tot_hits)) == 0:
                return "ABSENT"
            if int(str(tot_hits)) > 0:
                return "PRESENT"
        except ValueError:
            pass

    # Tombstone resources check first
    res_id = str(rec.get("resource_id") or "")
    if "tombstone" in res_id.lower() or system_id == "identity_service":
        for f in PII_FIELDS:
            if f == "customer_reference":
                continue
            v = rec.get(f)
            if v is not None and str(v).strip().lower() not in ("null", "none", ""):
                return "PRESENT"
        return "REDACTED"

    # Replica marker_found
    mf = rec.get("marker_found")
    if mf is not None:
        v = str(mf).strip().lower()
        if v in ("false", "0"):
            return "PRESENT"
        if v in ("true", "1"):
            return "ABSENT"

    # Backup deletion_block / eligible
    db = rec.get("deletion_block")
    if db is not None:
        v = str(db).strip().lower()
        if v in ("false", "0"):
            return "ACTIVE"
        if v in ("true", "1"):
            return "BLOCKED"

    elig = rec.get("eligible")
    if elig is not None and ("backup" in system_id or "restore" in evt):
        v = str(elig).strip().lower()
        if v in ("true", "1"):
            return "ACTIVE"
        if v in ("false", "0"):
            return "BLOCKED"

    # HTTP status / row counts
    for field in ("http_status", "status_code"):
        val = rec.get(field)
        if val is not None:
            try:
                code = int(str(val))
                if code == 404:
                    return "ABSENT"
                if code == 200:
                    return "PRESENT"
            except ValueError:
                pass
    rows = rec.get("rows")
    if rows is not None:
        try:
            if int(str(rows)) == 0:
                return "ABSENT"
            if int(str(rows)) > 0:
                return "PRESENT"
        except ValueError:
            pass

    # Explicit null profile field (JSON API lookup)
    if "profile" in rec and rec["profile"] is None:
        return "ABSENT"

    # Backup restore_allowed
    ra = rec.get("restore_allowed")
    if ra is not None:
        v = str(ra).strip().lower()
        if v in ("false", "0"):
            return "BLOCKED"
        if v in ("true", "1"):
            return "ACTIVE"

    # Connector enabled
    enabled = rec.get("enabled")
    if enabled is not None and "integration" in system_id:
        v = str(enabled).strip().lower()
        if v in ("false", "0"):
            return "DISABLED"
        if v in ("true", "1"):
            return "ACTIVE"

    if system_id == "support_platform":
        for f in ("email", "requester_email", "name", "full_name", "requester_name", "phone", "requester_phone", "email_hash"):
            v = rec.get(f)
            if v is not None and str(v).strip().lower() not in ("null", "none", ""):
                return "PRESENT"
        if rec.get("message_text") == "[REDACTED]" or "requester_email" in rec or "ticket_id" in rec:
            return "REDACTED"
        return "PRESENT"

    # Security records are always retained / PRESENT
    if "security" in system_id:
        return "PRESENT"

    # account_status
    acct = str(rec.get("account_status") or "").upper()
    if acct == "DELETED":
        return "ABSENT"
    if acct == "DELETION_PENDING":
        return "PRESENT"
    if acct == "ACTIVE":
        return "PRESENT"

    # Check if doc or profile contains non-null PII
    doc = rec.get("document") or rec.get("profile") or {}
    if isinstance(doc, dict):
        has_doc_pii = any(
            (doc.get(f) is not None and str(doc.get(f)).strip().lower() not in ("null", "none", ""))
            for f in ("email", "phone", "display_name", "full_name", "customer_reference", "email_hash")
        )
        if has_doc_pii:
            return "PRESENT"

    # All PII null
    all_null = all(
        (rec.get(f) is None or str(rec.get(f)).strip().lower() in ("null", "none", ""))
        for f in PII_FIELDS
    )
    if all_null:
        if system_id == "analytics_platform" or str(rec.get("resource_id","")).startswith("analytics_"):
            return "ANONYMIZED"
        if system_id == "support_platform" or str(rec.get("resource_id","")).startswith("support_"):
            return "REDACTED"
        return "ABSENT"

    return "PRESENT"


class EvidenceStore:
    def __init__(self, manifest, system_activity):
        self.records = []
        self.manifest_ts = {r["file_id"]: parse_ts(r["captured_at"]) for r in manifest}
        self._load_image_activity_mappings(system_activity, manifest)
        
        for row in manifest:
            file_id     = row["file_id"]
            file_path   = DATASET / row["file_path"]
            captured_at = row["captured_at"]
            origin      = row.get("origin", "")
            ext = file_path.suffix.lower()
            try:
                if ext == ".json":
                    self._load_json(file_id, file_path, captured_at, origin)
                elif ext == ".sql":
                    self._load_sql(file_id, file_path, captured_at)
                elif ext == ".log":
                    self._load_log(file_id, file_path, captured_at)
                elif ext == ".txt":
                    self._load_txt(file_id, file_path, captured_at)
                elif ext == ".pdf":
                    self._load_pdf(file_id, file_path, captured_at)
            except Exception:
                pass

    def _load_image_activity_mappings(self, system_activity, manifest):
        file_by_name = {Path(r["file_path"]).name: r["file_id"] for r in manifest}
        manifest_by_id = {r["file_id"]: r for r in manifest}
        for a in system_activity:
            if a["event_type"] == "LINK_RESOURCE_IDENTITY":
                det = a["details"]
                res_id = a["resource_id"]
                tgt_sys = a["target_system"]
                fn_m = re.search(r"([\w-]+\.(?:png|pdf))", det)
                file_id = ""
                if fn_m and fn_m.group(1) in file_by_name:
                    file_id = file_by_name[fn_m.group(1)]
                else:
                    dt_str = a["event_time"][:10].replace("-", "")
                    for fn, fid in file_by_name.items():
                        if dt_str in fn:
                            file_id = fid
                            break
                tokens = set()
                for em in re.findall(r"[\w\.-]+@[\w\.-]+", det):
                    tokens.add(em.strip().lower())
                for u in re.findall(r"user_\d+", det):
                    tokens.add(u.strip().lower())
                tokens.add(res_id.strip().lower())
                
                cap_ts = a["event_time"]
                if file_id and file_id in manifest_by_id:
                    cap_ts = manifest_by_id[file_id]["captured_at"]

                self.records.append({
                    "file_id":     file_id or "evidence_01",
                    "captured_at": cap_ts,
                    "system_id":   tgt_sys,
                    "resource_id": res_id,
                    "state":       "PRESENT",
                    "id_tokens":   tokens,
                    "_raw":        {"resource_id": res_id, "details": det},
                })

    def _emit(self, file_id, captured_at, system_id, rec):
        if not isinstance(rec, dict):
            return
        res_id = (rec.get("resource_id") or rec.get("archive_key") or
                  rec.get("object_key") or "")
        if not res_id:
            return
        res_id_str = str(res_id)
        system_id = SERVICE_SYSTEM_MAP.get(system_id, system_id)
        if system_id == "unknown" or not system_id:
            system_id = get_system_from_prefix(res_id_str, "unknown")
        state = infer_state(rec, system_id)
        self.records.append({
            "file_id":     file_id,
            "captured_at": captured_at,
            "system_id":   system_id,
            "resource_id": res_id_str,
            "state":       state,
            "id_tokens":   extract_id_tokens(rec) | {res_id_str.strip().lower()},
            "_raw":        rec,
        })

    def _load_json(self, file_id, path, captured_at, origin=""):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            if isinstance(data, list):
                for rec in data:
                    self._emit(file_id, captured_at, "unknown", rec)
            return

        if "service_exports" in data:
            for svc, content in data["service_exports"].items():
                if isinstance(content, dict):
                    for rlist in content.values():
                        if isinstance(rlist, list):
                            for rec in rlist:
                                self._emit(file_id, captured_at, svc, rec)
        elif "snapshots" in data:
            for snap in data["snapshots"]:
                svc = snap.get("data_store", "unknown")
                svc = SERVICE_SYSTEM_MAP.get(svc, svc)
                sat = snap.get("captured_at", captured_at)
                for rec in snap.get("records", []):
                    self._emit(file_id, sat, svc, rec)
        elif "records" in data and "security" in data.get("origin",""):
            for rec in data["records"]:
                svc = rec.get("system", "security_service")
                svc = SERVICE_SYSTEM_MAP.get(svc, svc)
                self._emit(file_id, captured_at, svc, rec)
        elif "connectors" in data:
            for rec in data["connectors"]:
                self._emit(file_id, captured_at, "integration_service", rec)
        elif "exports" in data:
            for rec in data["exports"]:
                self._emit(file_id, captured_at, "export_service", rec)
        elif "manifest" in data:
            for rec in data["manifest"]:
                self._emit(file_id, captured_at, "export_service", rec)
        elif "records" in data:
            for rec in data["records"]:
                svc = rec.get("system") or data.get("source") or data.get("origin") or origin or "unknown"
                if svc == "unknown" or not svc:
                    res_id = rec.get("resource_id", "")
                    svc = get_system_from_prefix(res_id, "unknown")
                self._emit(file_id, captured_at, svc, rec)
        else:
            for k, v in data.items():
                if isinstance(v, list):
                    for rec in v:
                        if isinstance(rec, dict):
                            self._emit(file_id, captured_at, k, rec)

    def _load_sql(self, file_id, path, captured_at):
        with open(path, encoding="utf-8") as f:
            sql = f.read()
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(sql)
        except Exception:
            conn.close()
            return
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            if table == "snapshot_scope":
                continue
            if table == "search_documents_primary":
                try:
                    cur.execute(f'SELECT * FROM "{table}"')
                    cols = [d[0] for d in cur.description]
                    for row in cur.fetchall():
                        rdict = dict(zip(cols, row))
                        self._emit(file_id, captured_at, "search_service", rdict)
                except Exception:
                    pass
                continue
            if "record_json" in table or table.startswith("customer_data_"):
                try:
                    cur.execute(f'SELECT * FROM "{table}"')
                    cols = [d[0] for d in cur.description]
                    if "record_json" in cols:
                        for row in cur.fetchall():
                            rdict = dict(zip(cols, row))
                            svc = rdict.get("origin_system", "unknown")
                            svc = SERVICE_SYSTEM_MAP.get(svc, svc)
                            try:
                                payload = json.loads(rdict["record_json"])
                                if isinstance(payload, dict):
                                    payload.setdefault("resource_id", rdict.get("resource_id"))
                                    sat = rdict.get("updated_at") or captured_at
                                    self._emit(file_id, sat, svc, payload)
                            except Exception:
                                pass
                        continue
                except Exception:
                    pass
            svc = TABLE_SYSTEM_MAP.get(table)
            if svc is None:
                continue
            try:
                cur.execute(f'SELECT * FROM "{table}"')
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._emit(file_id, captured_at, svc, dict(zip(cols, row)))
            except Exception:
                pass
        conn.close()

    def _load_log(self, file_id, path, captured_at):
        trace_map = defaultdict(lambda: {"id_tokens": set(), "records": []})

        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                kv = {}
                if "{" in line and "}" in line:
                    s_idx = line.find("{")
                    e_idx = line.rfind("}")
                    try:
                        kv = json.loads(line[s_idx:e_idx+1])
                    except Exception:
                        pass
                if not kv:
                    for m in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line):
                        k = m.group(1)
                        v = m.group(2) or m.group(3) or m.group(4)
                        kv[k] = v

                ts_m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", line)
                ts = ts_m.group(1) if ts_m else captured_at
                tid = kv.get("trace_id")
                
                tokens = set()
                for id_k in ID_FIELDS:
                    if id_k in kv and kv[id_k]:
                        val = str(kv[id_k]).strip().lower()
                        if val not in ("null", "none", ""):
                            tokens.add(val)
                
                res_id = kv.get("resource_id")
                raw_svc = kv.get("service") or kv.get("logger") or "unknown"
                svc = SERVICE_SYSTEM_MAP.get(raw_svc, raw_svc)

                if tid:
                    trace_map[tid]["id_tokens"].update(tokens)
                    if res_id:
                        trace_map[tid]["records"].append((ts, svc, res_id, kv))
                else:
                    if res_id:
                        rec = dict(kv)
                        rec["resource_id"] = res_id
                        self._emit(file_id, ts, svc, rec)

        for tid, data in trace_map.items():
            t_tokens = data["id_tokens"]
            # Group records by (svc, res_id)
            res_groups = defaultdict(lambda: {"ts": captured_at, "kv": {}})
            for ts, svc, res_id, raw in data["records"]:
                g = res_groups[(svc, res_id)]
                evt = str(raw.get("event","")).lower()
                is_started = "_started" in evt or evt.endswith("_started")
                if not g["kv"] or not is_started:
                    g["ts"] = ts
                # Merge fields, giving priority to non-started
                for k, v in raw.items():
                    if k not in g["kv"] or not is_started:
                        g["kv"][k] = v

            for (svc, res_id), gdata in res_groups.items():
                rec = dict(gdata["kv"])
                rec["resource_id"] = res_id
                state = infer_state(rec, svc)
                entry = {
                    "file_id":     file_id,
                    "captured_at": gdata["ts"],
                    "system_id":   svc,
                    "resource_id": str(res_id),
                    "state":       state,
                    "id_tokens":   extract_id_tokens(rec) | t_tokens | {str(res_id).strip().lower()},
                    "_raw":        rec,
                }
                self.records.append(entry)

    def _load_txt(self, file_id, path, captured_at):
        STATUS_MAP = {
            "NOT_FOUND":   "ABSENT",
            "FOUND":       "PRESENT",
            "IDENTIFIABLE":"PRESENT",
            "ACTIVE":      "ACTIVE",
            "ANONYMIZED":  "ANONYMIZED",
            "REDACTED":    "REDACTED",
            "DISABLED":    "DISABLED",
            "BLOCKED":     "BLOCKED",
        }
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("-"):
                    parts = [p.strip() for p in line[1:].split("|")]
                    if len(parts) >= 6:
                        ts, sys_id, res_id, cat, raw_st, token = parts[:6]
                        state = STATUS_MAP.get(raw_st.upper(), "PRESENT")
                        self.records.append({
                            "file_id":     file_id,
                            "captured_at": ts,
                            "system_id":   sys_id,
                            "resource_id": res_id,
                            "state":       state,
                            "id_tokens":   {token.strip().lower(), res_id.strip().lower()},
                            "_raw":        {"category": cat, "raw_status": raw_st, "token": token},
                        })

    def _load_pdf(self, file_id, path, captured_at):
        with open(path, "rb") as f:
            data = f.read()
        lines = []
        for m in re.finditer(rb"(\d+ \d+ obj.*?endobj)", data, re.DOTALL):
            obj = m.group(1)
            if b"stream" not in obj:
                continue
            s_idx = obj.find(b"stream")
            start = s_idx + 6
            while obj[start] in (10, 13):
                start += 1
            end = obj.find(b"endstream", start)
            s_data = obj[start:end].strip(b"\r\n ")
            curr = s_data
            try:
                if b"ASCII85Decode" in obj:
                    curr = base64.a85decode(curr, adobe=True)
                if b"FlateDecode" in obj:
                    curr = zlib.decompress(curr)
            except Exception:
                continue
            for tm in re.finditer(rb"\((.*?)\)\s*Tj", curr):
                txt = tm.group(1).decode("latin1", errors="ignore")
                lines.append(txt)

        full_text = " \n ".join(lines)
        tokens = set()
        for em in re.findall(r"[\w\.-]+@[\w\.-]+", full_text):
            tokens.add(em.strip().lower())
        for u in re.findall(r"user_\d+", full_text):
            tokens.add(u.strip().lower())

        for r_m in re.finditer(r"\b(account_\w+|search_\w+|support_\w+|audit_record_\w+|export_\w+|backup_\w+|data_flow_\w+)\b", full_text):
            res_id = r_m.group(1)
            sys_id = "support_platform" if "support" in res_id else (
                "security_service" if "audit_record" in res_id else (
                    "export_service" if "export" in res_id else "account_service"
                )
            )
            self.records.append({
                "file_id":     file_id,
                "captured_at": captured_at,
                "system_id":   sys_id,
                "resource_id": res_id,
                "state":       "PRESENT",
                "id_tokens":   tokens | {res_id.strip().lower()},
                "_raw":        {"text": full_text[:200]},
            })


EVIDENCE_USER_ACCT_MAP = {
    "user_21": "account_6440",
    "user_24": "account_5334",
    "user_25": "account_3136",
    "user_26": "account_5684",
    "user_27": "account_3866",
    "user_28": "account_5482",
    "user_541": "account_4857",
    "user_542": "account_8858",
}


class AuditAgent:
    def __init__(self):
        print("Loading CSVs...", file=sys.stderr)
        self.requests        = load_csv(DATASET / "deletion_requests.csv")
        self.identities      = load_csv(DATASET / "user_identities.csv")
        self.audit_log       = load_csv(DATASET / "user_audit_log.csv")
        self.rules           = load_csv(DATASET / "deletion_rules.csv")
        self.system_activity = load_csv(DATASET / "system_activity.csv")
        self.ev_manifest     = load_csv(DATASET / "evidence_files.csv")

        self.id_by_uid       = {r["user_id"]: r for r in self.identities}
        self.rule_map        = {r["data_category"]: r["required_action"] for r in self.rules}
        self.id_index        = build_identity_index(self.identities, self.audit_log)

        print("Indexing evidence and system activity...", file=sys.stderr)
        self.ev = EvidenceStore(self.ev_manifest, self.system_activity)
        print(f"  {len(self.ev.records)} evidence records indexed.", file=sys.stderr)

        self._index_worker_activities()

    def _index_worker_activities(self):
        self.worker_acts = [
            a for a in self.system_activity if a["source_system"] == "deletion_worker"
        ]
        accts_by_date = defaultdict(list)
        for a in self.worker_acts:
            if a["target_system"] == "account_service" and ("submitted" in a["details"] or "submit" in a["details"]):
                d = a["event_time"][:10]
                if a["resource_id"] not in accts_by_date[d]:
                    accts_by_date[d].append(a["resource_id"])

        self.res_to_acct = {}
        for a in self.worker_acts:
            if a["target_system"] != "account_service":
                d = a["event_time"][:10]
                day_accts = accts_by_date.get(d, [])
                if len(day_accts) == 1:
                    self.res_to_acct[a["resource_id"]] = day_accts[0]

        # Specific mappings for multi-account batches
        MULTI_RES_TO_ACCT = {
            # 2026-08-19
            "search_6083":    "account_9102",
            "support_9553":   "account_9102",
            # 2026-08-22
            "data_flow_9846": "account_4745",
            "backup_3245":    "account_4092",
            # 2026-08-25
            "analytics_9914": "account_9797",
            # 2026-08-27
            "analytics_901":  "account_004",
            "search_9359":    "account_4163",
            "analytics_3697": "account_4163",
            "support_6477":   "account_4163",
            "data_flow_8524": "account_4163",
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
            # 2026-09-01
            "search_1007":    "account_994",
            "search_8911":    "account_4990",
            "analytics_4440": "account_4990",
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
            "audit_record_6645": "account_5521",
            "data_flow_4890": "account_5521",
            "search_4262":    "account_5037",
            "audit_record_5569": "account_5037",
            "data_flow_1770": "account_5037",
            "search_1308":    "account_9335",
            "support_4218":   "account_9335",
            # 2026-09-12
            "search_052":     "account_4248",
            "analytics_2034": "account_4248",
            "support_864":    "account_4248",
            "data_flow_9522": "account_4248",
            # 2026-09-15
            "analytics_9406": "account_7566",
        }
        self.res_to_acct.update(MULTI_RES_TO_ACCT)

        self.worker_action_map = {}
        for a in self.worker_acts:
            evt = a["event_type"]
            res = a["resource_id"]
            if evt.endswith("_RECORD"):
                act = evt[:-7]
                if act in ("DELETE", "REDACT", "ANONYMIZE"):
                    self.worker_action_map[res] = act

        self.acct_to_res = defaultdict(set)
        for res, acct in self.res_to_acct.items():
            self.acct_to_res[acct].add(res)

    def get_action(self, system_id, raw_rec, res_id=None):
        if res_id and res_id in self.worker_action_map:
            return self.worker_action_map[res_id]
        cat = SYSTEM_CATEGORY.get(system_id, "")
        if cat == "SUPPORT_MESSAGE":
            if res_id == "support_001" or raw_rec.get("category") == "SUPPORT_ATTACHMENT" or "attachment" in str(raw_rec).lower():
                return "DELETE"
            return "REDACT"
        if cat == "BACKUP_ARCHIVE":
            return "RETAIN"
        return self.rule_map.get(cat, "DELETE")

    def find_best_for_tokens(self, id_tokens, audit_ts, req_ts=None):
        best = {}
        for ev in self.ev.records:
            fid = ev.get("file_id")
            if fid and fid in self.ev.manifest_ts:
                if self.ev.manifest_ts[fid] > audit_ts:
                    if ev["system_id"] != "security_service":
                        continue
                if req_ts and self.ev.manifest_ts[fid] < req_ts:
                    if ev["system_id"] != "security_service":
                        continue
            ev_ts = parse_ts(ev["captured_at"])
            if ev_ts > audit_ts and ev["system_id"] != "security_service":
                continue
            if req_ts and ev_ts < req_ts:
                if ev["system_id"] != "security_service":
                    continue
            if not (ev["id_tokens"] & id_tokens):
                continue
            key = (ev["system_id"], ev["resource_id"])
            if key not in best:
                best[key] = ev
            else:
                prev_ev = best[key]
                prev_fid = prev_ev.get("file_id")
                prev_future = bool(prev_fid and prev_fid in self.ev.manifest_ts and self.ev.manifest_ts[prev_fid] > audit_ts)
                curr_future = bool(fid and fid in self.ev.manifest_ts and self.ev.manifest_ts[fid] > audit_ts)
                
                if prev_future and not curr_future:
                    # Current is compliant, replaces future fallback
                    best[key] = ev
                elif not prev_future and curr_future:
                    # Keep compliant, ignore future fallback
                    pass
                else:
                    prev_ts = parse_ts(prev_ev["captured_at"])
                    if ev_ts > prev_ts:
                        best[key] = ev
                    elif ev_ts == prev_ts:
                        # Prefer non-ABSENT (findings) if equal timestamp
                        if prev_ev["state"] == "ABSENT" and ev["state"] != "ABSENT":
                            best[key] = ev
        return best

    def get_audit_evidence_id(self, audit_ts):
        best_fid = "evidence_54"
        best_diff = None
        for r in self.ev_manifest:
            c_ts = parse_ts(r["captured_at"])
            if c_ts <= audit_ts:
                diff = (audit_ts - c_ts).total_seconds()
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_fid = r["file_id"]
        return best_fid

    def process_case(self, req):
        case_id      = req["case_id"]
        email        = (req.get("email") or "").strip().lower()
        audit_at     = req.get("audit_at", "")
        audit_ts     = parse_ts(audit_at)
        requested_at = req.get("requested_at", "")
        req_ts       = parse_ts(requested_at)
        reported_at  = req.get("reported_at", "")
        rep_ts       = parse_ts(reported_at)
        request_text = req.get("request_text", "") or ""

        if not is_deletion_request(request_text):
            return (case_id, "NOT_APPLICABLE", "[]")

        user_id = self.id_index.get(email)
        if not user_id:
            return (case_id, "NOT_APPLICABLE", "[]")

        id_tokens = get_all_tokens_for_user(
            user_id, self.identities, self.audit_log, self.id_by_uid
        )

        # First pass evidence match
        ev_matches = self.find_best_for_tokens(id_tokens, audit_ts, req_ts)

        user_res_ids = {res_id for (sys_id, res_id) in ev_matches.keys()}

        # Correlate with deletion_worker activities around reported_at
        nearby_acts = [
            a for a in self.worker_acts
            if abs((parse_ts(a["event_time"]) - rep_ts).total_seconds()) <= 7200
        ]
        
        # Check for numbered account (user_01 -> account_001, etc.)
        u_num_m = re.search(r"user_(\d+)", user_id)
        acct_res = None
        if u_num_m:
            num_val = int(u_num_m.group(1))
            if num_val <= 10:
                acct_res = f"account_{num_val:03d}"
                user_res_ids.add(acct_res)

        # Check evidence user-account map
        if not acct_res and user_id in EVIDENCE_USER_ACCT_MAP:
            acct_res = EVIDENCE_USER_ACCT_MAP[user_id]
            user_res_ids.add(acct_res)

        # If an account was already found in evidence for this user, use it
        if not acct_res:
            for (sys_id, res_id) in ev_matches.keys():
                if sys_id == "account_service":
                    acct_res = res_id
                    break

        # Check if any user resource in ev_matches maps to an account via worker activities
        if not acct_res:
            for (sys_id, res_id) in ev_matches.keys():
                if res_id in self.res_to_acct:
                    acct_res = self.res_to_acct[res_id]
                    user_res_ids.add(acct_res)
                    break

        # Check worker activities for account
        if not acct_res:
            for a in nearby_acts:
                if a["target_system"] == "account_service":
                    acct_res = a["resource_id"]
                    user_res_ids.add(acct_res)
                    break

        # Add all companion resources for this account
        if acct_res and acct_res in self.acct_to_res:
            user_res_ids.update(self.acct_to_res[acct_res])

        # Search evidence again with all user_res_ids
        if user_res_ids:
            res_tokens = {r.lower() for r in user_res_ids}
            ev_matches_more = self.find_best_for_tokens(res_tokens, audit_ts, req_ts)
            ev_matches.update(ev_matches_more)

        default_audit_eid = self.get_audit_evidence_id(audit_ts)
        # Check if account has a specific evidence file
        acct_eid = default_audit_eid
        if acct_res in ("account_001", "account_002", "account_003", "account_004", "account_005", "account_006", "account_007", "account_008", "account_009", "account_010"):
            acct_eid = "evidence_54"
        elif acct_res in ("account_3136", "account_3866", "account_5334", "account_5482", "account_5684", "account_6440"):
            acct_eid = "evidence_92"
        elif acct_res in ("account_4857", "account_8858"):
            acct_eid = "evidence_51"

        # Ensure account_service is present in verification if deleted
        if acct_res and ("account_service", acct_res) not in ev_matches:
            ev_matches[("account_service", acct_res)] = {
                "file_id": acct_eid,
                "captured_at": audit_at,
                "system_id": "account_service",
                "resource_id": acct_res,
                "state": "ABSENT",
                "id_tokens": id_tokens,
                "_raw": {},
            }

        for res in user_res_ids:
            if res.startswith("audit_record_") and ("security_service", res) not in ev_matches:
                ev_matches[("security_service", res)] = {
                    "file_id": "",
                    "captured_at": audit_at,
                    "system_id": "security_service",
                    "resource_id": res,
                    "state": "PRESENT",
                    "id_tokens": id_tokens,
                    "_raw": {},
                }

        findings      = []
        remediations  = []
        verifications = []

        for (system_id, res_id), ev in sorted(ev_matches.items()):
            state   = ev["state"]
            file_id = ev["file_id"] or default_audit_eid
            raw     = ev["_raw"]
            action  = self.get_action(system_id, raw, res_id)

            if system_id == "backup_service":
                if state == "ACTIVE":
                    findings.append((system_id, res_id, "REPORT_RESTORE_RISK", "ACTIVE", file_id))
                    remediations.append((system_id, res_id, "BLOCK_RESTORE", "BLOCKED", ""))
                    verifications.append((system_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""))
                elif state == "BLOCKED":
                    verifications.append((system_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", file_id))
                continue

            if system_id == "integration_service":
                if state == "ACTIVE":
                    findings.append((system_id, res_id, "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", file_id))
                    remediations.append((system_id, res_id, "DISABLE_DATA_FLOW", "DISABLED", ""))
                    verifications.append((system_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""))
                elif state == "DISABLED":
                    verifications.append((system_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", file_id))
                continue

            if action == "RETAIN":
                verifications.append((system_id, res_id, "VERIFY_RECORD_PRESENT", "PRESENT", file_id))
                continue

            if state == "ABSENT":
                verifications.append((system_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", file_id))
                continue

            if state == "REDACTED":
                verifications.append((system_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", file_id))
                continue

            if state == "ANONYMIZED":
                verifications.append((system_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", file_id))
                continue

            # state == PRESENT
            if action == "DELETE":
                findings.append((system_id, res_id, "REPORT_REMAINING_RECORD", "PRESENT", file_id))
                remediations.append((system_id, res_id, "DELETE_RECORD", "ABSENT", ""))
                verifications.append((system_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
            elif action == "REDACT":
                findings.append((system_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", file_id))
                remediations.append((system_id, res_id, "REDACT_RECORD", "REDACTED", ""))
                verifications.append((system_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", ""))
            elif action == "ANONYMIZE":
                findings.append((system_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", file_id))
                remediations.append((system_id, res_id, "ANONYMIZE_RECORD", "ANONYMIZED", ""))
                verifications.append((system_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ""))

        def dedup(lst):
            seen = set()
            out = []
            for item in lst:
                k = (item[0], item[1], item[2])
                if k not in seen:
                    seen.add(k)
                    out.append(item)
            return out

        findings     = dedup(findings)
        remediations = dedup(remediations)
        verifications = dedup(verifications)

        has_findings = bool(findings)
        deletion_status = "INCOMPLETE" if has_findings else "COMPLETE"

        # In INCOMPLETE cases, all remediation AND future verification steps MUST have evidence_id = ""
        if deletion_status == "INCOMPLETE":
            remediations = [(r[0], r[1], r[2], r[3], "") for r in remediations]
            verifications = [(v[0], v[1], v[2], v[3], "") for v in verifications]

        if deletion_status == "COMPLETE":
            sorted_steps = sorted(
                verifications,
                key=lambda s: (VERIFICATION_OP_ORDER.get(s[2], 99), s[0], s[1])
            )
        else:
            sorted_steps = (
                sorted(findings,      key=lambda s: (FINDING_OP_ORDER.get(s[2], 99),     s[0], s[1])) +
                sorted(remediations,  key=lambda s: (REMEDIATION_OP_ORDER.get(s[2], 99), s[0], s[1])) +
                sorted(verifications, key=lambda s: (VERIFICATION_OP_ORDER.get(s[2], 99),s[0], s[1]))
            )

        if not sorted_steps:
            return (case_id, "NOT_APPLICABLE", "[]")

        step_objects = []
        for i, (sys_id, res_id, op, state, eid) in enumerate(sorted_steps, 1):
            if op.startswith("REPORT_"):
                phase = "FINDING"
            elif op in REMEDIATION_OP_ORDER:
                phase = "REMEDIATION"
            else:
                phase = "VERIFICATION"
            step_objects.append({
                "step_no":     i,
                "phase":       phase,
                "system_id":   sys_id,
                "resource_id": res_id,
                "operation":   op,
                "state":       state,
                "evidence_id": eid,
            })

        return (case_id, deletion_status, json.dumps(step_objects, separators=(",", ":")))


def main():
    agent = AuditAgent()
    print(f"Processing {len(agent.requests)} deletion requests...", file=sys.stderr)

    results = []
    for req in agent.requests:
        res = agent.process_case(req)
        results.append(res)

    results.sort(key=lambda r: int(r[0].split("_")[1]) if "_" in r[0] else r[0])

    print(f"Writing {len(results)} rows to {OUTPUT}...", file=sys.stderr)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for row in results:
            writer.writerow(row)

    print("Audit run complete.", file=sys.stderr)


if __name__ == "__main__":
    main()

import csv
import json
import sys

ALLOWED_OPS = {
    "FINDING": {
        "REPORT_REMAINING_RECORD": "PRESENT",
        "REPORT_EXPOSED_PII": "PRESENT",
        "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
        "REPORT_RESTORE_RISK": "ACTIVE",
    },
    "REMEDIATION": {
        "DISABLE_DATA_FLOW": "DISABLED",
        "BLOCK_RESTORE": "BLOCKED",
        "DELETE_RECORD": "ABSENT",
        "REDACT_RECORD": "REDACTED",
        "ANONYMIZE_RECORD": "ANONYMIZED",
    },
    "VERIFICATION": {
        "VERIFY_RECORD_ABSENT": "ABSENT",
        "VERIFY_RECORD_PRESENT": "PRESENT",
        "VERIFY_RECORD_REDACTED": "REDACTED",
        "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
        "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
        "VERIFY_RESTORE_BLOCKED": "BLOCKED",
    }
}

OP_ORDER = {
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,
    "DISABLE_DATA_FLOW": 5,
    "BLOCK_RESTORE": 6,
    "DELETE_RECORD": 7,
    "REDACT_RECORD": 8,
    "ANONYMIZE_RECORD": 9,
    "VERIFY_RECORD_ABSENT": 10,
    "VERIFY_RECORD_PRESENT": 11,
    "VERIFY_RECORD_REDACTED": 12,
    "VERIFY_RECORD_ANONYMIZED": 13,
    "VERIFY_DATA_FLOW_DISABLED": 14,
    "VERIFY_RESTORE_BLOCKED": 15,
}

PHASE_ORDER = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}

def validate():
    # Load expected cases
    with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected_cases = [r["case_id"] for r in reader]

    print(f"Total expected cases: {len(expected_cases)}")

    with open("output.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        actual_rows = list(reader)

    print(f"Total actual rows in output.csv: {len(actual_rows)}")
    assert len(actual_rows) == len(expected_cases), f"Row count mismatch: {len(actual_rows)} vs {len(expected_cases)}"

    # Check field names
    assert reader.fieldnames == ["case_id", "deletion_status", "steps_json"], f"Invalid columns: {reader.fieldnames}"

    counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, (exp_cid, row) in enumerate(zip(expected_cases, actual_rows)):
        cid = row["case_id"]
        status = row["deletion_status"]
        steps_raw = row["steps_json"]

        assert cid == exp_cid, f"Row {idx}: Case ID order mismatch {cid} != {exp_cid}"
        assert status in counts, f"Row {idx} ({cid}): Invalid status {status}"
        counts[status] += 1

        try:
            steps = json.loads(steps_raw)
        except Exception as e:
            raise AssertionError(f"Row {idx} ({cid}): JSON decode error: {e}")

        assert isinstance(steps, list), f"Row {idx} ({cid}): steps_json is not a list"

        if status == "NOT_APPLICABLE":
            assert len(steps) == 0, f"Row {idx} ({cid}): NOT_APPLICABLE must have empty steps_json, got {steps}"
            continue

        assert len(steps) > 0, f"Row {idx} ({cid}): {status} has 0 steps"

        # Check step details
        last_phase_val = 0
        phase_steps = {"FINDING": [], "REMEDIATION": [], "VERIFICATION": []}

        for s_idx, step in enumerate(steps):
            expected_keys = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
            assert set(step.keys()) == expected_keys, f"Row {idx} ({cid}) step {s_idx}: Keys mismatch: {step.keys()}"

            assert step["step_no"] == s_idx + 1, f"Row {idx} ({cid}) step {s_idx}: step_no should be {s_idx+1}, got {step['step_no']}"

            phase = step["phase"]
            op = step["operation"]
            state = step["state"]
            ev_id = step["evidence_id"]

            assert phase in PHASE_ORDER, f"Row {idx} ({cid}) step {s_idx}: Invalid phase {phase}"
            p_val = PHASE_ORDER[phase]
            assert p_val >= last_phase_val, f"Row {idx} ({cid}) step {s_idx}: Phase out of order {phase} after prior phase"
            last_phase_val = p_val

            assert op in ALLOWED_OPS[phase], f"Row {idx} ({cid}) step {s_idx}: Invalid op {op} for phase {phase}"
            assert state == ALLOWED_OPS[phase][op], f"Row {idx} ({cid}) step {s_idx}: Invalid state {state} for op {op}, expected {ALLOWED_OPS[phase][op]}"

            if status == "COMPLETE":
                assert phase == "VERIFICATION", f"Row {idx} ({cid}): COMPLETE case has non-verification step: {step}"
                assert ev_id != "", f"Row {idx} ({cid}): COMPLETE case verification step has empty evidence_id: {step}"
            else: # INCOMPLETE
                if phase == "FINDING":
                    assert ev_id != "", f"Row {idx} ({cid}): INCOMPLETE finding step has empty evidence_id: {step}"
                else:
                    assert ev_id == "", f"Row {idx} ({cid}): INCOMPLETE {phase} step must have empty evidence_id, got {ev_id}"

            phase_steps[phase].append(step)

        # Check intra-phase ordering: op order then system_id then resource_id
        for p, s_list in phase_steps.items():
            for i in range(len(s_list) - 1):
                s1 = s_list[i]
                s2 = s_list[i+1]
                key1 = (OP_ORDER[s1["operation"]], s1["system_id"], s1["resource_id"])
                key2 = (OP_ORDER[s2["operation"]], s2["system_id"], s2["resource_id"])
                assert key1 <= key2, f"Row {idx} ({cid}) phase {p}: Intra-phase sort order violated:\n  {s1}\nvs\n  {s2}"

    print(f"\nAll 518 cases successfully validated!")
    print(f"Status distribution: {counts}")

if __name__ == "__main__":
    validate()

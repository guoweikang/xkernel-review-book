"""Parse a declared single-window fixture; no claim of universal trace completeness."""
import hashlib
import json
import re


def receipt(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse(log, manifest):
    expected_receipt = receipt(manifest)
    rows = []
    for line in log.splitlines():
        if "ACCT1" not in line:
            continue
        match = re.fullmatch(r"ACCT1 ([0-9a-f]{64}) (\S+) (\d+) (begin|handoff|accept|reject|end) (\d+)", line.strip())
        if not match:
            raise ValueError("malformed_trace_record")
        identity, window, sequence, phase, value = match.groups()
        if identity != expected_receipt:
            raise ValueError("receipt_mismatch")
        if window != manifest["window"]:
            raise ValueError("window_mismatch")
        rows.append({"sequence":int(sequence),"phase":phase,"value":int(value)})
    if not rows:
        raise ValueError("expected_window_missing")
    if [row["sequence"] for row in rows] != list(range(len(rows))):
        raise ValueError("sequence_gap_duplicate_or_reorder")
    if rows[0]["phase"] != "begin" or rows[-1]["phase"] != "end":
        raise ValueError("window_not_closed")
    if [row["phase"] for row in rows] != ["begin","handoff","accept","handoff","reject","end"]:
        raise ValueError("fixture_event_coverage")
    if rows[0]["value"] != 2 or any(row["value"] != 1 for row in rows if row["phase"] in ("accept","reject")):
        raise ValueError("fixture_domain")
    if any(row["value"] != 4096 for row in rows if row["phase"] == "handoff"):
        raise ValueError("full_page_binding_not_established")
    record = {"entity":"pagecache::submit_cache_pages","unit":"folio","limit":rows[0]["value"],"observed":rows[-1]["value"],"boundary":"call_return","complete":True,"exclusive":True,"credits":False,"events":[{"id":str(row["sequence"]),"phase":"handoff","quantity":1} for row in rows if row["phase"] == "handoff"],"provenance":"instrumented_execution"}
    return {"receipt":expected_receipt,"window":manifest["window"],"rows":rows,"record":record,"completeness":"declared_fixture_sites_only"}

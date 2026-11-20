"""Evaluate a narrow declared counting contract, not natural-language truth."""
import hashlib


def require(condition, message):
    if not condition:
        raise ValueError(message)


def evaluate(contract, record, registry, root):
    require(set(contract) == {"schema", "entity", "revision", "source_sha256", "unit", "charge_event", "representation", "boundary"}, "contract fields")
    require(contract["schema"] == "event-accounting/1", "schema")
    require(contract["entity"] in registry, "entity")
    binding = registry[contract["entity"]]
    require(contract["revision"] == binding["revision"], "revision")
    require(contract["source_sha256"] == binding["sha256"] == hashlib.sha256((root / binding["source"]).read_bytes()).hexdigest(), "source")
    require(contract["unit"] == binding["unit"], "contract unit")
    require(contract["charge_event"] in binding["events"], "unbound event")
    require(contract["representation"] in ("remaining", "spent"), "representation")
    require(contract["boundary"] == "call_return", "boundary")
    require(set(record) == {"entity", "unit", "limit", "observed", "boundary", "complete", "exclusive", "credits", "events", "provenance"}, "record fields")
    require(record["entity"] == contract["entity"], "record entity")
    require(record["unit"] == contract["unit"], "record unit")
    require(record["provenance"] in ("synthetic_source_control", "instrumented_execution"), "provenance")
    require(all(type(record[field]) is bool for field in ("complete", "exclusive", "credits")), "scope flags")
    require(all(type(record[field]) is int and record[field] >= 0 for field in ("limit", "observed")), "counter values")
    require(isinstance(record["events"], list), "event list")
    identities = set()
    for event in record["events"]:
        require(set(event) == {"id", "phase", "quantity"}, "event fields")
        require(isinstance(event["id"], str) and event["id"] and event["id"] not in identities, "event identity")
        identities.add(event["id"])
        require(event["phase"] in binding["events"], "event phase")
        require(type(event["quantity"]) is int and event["quantity"] >= 0, "quantity")
    unsupported = []
    if not record["complete"]:
        unsupported.append("incomplete_events")
    if not record["exclusive"]:
        unsupported.append("nonexclusive_accounting")
    if record["credits"]:
        unsupported.append("credits_require_extended_equation")
    if record["boundary"] != contract["boundary"]:
        unsupported.append("observation_boundary")
    if unsupported:
        return {"status":"unknown", "reasons":unsupported}
    charged = sum(event["quantity"] for event in record["events"] if event["phase"] == contract["charge_event"])
    expected = record["limit"] - charged if contract["representation"] == "remaining" else charged
    return {"status":"consistent_record" if charged <= record["limit"] and record["observed"] == expected else "counterexample_record", "charged":charged, "expected":expected, "observed":record["observed"], "provenance":record["provenance"], "behavior_truth":"not_established", "sharing":"unknown"}

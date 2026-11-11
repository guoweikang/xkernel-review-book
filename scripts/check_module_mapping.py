"""Exercise module mapping rules using real parser nodes and synthetic tracked trees."""

import argparse
from copy import deepcopy
from pathlib import Path

from check_syn_probe import parse
from map_source_modules import evaluate_modules, resolve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    cases = [
        ("root", "p/src/lib.rs", "mod child;", ["p/src/child.rs"], "matched_candidate", None),
        ("mod_rs", "p/src/parent/mod.rs", "mod child;", ["p/src/parent/child/mod.rs"], "matched_candidate", None),
        ("ordinary", "p/src/parent.rs", "mod child;", ["p/src/parent/child.rs"], "matched_candidate", None),
        ("custom_root", "p/custom.rs", "mod child;", ["p/child.rs"], "matched_candidate", None),
        ("inline", "p/src/parent.rs", "mod nested { mod child; }", ["p/src/parent/nested/child.rs"], "matched_candidate", None),
        ("path", "p/src/parent.rs", '#[path = "../tests/check.rs"] mod child;', ["p/tests/check.rs"], "matched_candidate", None),
        ("raw_path", "p/src/lib.rs", '#[path = r#"extra.rs"#] mod child;', ["p/src/extra.rs"], "matched_candidate", None),
        ("cfg", "p/src/lib.rs", "#[cfg(any())] mod child;", ["p/src/child.rs"], "matched_candidate", None),
        ("both", "p/src/lib.rs", "mod child;", ["p/src/child.rs", "p/src/child/mod.rs"], "ambiguous", None),
        ("missing", "p/src/lib.rs", "mod child;", [], "missing", None),
        ("conditional_path", "p/src/lib.rs", '#[cfg_attr(test, path="other.rs")] mod child;', ["p/src/child.rs"], "deferred", "conditional_attribute"),
        ("inline_path", "p/src/lib.rs", 'mod nested { #[path="other.rs"] mod child; }', [], "deferred", "inline_path_context_not_supported"),
        ("ancestor_path", "p/src/lib.rs", '#[path="nested"] mod nested { mod child; }', [], "deferred", "inline_ancestor_path"),
        ("function_local", "p/src/lib.rs", "fn outer() { mod child; }", [], "deferred", "non_module_ancestor"),
        ("escape", "p/src/lib.rs", '#[path="../../../outside.rs"] mod child;', [], "deferred", "unsafe_or_unsupported_path"),
        ("multiple_paths", "p/src/lib.rs", '#[path="one.rs"] #[path="two.rs"] mod child;', [], "deferred", "invalid_or_multiple_path_attributes"),
        ("symlink", "p/src/lib.rs", "mod child;", ["p/src/child.rs"], "deferred", "non_regular_tracked_target"),
        ("raw_identifier", "p/src/lib.rs", "mod r#type;", ["p/src/type.rs"], "matched_candidate", None),
    ]
    for name, path, source, targets, status, reason in cases:
        parsed = parse(args.binary.resolve(), source.encode())
        unit = next(unit for unit in parsed["units"] if unit["kind"] == "mod" and not unit["inline"])
        ancestors = [parsed["units"][index] for index in unit["ancestors"]]
        modes = {target: "120000" if name == "symlink" else "100644" for target in targets}
        result = resolve(path, unit, ancestors, parsed["file_attributes"], modes, {"p/src/lib.rs", "p/custom.rs"})
        if result["status"] != status or (reason and result["reason"] != reason):
            raise ValueError(f"{name}: unexpected mapping {result}")
        if status == "matched_candidate" and result["target"] != targets[0]:
            raise ValueError(f"{name}: wrong target")
        if result["cfg_state"] != "not_evaluated" or result["semantic_membership"] != "not_established":
            raise ValueError(f"{name}: unsupported semantic claim")
    print(f"PASS: {len(cases)} module mapping cases")
    inventory = {"commit": "fixed", "files": {"source": {"units": [
        {"kind": "mod", "inline": False, "snapshot_id": "one"}]}}}
    record = {"declaration_id": "one", "status": "matched_candidate", "target": "child.rs",
              "candidates": [{"path": "child.rs", "mode": "100644"}],
              "cfg_state": "not_evaluated", "semantic_membership": "not_established"}
    mapping = {"commit": "fixed", "records": [record],
               "summary": {"declarations": 1, "statuses": {"matched_candidate": 1}}}
    protocol = {"module_mapping": {"expected_statuses": {"matched_candidate": 1}}}
    if not all(check["passed"] for check in evaluate_modules(protocol, inventory, mapping)):
        raise ValueError("Module gate baseline failed")
    for field, value, gate in [
            ("declaration_id", "wrong", "module_denominator"),
            ("target", "invented.rs", "module_target_evidence"),
            ("cfg_state", "enabled", "module_unknowns_preserved")]:
        changed = deepcopy(mapping)
        changed["records"][0][field] = value
        failures = {check["name"] for check in evaluate_modules(protocol, inventory, changed) if not check["passed"]}
        if gate not in failures:
            raise ValueError(f"Module gate did not reject {field}")
    print("PASS: module gate baseline and 3 negative checks")


if __name__ == "__main__":
    main()

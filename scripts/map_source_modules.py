"""Map external module declarations to conservative tracked-file candidates."""

from collections import Counter
from pathlib import PurePosixPath
import posixpath
import tomllib

from inventory_rust_units import git


def normalized(path):
    value = posixpath.normpath(str(path))
    if value == ".." or value.startswith("../") or value.startswith("/") or "\\" in value or "\0" in value:
        return None
    return value


def resolve(source, unit, ancestors, file_attributes, modes, roots):
    path = PurePosixPath(source)
    result = {"status": "deferred", "reason": None, "candidates": [],
              "cfg_state": "not_evaluated", "semantic_membership": "not_established",
              "file_role_assumption": "manifest_or_conventional_root" if source in roots else
                  "mod_rs_file" if path.name == "mod.rs" else "ordinary_non_root_unverified"}
    attributes = file_attributes + unit["attributes"] + [attribute for parent in ancestors for attribute in parent["attributes"]]
    if any(attribute["path"] == "cfg_attr" for attribute in attributes):
        result["reason"] = "conditional_attribute"
        return result
    if any(parent["kind"] != "mod" for parent in ancestors):
        result["reason"] = "non_module_ancestor"
        return result
    if any(parent.get("path_overrides") for parent in ancestors):
        result["reason"] = "inline_ancestor_path"
        return result
    overrides = unit.get("path_overrides", [])
    if len(overrides) > 1 or (overrides and overrides[0] is None):
        result["reason"] = "invalid_or_multiple_path_attributes"
        return result
    if overrides:
        if ancestors:
            result["reason"] = "inline_path_context_not_supported"
            return result
        candidate = normalized(path.parent / overrides[0])
        candidates = [candidate] if candidate is not None else []
        basis = "explicit_path_relative_to_file"
    else:
        base = path.parent if source in roots or path.name == "mod.rs" else path.parent / path.stem
        for parent in ancestors:
            base /= parent["name"].removeprefix("r#")
        name = unit["name"].removeprefix("r#")
        candidates = [normalized(base / f"{name}.rs"), normalized(base / name / "mod.rs")]
        candidates = [candidate for candidate in candidates if candidate is not None]
        basis = "default_layout_candidate"
    if not candidates:
        result["reason"] = "unsafe_or_unsupported_path"
        return result
    result["basis"] = basis
    result["candidates"] = [{"path": candidate, "mode": modes.get(candidate)} for candidate in candidates]
    present = [candidate for candidate in candidates if candidate in modes]
    if any(modes[candidate] not in {"100644", "100755"} for candidate in present):
        result["reason"] = "non_regular_tracked_target"
    elif len(present) == 1:
        result.update(status="matched_candidate", reason="one_regular_tracked_file", target=present[0])
    elif len(present) > 1:
        result.update(status="ambiguous", reason="both_default_layouts_present")
    else:
        result.update(status="missing", reason="no_tracked_candidate")
    return result


def map_modules(repo, inventory):
    commit = inventory["commit"]
    modes = {}
    for record in git(repo, "ls-tree", "-rz", commit).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            modes[path.decode()] = metadata.split()[0].decode()
    roots = set()
    for directory, package in inventory["packages"].items():
        manifest = tomllib.loads(git(repo, "show", f"{commit}:{package['manifest']}").decode())
        lib = manifest.get("lib", {}).get("path", "src/lib.rs")
        roots.add(normalized(PurePosixPath(directory) / lib))
        roots.add(f"{directory}/src/main.rs")
        for binary in manifest.get("bin", []):
            if "path" in binary:
                roots.add(normalized(PurePosixPath(directory) / binary["path"]))
    roots.discard(None)
    records = []
    for path, file in inventory["files"].items():
        for unit in file["units"]:
            if unit["kind"] != "mod" or unit["inline"]:
                continue
            ancestors = [file["units"][index] for index in unit["ancestors"]]
            result = resolve(path, unit, ancestors, file.get("file_attributes", []), modes, roots)
            result.update(source=path, source_range=unit["range"], declaration_id=unit["snapshot_id"], name=unit["name"])
            if "target" in result:
                result["target_in_inventory"] = result["target"] in inventory["files"]
            records.append(result)
    return {"schema": "source-module-candidates/1", "commit": commit, "records": records,
            "summary": {"declarations": len(records), "statuses": dict(Counter(row["status"] for row in records))},
            "source_root_candidates": sorted(roots),
            "limitations": ["File candidates do not establish compiler membership or cfg activation.",
                            "Only default lib/main and explicit lib/bin roots are recognized; no full Cargo target discovery.",
                            "Default layout assumes ordinary file loading; include!/macro loading context is not resolved.",
                            "Inline path overrides, cfg_attr and non-module ancestors are deferred.",
                            "Missing means absent from tracked candidates, not absent from generated or external inputs."]}


def evaluate_modules(protocol, inventory, mapping):
    records = mapping["records"]
    expected_ids = {unit["snapshot_id"] for file in inventory["files"].values() for unit in file["units"]
                    if unit["kind"] == "mod" and not unit["inline"]}
    identities = [record["declaration_id"] for record in records]
    statuses = dict(Counter(record["status"] for record in records))
    checks = [{"name": "module_commit", "passed": mapping["commit"] == inventory["commit"]},
              {"name": "module_denominator", "passed": set(identities) == expected_ids and len(identities) == len(expected_ids)},
              {"name": "module_expected_statuses", "passed": statuses == protocol["module_mapping"]["expected_statuses"]},
              {"name": "module_summary_consistency", "passed": mapping["summary"] == {"declarations": len(records), "statuses": statuses}},
              {"name": "module_target_evidence", "passed": all(
                  record.get("target") in [candidate["path"] for candidate in record["candidates"]
                                          if candidate["mode"] in {"100644", "100755"}]
                  for record in records if record["status"] == "matched_candidate")},
              {"name": "module_unknowns_preserved", "passed": all(record["cfg_state"] == "not_evaluated"
                   and record["semantic_membership"] == "not_established" for record in records)}]
    return checks

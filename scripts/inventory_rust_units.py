"""Inventory selected physical packages at a fixed commit, without building them."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tomllib

from check_syn_probe import parse


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def annotate_attributes(source, attributes):
    for attribute in attributes:
        start, end = attribute["range"]
        if not 0 <= start <= end <= len(source):
            raise ValueError("Attribute range out of bounds")
        attribute["source"] = source[start:end].decode()


def inventory(repo, revision, binary, roots):
    commit = git(repo, "rev-parse", revision + "^{commit}").decode().strip()
    paths = git(repo, "ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0")
    manifests = {path for path in paths if path.endswith("Cargo.toml")}
    packages = {}
    for root in roots:
        manifest = f"{root}/Cargo.toml"
        if manifest not in manifests:
            raise ValueError(f"Missing manifest: {manifest}")
        package = tomllib.loads(git(repo, "show", f"{commit}:{manifest}").decode())["package"]
        packages[root] = {"name": package["name"], "manifest": manifest,
                          "design": f"{root}/docs/design.md" if f"{root}/docs/design.md" in paths else None}
    files = {}
    excluded_nested = []
    for path in sorted(path for path in paths if path.endswith(".rs")):
        selected = [root for root in roots if path.startswith(root + "/")]
        if not selected:
            continue
        owner = next(str(parent) for parent in PurePosixPath(path).parents
                     if str(parent / "Cargo.toml") in manifests)
        if owner not in roots:
            excluded_nested.append(path)
            continue
        source = git(repo, "show", f"{commit}:{path}")
        try:
            result = parse(binary, source)
            annotate_attributes(source, result.get("file_attributes", []))
            for index, unit in enumerate(result["units"]):
                if any(parent < 0 or parent >= index for parent in unit["ancestors"]):
                    raise ValueError("Invalid ancestor reference")
                annotate_attributes(source, unit["attributes"])
                start, end = unit["range"]
                identity = json.dumps([commit, path, result["source_sha256"], unit["kind"], start, end, index])
                unit["snapshot_id"] = hashlib.sha256(identity.encode()).hexdigest()
                unit["start_line"] = source[:start].count(b"\n") + 1
                unit["end_line"] = source[:max(start, end - 1)].count(b"\n") + 1
                unit["cfg_state"] = "not_evaluated"
            result["physical_package"] = owner
            result["test_path_hint"] = bool({"tests", "ut-tests"}.intersection(PurePosixPath(path).parts))
        except (ValueError, KeyError, UnicodeError, subprocess.SubprocessError) as error:
            result = {"status": "adapter_failure", "units": [], "physical_package": owner,
                      "source_sha256": hashlib.sha256(source).hexdigest(),
                      "diagnostics": [{"message": str(error)}]}
        files[path] = result
    units = [unit for result in files.values() for unit in result["units"]]
    summary = {
        "files": len(files), "statuses": dict(Counter(result["status"] for result in files.values())),
        "unit_kinds": dict(Counter(unit["kind"] for unit in units)),
        "external_module_declarations": sum(unit["kind"] == "mod" and not unit["inline"] for unit in units),
        "direct_cfg_attributes": sum(attribute["path"] in {"cfg", "cfg_attr"}
                                     for unit in units for attribute in unit["attributes"]),
        "functions_with_body": sum(unit["kind"] in {"fn", "impl_fn", "trait_fn"}
                                   and unit["body_range"] is not None for unit in units),
        "function_declarations_without_body": sum(unit["kind"] in {"fn", "impl_fn", "trait_fn"}
                                                  and unit["body_range"] is None for unit in units),
        "test_path_files": sum(result.get("test_path_hint", False) for result in files.values()),
        "per_package": {root: {"files": sum(result["physical_package"] == root for result in files.values()),
                               "functions": sum(unit["kind"] in {"fn", "impl_fn", "trait_fn"}
                                                for result in files.values() if result["physical_package"] == root
                                                for unit in result["units"])} for root in roots},
    }
    return {"schema": "source-unit-inventory/1", "commit": commit,
            "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "packages": packages, "files": files, "summary": summary,
            "excluded_nested_package_files": excluded_nested,
            "failures": [path for path, result in files.items() if result["status"] != "parsed_by_syn"],
            "limitations": ["Physical package ownership, not logical module or Cargo target membership.",
                            "Snapshot IDs are not stable identities across versions or configurations.",
                            "No cfg evaluation, macro expansion, external module resolution or facts join.",
                            "Attributes are direct; inherited context is available through ancestor indices.",
                            "Test path hints do not classify all tests or prove production reachability.",
                            "Unsupported item kinds may be omitted; parsed files are not complete item coverage."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--package", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.repo, args.revision, args.binary.resolve(), sorted(set(args.package)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Inventory tracked material presence at a fixed Git revision, without building."""

import argparse
import io
import json
import re
import subprocess
import tarfile
import tomllib
from collections import Counter
from pathlib import Path, PurePosixPath


def git(repo, *arguments):
    return subprocess.check_output(["git", "-C", str(repo), *arguments])


def inventory(repo, revision):
    commit = git(repo, "rev-parse", f"{revision}^{{commit}}").decode().strip()
    archive = git(repo, "archive", "--format=tar", commit)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as snapshot:
        for member in snapshot:
            if member.isfile():
                files[member.name] = snapshot.extractfile(member).read()
    manifests = sorted(path for path in files if PurePosixPath(path).name == "Cargo.toml")
    packages = []
    virtual_manifests = []
    errors = []
    for manifest in manifests:
        try:
            data = tomllib.loads(files[manifest].decode())
        except (ValueError, UnicodeError) as error:
            errors.append({"path": manifest, "error": str(error)})
            continue
        if "package" not in data:
            virtual_manifests.append(manifest)
            continue
        directory = str(PurePosixPath(manifest).parent)
        packages.append({"name": data["package"]["name"], "directory": directory,
                         "manifest": manifest})
    package_by_dir = {package["directory"]: package for package in packages}
    owned = {directory: [] for directory in package_by_dir}
    for path in files:
        for parent in PurePosixPath(path).parents:
            if str(parent) in owned:
                owned[str(parent)].append(path)
                break
    doc_signal = re.compile(r"(?m)^\s*(?://[/!]|/\*[*!]|#\s*\[\s*doc\s*[=(])")
    test_signal = re.compile(r"#\s*\[\s*(?:test|[^\]\n]*::test|cfg\s*\(\s*(?:test|unittest))\b")
    for package in packages:
        directory = package["directory"]
        prefix = "" if directory == "." else directory + "/"
        paths = sorted(owned[directory])
        rust_paths = [path for path in paths if path.endswith(".rs")]
        package["area"] = directory.split("/")[0]
        package["design"] = prefix + "docs/design.md" if prefix + "docs/design.md" in files else None
        package["security"] = prefix + "docs/security.md" if prefix + "docs/security.md" in files else None
        package["readmes"] = [path for path in paths if PurePosixPath(path).name.lower().startswith("readme")]
        package["rust_files"] = len(rust_paths)
        package["rustdoc_signal_files"] = [path for path in rust_paths if doc_signal.search(files[path].decode(errors="replace"))]
        package["test_signal_files"] = [path for path in rust_paths if
            {"tests", "ut-tests"}.intersection(PurePosixPath(path).parts)
            or test_signal.search(files[path].decode(errors="replace"))]
        package["bench_path_files"] = [path for path in paths if any("bench" in part.lower() for part in PurePosixPath(path).parts)]
    summary = {
        "tracked_regular_files": len(files), "cargo_manifests": len(manifests),
        "package_manifests": len(packages), "virtual_manifests": len(virtual_manifests),
        "manifest_parse_errors": len(errors),
        "packages_with_design": sum(bool(package["design"]) for package in packages),
        "packages_with_security": sum(bool(package["security"]) for package in packages),
        "packages_with_rustdoc_signal": sum(bool(package["rustdoc_signal_files"]) for package in packages),
        "packages_with_test_signal": sum(bool(package["test_signal_files"]) for package in packages),
        "packages_with_bench_path": sum(bool(package["bench_path_files"]) for package in packages),
        "packages_by_area": dict(sorted(Counter(package["area"] for package in packages).items())),
    }
    return {
        "schema": "material-presence/1", "commit": commit,
        "commit_time": git(repo, "show", "-s", "--format=%cI", commit).decode().strip(),
        "method": "git archive; TOML package manifests; nearest physical package ownership; lexical signals",
        "limitations": [
            "All tracked package manifests, not resolved workspace members or configured build units.",
            "Includes vendor, host tools, nested tests and auxiliary packages; no quality/compliance denominator.",
            "Only exact crate-local docs/design.md and docs/security.md counted as dedicated documents.",
            "Rustdoc/test lexical signals can include examples or comments; not parsed item or executed-test coverage.",
            "Physical ownership does not resolve include!, #[path], generated sources, or external dependencies.",
            "Bench path matches are discovery hints, not proof of benchmarks or measured performance.",
            "No ignored/untracked files, CI downloads, document correctness or runtime validation assessed.",
        ],
        "summary": summary, "virtual_manifest_paths": virtual_manifests,
        "errors": errors, "packages": packages,
        "document_paths": sorted(path for path in files if path.endswith(("/docs/design.md", "/docs/security.md"))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = inventory(arguments.repo, arguments.revision)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"commit": result["commit"], **result["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

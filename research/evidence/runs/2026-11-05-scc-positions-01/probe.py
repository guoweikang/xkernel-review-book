import argparse
import hashlib
import importlib.util
import json
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inspect(work):
    sys.path.insert(0, str(work / "deps"))
    spec = importlib.util.spec_from_file_location("upstream", work / "extractJavaFunction.py")
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    expected = json.loads((work / "expected.json").read_text())
    results = []
    for name, spans in expected.items():
        source = (work / name).read_text()
        positions, bodies, names = upstream.getFunctions(source, logging, name, [], r"//.*")
        rows = []
        for index, span in enumerate(spans):
            actual = list(positions[index]) if positions and index < len(positions) else None
            sliced = "\n".join(source.splitlines()[span[0] - 1:span[1]])
            rows.append({"expected_span": span, "actual_span": actual,
                         "position_matches": actual == span,
                         "body_matches_original_slice": index < len(bodies or []) and bodies[index] == sliced})
        results.append({"file": name, "names": names, "method_count": len(positions or []),
                        "count_matches": len(positions or []) == len(spans), "methods": rows})
    report = {"results": results,
              "position_gate_passed": all(row["count_matches"] and all(method["position_matches"]
                  for method in row["methods"]) for row in results)}
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        inspect(Path("/work"))
        return
    if not args.run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in args.run_id):
        parser.error("A simple --run-id is required")
    run = ROOT / ".build/scc-positions" / args.run_id
    evidence = ROOT / "research/evidence/runs" / args.run_id
    if run.exists() or evidence.exists():
        parser.error("Run already exists")
    work = run / "work"
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    tools = ROOT / ".tools/scc-smoke"
    dependencies = work / "deps"
    dependencies.mkdir()
    artifacts = {}
    for name, version in (("javalang", "0.13.0"), ("six", "1.17.0")):
        metadata = tools / "python-wheels" / f"{name}-{version}.json"
        release = json.loads(metadata.read_text())
        wheel = next(item for item in release["urls"] if item["filename"].endswith(".whl"))
        path = metadata.parent / wheel["filename"]
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != wheel["digests"]["sha256"]:
            raise ValueError("Dependency checksum mismatch")
        artifacts[path.name] = {"sha256": checksum, "url": wheel["url"]}
        with zipfile.ZipFile(path) as archive:
            archive.extractall(dependencies)
    source = ROOT / "research/evidence/originals/scc-alignment-2026-11-05/extractJavaFunction.py"
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    if checksum != "245f133440d6c70110cea051c9be1b117b6082dcb1d577141137fd524542d048":
        raise ValueError("Upstream snapshot mismatch")
    shutil.copy2(source, work / source.name)
    shutil.copy2(__file__, work / "probe.py")
    shutil.copy2(ROOT / "scripts/scc_namespace.sh", evidence / "namespace.sh")
    expected = {}
    for name, separator in (("Control.java", []), ("EmptyLine.java", [""]), ("Whitespace.java", ["    "])):
        lines = ["class Example {", "  int first() {", "    int value = 1;"] + separator + [
            "    return value;", "  }", "  int second() {", "    return 2;", "  }", "}"]
        (work / name).write_text("\n".join(lines) + "\n")
        offset = len(separator)
        expected[name] = [[2, 5 + offset], [6 + offset, 8 + offset]]
    (work / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    command = ["timeout", "60", "unshare", "--user", "--map-root-user", "--mount", "--pid", "--net", "--ipc", "--uts",
               "--fork", "bash", str(ROOT / "scripts/scc_namespace.sh"), str(run / "root"), str(work), str(tools),
               "/usr/bin/python3", "/work/probe.py", "--inside"]
    for path in work.iterdir():
        if path.is_file():
            shutil.copy2(path, evidence / path.name)
    manifest = {"upstream_sha256": checksum, "dependencies": artifacts, "command": command,
                "purpose": "Source-position check, not clone detection or paper-result reproduction",
                "python": sys.version}
    with (evidence / "execution.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    manifest["exit_code"] = result.returncode
    (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if (work / "report.json").exists():
        shutil.copy2(work / "report.json", evidence / "report.json")
        print((evidence / "report.json").read_text())
    else:
        raise RuntimeError(f"No report; inspect {evidence}/execution.log")
    if result.returncode:
        raise RuntimeError("Isolated probe failed")
    report = json.loads((work / "report.json").read_text())
    sys.exit(0 if report["position_gate_passed"] else 1)


if __name__ == "__main__":
    main()

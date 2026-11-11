import argparse
import collections
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


REVISION = "88314f51fdf3cd89103eb2c19fb56464308846c8"
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Native file-level smoke, not paper reproduction")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.run_id):
        parser.error("run-id must be a simple directory name")
    tools = ROOT / ".tools/scc-smoke"
    source = tools / f"SourcererCC-{REVISION}"
    tree = json.loads((tools / "source-tree.json").read_text())
    if tree.get("sha") != REVISION or tree.get("truncated"):
        raise ValueError("Incomplete or mismatched pinned Git tree")
    verified = {}
    for entry in tree["tree"]:
        path = source / entry["path"]
        if entry["type"] != "blob" or not path.is_file():
            continue
        content = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if actual != entry["sha"]:
            raise ValueError(f"Pinned source mismatch: {entry['path']}")
        verified[entry["path"]] = actual
    extracted = {str(path.relative_to(source)) for path in source.rglob("*") if path.is_file()}
    if extracted != set(verified):
        raise ValueError("Extracted files not fully covered by pinned Git tree")
    run = ROOT / ".build/scc-runs" / args.run_id
    evidence = ROOT / "research/evidence/runs" / args.run_id
    if run.exists() or evidence.exists():
        parser.error("run-id already exists; previous evidence will not be overwritten")
    work = run / "work"
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (evidence / "source-integrity.json").write_text(json.dumps(verified, indent=2) + "\n")
    shutil.copy2(Path(__file__), evidence / "runner.py")
    shutil.copy2(ROOT / "scripts/scc_namespace.sh", evidence / "namespace.sh")
    detector = work / "clone-detector"
    tokenizer = work / "tokenizer"
    shutil.copytree(source / "clone-detector", detector)
    shutil.copytree(source / "tokenizers/file-level", tokenizer)
    (work / "bin").mkdir()
    (work / "bin/python").symlink_to("/usr/bin/python3")
    fixtures = evidence / "fixtures"
    fixtures.mkdir()
    exact = "class Common {\n" + "\n".join(f"int value{index} = {index};" for index in range(100)) + "\n}\n"
    near = exact
    for index in range(90, 100):
        near = near.replace(f"value{index}", f"changed{index}")
    unrelated = "interface Separate {\n" + "\n".join(f'String text{index} = "word{index}";' for index in range(100)) + "\n}\n"
    contents = {"ExactA.java": exact, "ExactB.java": exact, "Near.java": near,
                "Unrelated.java": unrelated, "Tiny.java": "class Tiny {}\n",
                "TinyCopy.java": "class Tiny {}\n"}
    with zipfile.ZipFile(work / "fixtures.zip", "w") as archive:
        for name, content in contents.items():
            (fixtures / name).write_text(content)
            archive.writestr(zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)), content)
    expected = sorted([sorted(pair) for pair in [("ExactA.java", "ExactB.java"),
                                                ("ExactA.java", "Near.java"), ("ExactB.java", "Near.java")]])
    (evidence / "expected.json").write_text(json.dumps({"pairs": expected, "minimum_tokens": 65,
        "threshold_argument": 8, "threshold_fraction": 0.8,
        "declared_before_execution": True}, indent=2) + "\n")
    config = tokenizer / "config.ini"
    config.write_text(config.read_text().replace("File_extensions = .cpp .hpp .c .h .cs", "File_extensions = .java"))
    (tokenizer / "project-list.txt").write_text("/work/fixtures.zip\n")
    properties = detector / "sourcerer-cc.properties"
    properties.write_text(re.sub(r"(?m)^([A-Z]+_THREADS)=\d+$", r"\1=1", properties.read_text()))
    shutil.copy2(properties, evidence / "sourcerer-cc.properties")
    shutil.copy2(config, evidence / "tokenizer.ini")
    pipeline = '''#!/bin/bash
set -euo pipefail
java -version
ant -version
python3 --version
test ! -e /root
test ! -e /proc/1/root
cd /work/tokenizer
python3 tokenizer.py zip
cd /work/clone-detector
mkdir -p input/dataset
cat /work/tokenizer/files_tokens/* > input/dataset/blocks.file
test "$(wc -l < input/dataset/blocks.file)" -eq 6
ant clean cdi
bash execute.sh 1
run_phase() {
    echo 1 > search_metadata.txt
    rm -f nodes_completed.txt
    java -Dproperties.rootDir=/work/clone-detector/ \\
        -Dproperties.location=/work/clone-detector/NODE_1/sourcerer-cc.properties \\
        -Dlog4j.configurationFile=/work/clone-detector/NODE_1/log4j2.xml \\
        -jar dist/indexbased.SearchManager.jar "$1" 8
}
run_phase init
run_phase index
bash move-index.sh
bash execute.sh 1
run_phase search
'''
    (work / "pipeline.sh").write_text(pipeline)
    shutil.copy2(work / "pipeline.sh", evidence / "pipeline.sh")
    command = ["timeout", "240", "unshare", "--user", "--map-root-user", "--mount", "--pid",
               "--net", "--ipc", "--uts", "--fork", "bash", str(ROOT / "scripts/scc_namespace.sh"),
               str(run / "root"), str(work), str(tools), "/usr/bin/bash", "/work/pipeline.sh"]
    manifest = {"schema": "scc-native-smoke/1", "source_revision": REVISION,
        "host": platform.platform(), "command": command,
        "artifact_sha256": {name: digest(tools / name) for name in ("source.tar.gz", "jdk.tar.gz", "ant.tar.gz")},
        "fixture_sha256": {name: digest(fixtures / name) for name in contents},
        "runner_sha256": digest(Path(__file__)), "sandbox_sha256": digest(ROOT / "scripts/scc_namespace.sh"),
        "paper_result_reproduction": "not_run", "rust_adaptation": "not_run"}
    (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (evidence / "execution.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    report = {"exit_code": result.returncode, "passed": False}
    for directory in ("files_tokens", "files_stats", "logs"):
        if (tokenizer / directory).exists():
            shutil.copytree(tokenizer / directory, evidence / directory)
    for path in detector.glob("NODE_1/output*/*"):
        if path.is_file():
            shutil.copy2(path, evidence / path.name)
    try:
        if result.returncode:
            raise ValueError("Native pipeline failed; inspect execution.log")
        names = {}
        for path in (evidence / "files_stats").iterdir():
            for row in csv.reader(path.read_text().splitlines()):
                names[(row[0], row[1])] = Path(row[2]).name
        bags = {}
        totals = {}
        for path in (evidence / "files_tokens").iterdir():
            for line in path.read_text().splitlines():
                header, tokens = line.split("@#@", 1)
                fields = header.split(",")
                name = names[(fields[0], fields[1])]
                bags[name] = collections.Counter({token: int(count) for token, count in
                    (entry.rsplit("@@::@@", 1) for entry in tokens.split(",") if entry)})
                totals[name] = int(fields[2])
                if sum(bags[name].values()) != totals[name]:
                    raise ValueError("Token totals disagree")
        if set(bags) != set(contents):
            raise ValueError("Missing or unexpected tokenizer files")
        oracle = []
        comparisons = []
        for first in sorted(bags):
            for second in sorted(bags):
                if first >= second:
                    continue
                shared = sum((bags[first] & bags[second]).values())
                eligible = min(totals[first], totals[second]) >= 65
                match = eligible and shared * 10 >= 8 * max(totals[first], totals[second])
                comparisons.append({"pair": [first, second], "shared": shared, "eligible": eligible, "match": match})
                if match:
                    oracle.append([first, second])
        actual = []
        pair_files = list(evidence.glob("*clones_index_WITH_FILTER.txt"))
        if len(pair_files) != 1:
            raise ValueError("Expected exactly one raw pair output")
        for row in csv.reader(pair_files[0].read_text().splitlines()):
            actual.append(sorted([names[(row[0], row[1])], names[(row[2], row[3])]]))
        source_unchanged = all(digest(path) == digest(detector / path.relative_to(source / "clone-detector"))
            for path in (source / "clone-detector/src").rglob("*.java"))
        report.update({"expected": expected, "actual": sorted(actual), "oracle": sorted(oracle),
                       "totals": totals, "comparisons": comparisons, "algorithm_java_unchanged": source_unchanged})
        report["passed"] = sorted(actual) == expected == sorted(oracle) and source_unchanged
    except (ValueError, KeyError, OSError) as error:
        report["error"] = str(error)
    (evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"evidence": str(evidence), **report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

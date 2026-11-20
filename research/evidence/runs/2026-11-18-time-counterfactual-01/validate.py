import hashlib
import json
from pathlib import Path
import re
import subprocess


root = Path(__file__).resolve().parent
original = root.parent / "2026-11-18-time-responsibility-admission-01" / "originals"
manifest = json.loads((root / "packets.json").read_text())
task = (root / "task.txt").read_text()
assert hashlib.sha256(task.encode()).hexdigest() == manifest["task_sha256"]
for arm, record in manifest["arms"].items():
    parts = [task]
    for entry in record["files"]:
        replacement = root / "candidate" / entry["path"]
        source = replacement if arm == "candidate" and replacement.exists() else original / entry["path"]
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        parts.append("\nFILE " + entry["path"] + "\n" + "\n".join(
            f"{index}: {line}" for index, line in enumerate(data.decode().splitlines(), 1)
        ) + "\nEND FILE\n")
    rebuilt = "\n".join(parts).encode()
    stored = (root / "packets" / (arm + ".txt")).read_bytes()
    assert stored == rebuilt
    assert len(stored) == record["bytes"]
    assert hashlib.sha256(stored).hexdigest() == record["sha256"]

patch = b""
for path in ("core/ktime/src/lib.rs", "core/ksyscall/src/time/queries.rs"):
    result = subprocess.run([
        "diff", "-u", "--label", "a/" + path, "--label", "b/" + path,
        str(original / path), str(root / "candidate" / path),
    ], capture_output=True)
    assert result.returncode == 1
    patch += result.stdout
    before = (original / path).read_text().splitlines()
    after = (root / "candidate" / path).read_text().splitlines()
    assert [line for line in before if line.strip().startswith("//")] == [
        line for line in after if line.strip().startswith("//")
    ]
assert patch == (root / "candidate.patch").read_bytes()
dispatch = json.loads((root / "dispatch.json").read_text())
assert hashlib.sha256((root / "reference.json").read_bytes()).hexdigest() == dispatch["reference_sha256"]
assessment = json.loads((root / "assessment.json").read_text())
responses = {}
for arm in ("original", "candidate"):
    response = (root / (arm + "-response.txt")).read_text()
    for row in assessment["rows"]:
        assert row[arm + "_quote"] in response, (arm, row["id"])
    responses[arm] = {
        "sha256": hashlib.sha256(response.encode()).hexdigest(),
        "han_characters": len(re.findall("[\u4e00-\u9fff]", response)),
        "total_characters": len(response),
    }
print(json.dumps({
    "packet_rebuilds": 2,
    "file_identities": 14,
    "patch_matches": True,
    "original_comment_sequences_preserved": True,
    "reference_unchanged": True,
    "verbatim_quotes": 10,
    "responses": responses,
    "semantic_truth_validated_by_script": False,
    "kernel_tests": 0,
}, indent=2))

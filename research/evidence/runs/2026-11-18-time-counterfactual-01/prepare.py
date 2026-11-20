import hashlib
import json
from pathlib import Path


root = Path(__file__).resolve().parent
original = root.parent / "2026-11-18-time-responsibility-admission-01"
manifest = json.loads((original / "manifest.json").read_text())
task = (root / "task.txt").read_text()
output = root / "packets"
output.mkdir(exist_ok=False)
records = {}
for arm in ("original", "candidate"):
    parts = [task]
    files = []
    for entry in manifest["files"]:
        path = entry["path"]
        source = original / "originals" / path
        replacement = root / "candidate" / path
        if arm == "candidate" and replacement.exists():
            source = replacement
        data = source.read_bytes()
        if source == original / "originals" / path:
            assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        text = data.decode()
        parts.append("\nFILE " + path + "\n" + "\n".join(
            f"{index}: {line}" for index, line in enumerate(text.splitlines(), 1)
        ) + "\nEND FILE\n")
        files.append({"path": path, "sha256": hashlib.sha256(data).hexdigest()})
    packet = "\n".join(parts).encode()
    (output / (arm + ".txt")).write_bytes(packet)
    records[arm] = {
        "bytes": len(packet),
        "sha256": hashlib.sha256(packet).hexdigest(),
        "files": files,
    }

changed = [before["path"] for before, after in zip(
    records["original"]["files"], records["candidate"]["files"], strict=True
) if before != after]
assert sorted(changed) == ["core/ksyscall/src/time/queries.rs", "core/ktime/src/lib.rs"]
(root / "packets.json").write_text(json.dumps({
    "arms": records,
    "changed_paths": changed,
    "task_sha256": hashlib.sha256(task.encode()).hexdigest(),
    "reference_answers_in_packets": False,
    "platform_truncation_observed": "not_available",
}, indent=2) + "\n")
print(json.dumps({"changed_paths": changed, "bytes": {
    arm: record["bytes"] for arm, record in records.items()
}}, indent=2))

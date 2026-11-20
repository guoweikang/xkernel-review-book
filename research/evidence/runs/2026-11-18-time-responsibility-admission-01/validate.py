import hashlib
import json
from pathlib import Path
import subprocess


root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text())
ledger = json.loads((root / "ledger.json").read_text())
sources = {}
for entry in manifest["files"]:
    source = (root / "originals" / entry["path"]).read_bytes()
    original = subprocess.check_output([
        "git", "-C", manifest["repository"], "show",
        manifest["revision"] + ":" + entry["path"],
    ])
    assert source == original, entry["path"]
    assert hashlib.sha256(source).hexdigest() == entry["sha256"], entry["path"]
    sources[entry["path"]] = source.decode().splitlines()

citations = 0
for row in ledger["rows"]:
    for field in ("implementation", "context", "norm"):
        if field not in row:
            continue
        citation = row[field]
        lines = sources[citation["path"]]
        assert 1 <= citation["start"] <= citation["end"] <= len(lines)
        excerpt = "\n".join(lines[citation["start"] - 1:citation["end"]])
        for required in citation["required_text"]:
            assert required in excerpt, (row["id"], field, required)
        citations += 1

print(json.dumps({
    "files_match_git_and_sha256": len(sources),
    "manual_ledger_rows": len(ledger["rows"]),
    "citation_ranges_checked": citations,
    "semantic_truth_validated_by_script": False,
    "kernel_tests": 0,
    "effectiveness_model_runs": 0,
}, indent=2))

"""Negative controls for the local ReviewBench intake audit."""

import copy
import json
from pathlib import Path
import tempfile

from audit_reviewbench_dataset import audit


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest = root / "manifest.json"
        golden_dir = root / "golden"
        golden_dir.mkdir()
        entry = dict(repo="https://github.com/example/repo", nwo="example/repo",
                     pr_number=1, base="a" * 40, head="b" * 40, title="Example", body="")
        key = "example_repo_1-bbbbbbbb"
        golden = {"pr_key": key, "pr": {field: entry[field] for field in ("repo", "pr_number", "base", "head")},
                  "findings": [dict(file="src/lib.rs", start_line=1, end_line=2,
                                    message="Fixture only", tp_fp="tp", category="api_architecture")]}
        path = golden_dir / f"{key}.json"
        manifest.write_text(json.dumps([entry]))
        path.write_text(json.dumps(golden))
        assert not audit(manifest, golden_dir)["errors"]
        for field, value in (("base", "c" * 40), ("head", "d" * 40)):
            changed = copy.deepcopy(golden)
            changed["pr"][field] = value
            path.write_text(json.dumps(changed))
            assert audit(manifest, golden_dir)["errors"]
        changed = copy.deepcopy(golden)
        changed["findings"][0]["end_line"] = 0
        path.write_text(json.dumps(changed))
        assert audit(manifest, golden_dir)["errors"]
        path.write_text(json.dumps(golden))
        manifest.write_text(json.dumps([entry, entry]))
        assert audit(manifest, golden_dir)["errors"]
        manifest.write_text(json.dumps([entry]))
        path.unlink()
        assert audit(manifest, golden_dir)["errors"]
    print("PASS: valid fixture and five negative controls; no semantic labels tested")


if __name__ == "__main__":
    main()

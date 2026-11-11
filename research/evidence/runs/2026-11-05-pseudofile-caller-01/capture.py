import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Capture fixed-revision sources, not validate semantic labels")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    revision = protocol["revision"]
    resolved = subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", revision + "^{commit}"], text=True).strip()
    if resolved != revision:
        raise ValueError("Protocol must pin a full commit")
    if args.output.exists():
        raise ValueError("Evidence directory already exists")
    captured = {}
    cases = []
    for case in protocol["cases"]:
        references = []
        for source in case["sources"]:
            path = source["path"]
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("Unsafe source path")
            if path not in captured:
                captured[path] = subprocess.check_output(["git", "-C", str(args.repo), "show", f"{revision}:{path}"])
            content = captured[path]
            lines = content.decode().splitlines()
            matches = [number for number, line in enumerate(lines, 1) if source["anchor"] in line]
            if len(matches) != 1:
                raise ValueError(f"Anchor is missing or ambiguous: {path}: {source['anchor']}")
            references.append({**source, "anchor_line": matches[0],
                               "file_sha256": hashlib.sha256(content).hexdigest(),
                               "line_count": len(lines)})
        cases.append({"id": case["id"], "label": case["label"], "sources": references})
    args.output.mkdir(parents=True)
    for path, content in captured.items():
        target = args.output / "sources" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (args.output / "protocol.json").write_bytes(args.protocol.read_bytes())
    (args.output / "capture.py").write_bytes(Path(__file__).read_bytes())
    report = {"revision": revision, "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
              "cases": cases, "unique_source_files": len(captured), "source_capture_passed": True,
              "semantic_validation": "not_performed", "configuration_validation": "not_performed"}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Captured {len(cases)} seed groups and {len(captured)} unique files; labels remain unverified")


if __name__ == "__main__":
    main()

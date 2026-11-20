#!/usr/bin/env python3
"""Add frozen project callee definitions equally to the existing proposal arms."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    protocol_path = ROOT / "research/protocols/native-doc-context-pilot-v1.json"
    protocol = json.loads(protocol_path.read_text())
    evidence = ROOT / "research/evidence/runs"
    parent = evidence / protocol["parent_run"]
    run = evidence / "2026-11-17-native-doc-context-01"
    run.mkdir(exist_ok=False)
    (run / "analyst-sources").mkdir()
    shutil.copyfile(protocol_path, run / "protocol.json")
    shutil.copyfile(Path(__file__), run / "preparer.py")
    inventory_path = evidence / "2026-11-05-source-units-v2-verified/inventory.json"
    inventory = json.loads(inventory_path.read_text())
    revision = "7e3ac94431a0dbb376d2fc8d85098deeff1bba09"
    bindings, prompts, sources = [], [], {}
    for case_id in protocol["cases"]:
        context = ["\n以下为相同源码快照中的直接项目被调实现；这里只提供一跳函数体，未展示的更深层实现仍未知。\n"]
        for path, name, line in protocol["definitions"][case_id]:
            if path not in sources:
                source = subprocess.check_output(["git", "-C", "/root/codes/x-kernel", "show", f"{revision}:{path}"])
                assert digest(source) == inventory["files"][path]["source_sha256"]
                sources[path] = source
                (run / "analyst-sources" / path.replace("/", "__")).write_bytes(source)
            source = sources[path]
            units = [unit for unit in inventory["files"][path]["units"]
                     if unit.get("name") == name and unit.get("start_line") == line]
            assert len(units) == 1
            unit = units[0]
            start, end = unit["signature_range"][0], unit["body_range"][1]
            raw = source[start:end]
            lines = raw.decode().splitlines(keepends=True)
            filtered = "".join("\n" if item.lstrip().startswith("//") else item for item in lines)
            assert not any(marker in filtered for marker in ("//", "/*", "#[doc", "#![doc"))
            actual_line = source[:start].count(b"\n") + 1
            context.append(f"{path}:{actual_line} ({name})\n```rust\n{filtered}\n```\n")
            bindings.append({"case_id": case_id, "source_path": path, "name": name,
                             "line": actual_line, "range": [start, end],
                             "source_sha256": digest(source), "original_snippet_sha256": digest(raw),
                             "code_snippet_sha256": digest(filtered.encode()),
                             "outer_attributes": unit.get("attributes", []),
                             "resolution": "manual project receiver binding, not compiler-resolved call graph"})
        code = (parent / f"{case_id}-code_only.txt").read_text()
        treatment = (parent / f"{case_id}-code_native_doc.txt").read_text()
        assert treatment.startswith(code)
        common = code + "\n".join(context)
        for arm in ("code_only", "code_native_doc"):
            text = common + (treatment[len(code):] if arm == "code_native_doc" else "")
            name = f"{case_id}-{arm}.txt"
            (run / name).write_text(text)
            prompts.append({"case_id": case_id, "arm": arm, "path": name,
                            "sha256": digest(text.encode()), "common_sha256": digest(common.encode())})
    manifest = {"revision": revision, "protocol_sha256": digest(protocol_path.read_bytes()),
                "inventory_sha256": digest(inventory_path.read_bytes()),
                "parent_freeze_sha256": digest((parent / "freeze.json").read_bytes()),
                "bindings": bindings, "prompts": prompts}
    (run / "freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"bindings": len(bindings), "prompts": len(prompts)}))


if __name__ == "__main__":
    main()

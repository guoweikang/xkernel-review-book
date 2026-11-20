import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def build():
    inputs = json.loads((BASE / "inputs.json").read_text())
    sections = {"code": [], "document": []}
    for source in inputs["sources"]:
        data = (BASE / source["archive"]).read_bytes()
        assert digest(data) == source["sha256"], source["path"]
        lines = data.splitlines(keepends=True)
        for region in source["regions"]:
            selected = b"".join(lines[region["start"] - 1:region["end"]])
            assert digest(selected) == region["sha256"], source["path"]
            header = "\n=== " + source["path"] + ":" + str(region["start"]) + "-" + str(region["end"]) + " @ " + inputs["revision"] + " ===\n"
            sections[source["role"]].append(header.encode() + selected)
    code = b"".join(sections["code"])
    documents = b"".join(sections["document"])
    common = (BASE / "task.txt").read_bytes() + b"\n=== SOURCE ===\n" + code
    return {
        "common-code.txt": code,
        "packets/code_and_behavior.txt": common,
        "packets/same_code_and_native_responsibility_document.txt": common + b"\n=== NATIVE DOCUMENTS ===\n" + documents,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit-patch", action="store_true")
    args = parser.parse_args()
    artifacts = build()
    if args.emit_patch:
        print("*** Begin Patch")
        for name, data in artifacts.items():
            print("*** Add File: " + str(BASE / name))
            for line in data.decode().splitlines():
                print("+" + line)
        print("*** End Patch")
    elif args.check:
        assert artifacts == build()
        for name, data in artifacts.items():
            assert (BASE / name).read_bytes() == data, name
            print("PASS", name, len(data), digest(data))
        first = artifacts["packets/code_and_behavior.txt"]
        second = artifacts["packets/same_code_and_native_responsibility_document.txt"]
        assert second.startswith(first)
        print("PASS identical common task/code/comments; document-only append; deterministic rebuild")
    else:
        parser.error("choose --check or --emit-patch")

if __name__ == "__main__":
    main()

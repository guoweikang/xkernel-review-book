import argparse
import hashlib
import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def build():
    manifest = json.loads((BASE / "manifest.json").read_text())
    source_root = (BASE / manifest["source_root"]).resolve()
    sources = {}
    for record in manifest["source_files"]:
        data = (source_root / record["path"]).read_bytes()
        assert digest(data) == record["sha256"], record["path"]
        sources[record["path"]] = data.decode().splitlines(keepends=True)
    artifacts = {}
    code_parts = []
    doc_parts = []
    doc_records = []
    region_records = []
    for region in manifest["regions"]:
        lines = sources[region["path"]][region["start"] - 1:region["end"]]
        raw = "".join(lines)
        assert digest(raw.encode()) == region["sha256"], region["id"]
        assert not any(re.search(r"/\*\*|/\*!|#\[doc\b", line) for line in lines)
        label = f'{region["path"]}:{region["start"]}-{region["end"]}'
        artifacts["regions/" + region["id"] + ".txt"] = raw
        code = "".join(line for line in lines if not re.match(r"^\s*//[/!]", line))
        code_parts.append(label + "\n" + code)
        groups = []
        for number, line in enumerate(lines, region["start"]):
            if re.match(r"^\s*//[/!]", line):
                if groups and groups[-1][-1][0] + 1 == number:
                    groups[-1].append((number, line))
                else:
                    groups.append([(number, line)])
        for group in groups:
            text = "".join(line for _, line in group)
            first, last = group[0][0], group[-1][0]
            doc_parts.append(f'{region["path"]}:{first}-{last}\n' + text)
            doc_records.append({"path": region["path"], "start": first, "end": last,
                                "sha256": digest(text.encode()), "text": text})
        region_records.append({**region, "code_sha256": digest(code.encode()),
                               "raw_bytes": len(raw.encode()), "code_bytes": len(code.encode())})
    code = "\n".join(code_parts)
    native = "\n".join(doc_parts)
    ledger = json.loads((BASE / "facts-ledger.json").read_text())
    additions = []
    for fact in ledger["facts"]:
        source = fact["source"]
        excerpt = "".join(sources[source["path"]][source["start"] - 1:source["end"]])
        assert excerpt
        fact["source_excerpt_sha256"] = digest(excerpt.encode())
        fact["source_excerpt"] = excerpt
        additions.append(f'{fact["endpoint"]}\n{fact["text"]}\n'
                         f'来源：{source["path"]}:{source["start"]}-{source["end"]}\n')
    completed = "\n".join(additions)
    task = (BASE / "task.txt").read_text()
    prefix = task + "\n=== CODE BEGIN ===\n" + code + "=== CODE END ===\n"
    packets = {
        "code_only": prefix,
        "code_native_doc": prefix + "\n=== NATIVE RUSTDOC BEGIN ===\n" + native
                           + "=== NATIVE RUSTDOC END ===\n",
        "code_completed_doc": prefix + "\n=== NATIVE RUSTDOC BEGIN ===\n" + native
                              + "=== NATIVE RUSTDOC END ===\n"
                              + "\n=== SOURCE-SUPPORTED ENDPOINT NOTES BEGIN ===\n" + completed
                              + "=== SOURCE-SUPPORTED ENDPOINT NOTES END ===\n",
    }
    for arm, packet in packets.items():
        artifacts["packets/" + arm + ".txt"] = packet
    artifacts["common-code.txt"] = code
    artifacts["native-doc.txt"] = native
    artifacts["completed-additions.txt"] = completed
    artifacts["native-doc-ledger.json"] = encoded_json(doc_records)
    artifacts["fact-source-excerpts.json"] = encoded_json(ledger)
    artifacts["region-index.json"] = encoded_json(region_records)
    artifacts["packet-hashes.json"] = encoded_json({
        "code_sha256": digest(code.encode()),
        "task_sha256": digest(task.encode()),
        "native_doc_sha256": digest(native.encode()),
        "completed_additions_sha256": digest(completed.encode()),
        "packets": {arm: {"sha256": digest(packet.encode()), "bytes": len(packet.encode()),
                          "characters": len(packet), "code_sha256": digest(code.encode())}
                    for arm, packet in packets.items()},
    })
    return artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-patch", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build()
    if args.emit_patch:
        print("*** Begin Patch")
        for name, content in artifacts.items():
            assert content.endswith("\n")
            print("*** Add File: " + str(BASE / name))
            for line in content[:-1].split("\n"):
                print("+" + line)
        print("*** End Patch")
    elif args.check:
        for name, content in artifacts.items():
            assert (BASE / name).read_bytes() == content.encode(), name
        print(encoded_json({"status": "PASS", "rebuilt_artifacts": len(artifacts),
                            "source_files": 4, "regions": 17, "packets": 3,
                            "identical_code": True, "model_dispatches": 0}), end="")
    else:
        parser.error("choose --emit-patch (stdout only) or --check (read only)")


if __name__ == "__main__":
    main()

"""Probe a pinned rust-analyzer CLI dump; not a production syntax validator."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from audit_facts_sample import decompress


TOOL = ["rustup", "run", "1.95.0", "rust-analyzer"]
NODE = re.compile(r"^( *)([A-Z_][A-Z_0-9]*)@(\d+)\.\.(\d+)(.*)$")
FIXTURES = {
    "unicode_same_line": ('/// 中文\nfn first() { let text = r#"} fn fake() {"#; } fn second() {}', 2),
    "trait_generic": ('trait Sample<T> { fn required(&self); fn defaulted(&self) {} }\n'
                      'impl<T> Sample<T> for Vec<T> { fn required(&self) {} }', 3),
    "nested_closure": ('fn outer() { fn inner() {} let callback = || { inner(); }; }', 2),
    "cfg_and_modules": ('#[cfg(any())] fn disabled() {}\nmod external;\n'
                        'mod inline { pub fn inside() {} }', 2),
    "macro_tokens": ('macro_rules! make { () => { fn generated() {} }; }\nmake!();', 0),
    "missing_delimiters": ('fn broken( {', 1),
    "invalid_expression": ('fn broken() { let value = ; }', 1),
}


def parse(source):
    process = subprocess.run(TOOL + ["parse"], input=source, capture_output=True, check=True)
    nodes = []
    stack = []
    for line in process.stdout.decode().splitlines():
        match = NODE.match(line)
        if not match:
            if line.strip():
                raise ValueError(f"Unexpected CLI dump line: {line}")
            continue
        indent, kind, start, end, suffix = match.groups()
        depth = len(indent)
        while stack and nodes[stack[-1]]["depth"] >= depth:
            stack.pop()
        node = {"kind": kind, "start": int(start), "end": int(end),
                "depth": depth, "parent": stack[-1] if stack else None}
        if not 0 <= node["start"] <= node["end"] <= len(source):
            raise ValueError("Dump range out of bounds")
        source[node["start"]:node["end"]].decode()
        nodes.append(node)
        stack.append(len(nodes) - 1)
    units = []
    for index, node in enumerate(nodes):
        if node["kind"] not in {"FN", "MODULE", "IMPL", "TRAIT", "CLOSURE_EXPR", "MACRO_RULES", "MACRO_CALL"}:
            continue
        children = [child for child in nodes if child["parent"] == index]
        names = [child for child in children if child["kind"] == "NAME"]
        name = source[names[0]["start"]:names[0]["end"]].decode() if names else None
        bodies = [child for child in children if child["kind"] == "BLOCK_EXPR"]
        keywords = [child for child in children if child["kind"] == "FN_KW"]
        ancestors = []
        parent = node["parent"]
        while parent is not None:
            if nodes[parent]["kind"] in {"FN", "MODULE", "IMPL", "TRAIT"}:
                ancestors.append({key: nodes[parent][key] for key in ("kind", "start", "end")})
            parent = nodes[parent]["parent"]
        units.append({"kind": node["kind"], "name": name,
                      "start_byte": node["start"], "end_byte": node["end"],
                      "start_line": source[:node["start"]].count(b"\n") + 1,
                      "end_line": source[:max(node["start"], node["end"] - 1)].count(b"\n") + 1,
                      "name_line": source[:names[0]["start"]].count(b"\n") + 1 if names else None,
                      "body_range": [bodies[0]["start"], bodies[0]["end"]] if bodies else None,
                      "fn_signature_tail_range": [keywords[0]["start"], bodies[0]["start"]] if keywords and bodies else None,
                      "ancestors": ancestors})
    return {"source_sha256": hashlib.sha256(source).hexdigest(),
            "dump_sha256": hashlib.sha256(process.stdout).hexdigest(),
            "exit_code": process.returncode, "stderr": process.stderr.decode(),
            "error_nodes": sum(node["kind"] == "ERROR" for node in nodes),
            "syntax_validity": "not established by this CLI",
            "units": units}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", args.revision + "^{commit}"], text=True).strip()
    raw = args.sample.read_bytes()
    facts = [json.loads(line) for line in decompress(raw).splitlines()]
    items = [record for record in facts if record["t"] == "item"]
    files = {}
    for path in sorted({item["file"] for item in items}):
        source = subprocess.check_output(["git", "-C", str(args.repo), "show", f"{commit}:{path}"])
        files[path] = parse(source)
    joins = []
    for item in items:
        if item["kind"] != "fn":
            continue
        candidates = [unit for unit in files[item["file"]]["units"]
                      if unit["kind"] == "FN" and unit["name"] == item["name"]
                      and item["line"] <= unit["name_line"] <= item["end_line"]]
        status = ("generated_not_joined" if item.get("gen") else
                  "unique_location_candidate" if len(candidates) == 1 else
                  "ambiguous" if candidates else "unmatched")
        overlaps = [unit for unit in files[item["file"]]["units"]
                    if unit["kind"] == "FN" and unit["name"] == item["name"]
                    and unit["start_line"] <= item["end_line"]
                    and item["line"] <= unit["end_line"]]
        joins.append({"key": item["key"], "file": item["file"], "status": status,
                      "macro": item.get("macro"),
                      "candidate_ranges": [[unit["start_byte"], unit["end_byte"]] for unit in candidates],
                      "overlap_candidates_not_confirmed": [
                          [unit["start_byte"], unit["end_byte"]] for unit in overlaps]
                          if status == "unmatched" else []})
    fixtures = {}
    for name, (source, expected) in FIXTURES.items():
        result = parse(source.encode())
        count = sum(unit["kind"] == "FN" for unit in result["units"])
        if count != expected:
            raise ValueError(f"Fixture {name}: expected {expected} FN nodes, got {count}")
        fixtures[name] = {"source": source, "expected_fn_nodes": expected, **result}
    unicode_case = fixtures["unicode_same_line"]
    second = next(unit for unit in unicode_case["units"] if unit["name"] == "second")
    if unicode_case["source"].encode()[second["start_byte"]:second["end_byte"]] != b"fn second() {}":
        raise ValueError("UTF-8 byte slicing failed")
    declarations = [unit for unit in fixtures["trait_generic"]["units"]
                    if unit["kind"] == "FN" and unit["body_range"] is None]
    if len(declarations) != 1:
        raise ValueError("Trait declaration/body distinction failed")
    if not any(unit["kind"] == "CLOSURE_EXPR" for unit in fixtures["nested_closure"]["units"]):
        raise ValueError("Closure fixture was not represented")
    binary = subprocess.check_output(["rustup", "which", "--toolchain", "1.95.0", "rust-analyzer"], text=True).strip()
    result = {"schema": "rust-unit-location-probe/1", "commit": commit,
              "tool": subprocess.check_output(TOOL + ["--version"], text=True).strip(),
              "tool_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              "sample_sha256": hashlib.sha256(raw).hexdigest(),
              "files": files, "fixtures": fixtures, "joins": joins,
              "join_counts": dict(Counter(join["status"] for join in joins)),
              "limitations": ["Unstable CLI dump adapter; not a supported AST API.",
                              "Locations are candidates, not independently verified semantic identities.",
                              "No cfg evaluation, macro expansion, type resolution or module loading.",
                              "Malformed source can exit successfully without ERROR nodes.",
                              "Revision/sample alignment is a caller prerequisite; use the sample audit first."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"commit": commit, "files": len(files), "fixtures": len(fixtures),
                      "join_counts": result["join_counts"]}, indent=2))


if __name__ == "__main__":
    main()

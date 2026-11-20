"""Run bounded parser-adapter checks, not duplicate detection experiments."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from probe_rust_units import FIXTURES


def parse(binary, source):
    process = subprocess.run([str(binary)], input=source, capture_output=True, check=True, timeout=30)
    result = json.loads(process.stdout)
    if result.get("schema") != "syn-unit-probe/2":
        raise ValueError("Unsupported parser output schema")
    if result.get("status") not in {"parsed_by_syn", "rejected_by_syn", "unsupported_prefix"}:
        raise ValueError("Unknown parser status")
    if result["status"] != "parsed_by_syn" and (result.get("units") or not result.get("diagnostics")):
        raise ValueError("Rejected input must have diagnostics and no usable units")
    result["source_sha256"] = hashlib.sha256(source).hexdigest()
    for unit in result["units"]:
        for field in ("range", "signature_range", "body_range"):
            if unit.get(field) is not None:
                start, end = unit[field]
                if not 0 <= start <= end <= len(source):
                    raise ValueError(f"Out-of-bounds {field}: {unit}")
                source[start:end].decode()
    return result


def functions(result):
    return [unit for unit in result["units"] if unit["kind"] in {"fn", "impl_fn", "trait_fn"}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    prior = json.loads(args.prior.read_text())
    fixtures = {}
    cases = {**FIXTURES,
             "macro_inner_invalid": ("unknown_macro! { fn broken( }", 0),
             "macro_balanced_invalid_rust": ("unknown_macro! { fn broken() -> }", 0),
             "unresolved_semantics": ("fn missing() -> Unknown { absent() }", 1),
             "bom_prefix": ("\ufefffn example() {}", 0),
             "shebang_prefix": ("#!/usr/bin/env rust-script\nfn example() {}", 0),
             "verbatim_item": ("fn declaration();", 0),
             "metadata": ('#![cfg_attr(test, allow(dead_code))]\n'
                          '#[cfg(any())] mod guarded { #[derive(Clone)] struct Value; '
                          'impl Value { #[inline] fn work(&self) {} } }', 1),
             "modifiers": ("pub const unsafe fn raw<T>(value: T) -> T { value }", 1)}
    for name, (text, expected) in cases.items():
        result = parse(binary, text.encode())
        rejected = name in {"missing_delimiters", "invalid_expression", "macro_inner_invalid"}
        unsupported = name in {"bom_prefix", "shebang_prefix"}
        if unsupported:
            if result["status"] != "unsupported_prefix" or result["units"]:
                raise ValueError(f"Unsupported prefix was not excluded: {name}")
        elif rejected:
            if result["status"] != "rejected_by_syn" or not result["diagnostics"] or result["units"]:
                raise ValueError(f"Invalid fixture accepted: {name}")
        elif result["status"] != "parsed_by_syn" or len(functions(result)) != expected:
            raise ValueError(f"Unexpected fixture result: {name}")
        fixtures[name] = {"source": text, "expected_rejected": rejected,
                          "expected_unsupported": unsupported, **result}
    if not any(unit["kind"] == "verbatim_item" for unit in fixtures["verbatim_item"]["units"]):
        raise ValueError("Verbatim item silently lost")
    metadata = fixtures["metadata"]
    if metadata["file_attributes"][0]["path"] != "cfg_attr":
        raise ValueError("File attributes lost")
    method = functions(metadata)[0]
    inherited = [metadata["units"][parent] for parent in method["ancestors"]]
    if method["attributes"][0]["path"] != "inline" or not any(
            attribute["path"] == "cfg" for unit in inherited for attribute in unit["attributes"]):
        raise ValueError("Direct/inherited attribute context lost")
    if not any(unit["kind"] == "struct" and unit["attributes"][0]["path"] == "derive"
               for unit in metadata["units"]):
        raise ValueError("Struct derive context lost")
    unicode_case = fixtures["unicode_same_line"]
    second = next(unit for unit in functions(unicode_case) if unit["name"] == "second")
    start, end = second["range"]
    if unicode_case["source"].encode()[start:end] != b"fn second() {}":
        raise ValueError("UTF-8 byte slicing failed")
    if sum(unit["body_range"] is None for unit in functions(fixtures["trait_generic"])) != 1:
        raise ValueError("Trait declaration/body distinction failed")
    signatures = functions(fixtures["modifiers"])
    start, end = signatures[0]["signature_range"]
    if not fixtures["modifiers"]["source"][start:end].startswith("const unsafe fn"):
        raise ValueError("Signature modifiers lost")
    files = {}
    for path, earlier in prior["files"].items():
        source = subprocess.check_output(["git", "-C", str(args.repo), "show", f"{prior['commit']}:{path}"])
        result = parse(binary, source)
        if result["source_sha256"] != earlier["source_sha256"]:
            raise ValueError("Source differs from prior probe")
        if result["status"] != "parsed_by_syn":
            raise ValueError(f"Fixed source rejected: {path}")
        previous_names = sorted(unit["name"] for unit in earlier["units"] if unit["kind"] == "FN")
        if sorted(unit["name"] for unit in functions(result)) != previous_names:
            raise ValueError(f"Parser function-name disagreement: {path}")
        files[path] = result
    output = {"schema": "syn-adapter-check/1", "commit": prior["commit"],
              "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "versions": {"syn": "2.0.119", "proc-macro2": "1.0.107"},
              "fixtures": fixtures, "files": files,
              "limitations": ["Parser success is not rustc validation or type checking.",
                              "Name multiset agreement does not independently establish exact spans.",
                              "No macro expansion, cfg evaluation, module loading or identity resolution."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"fixtures": len(fixtures), "files": len(files),
                      "source_functions": sum(len(functions(result)) for result in files.values())}))


if __name__ == "__main__":
    main()

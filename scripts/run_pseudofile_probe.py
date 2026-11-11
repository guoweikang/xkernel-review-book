import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUSTC = Path('/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc')
SOURCES = {
    "starry": ("2026-11-05-starry-reading-scope-01/sources/kernel/src/pseudofs/file.rs",
               "c7d4ec8d527c12cd83eae43a92b83bc1e695f5118eb7521bd788844d1172def9",
               "    fn write_at(", "    fn append("),
    "xkernel": ("2026-11-05-rust-pilot-seeds-01/sources/fs/kvfs/src/simple_file.rs",
                "88fdfcbce5edea1f759c3f107b68a10e2b45c9b4e483ed78de1e41bfa719a912",
                "    fn write(&self, file: &VfsFile, data:", "    fn write_iter("),
}


def main():
    parser = argparse.ArgumentParser(description="Extracted method experiment with controlled dependencies; not kernel integration tests")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("Expected a simple run ID")
    run = ROOT / ".build/pseudofile" / args.run_id
    evidence = ROOT / "research/evidence/runs" / args.run_id
    if run.exists() or evidence.exists():
        parser.error("Run already exists")
    methods = {}
    provenance = {}
    for name, (relative, checksum, start, end) in SOURCES.items():
        source = ROOT / "research/evidence/runs" / relative
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != checksum:
            raise ValueError("Source checksum mismatch")
        decoded = content.decode()
        if decoded.count(start) != 1:
            raise ValueError("Ambiguous method start")
        first = decoded.index(start)
        last = decoded.index(end, first)
        method = decoded[first:last]
        methods[name] = method
        provenance[name] = {"source": relative, "source_sha256": checksum,
                            "start_line": decoded[:first].count("\n") + 1,
                            "method_sha256": hashlib.sha256(method.encode()).hexdigest(),
                            "transformation": "verbatim substring; wrapper types and dependencies replaced"}
    work = run / "work"
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    template = (ROOT / "research/tools/pseudofile-probe.rs.in").read_text()
    harness = template.replace("@@STARRY_METHOD@@", methods["starry"]).replace("@@XKERNEL_METHOD@@", methods["xkernel"])
    for name, method in methods.items():
        (evidence / f"{name}-method.rs").write_text(method)
    (work / "probe.rs").write_text(harness)
    (evidence / "probe.rs").write_text(harness)
    shutil.copy2(__file__, evidence / "runner.py")
    shutil.copy2(ROOT / "scripts/scc_namespace.sh", evidence / "namespace.sh")
    (evidence / "rustc-version.txt").write_bytes(subprocess.check_output([str(RUSTC), "-Vv"]))
    report = {"scope": "extracted_methods_with_test_doubles", "passed": False,
              "provenance": provenance, "commands": [], "kernel_integration": "not_run",
              "checks": ["PC01", "PC03"], "negative_control": "not_run"}

    def execute(command, log_name):
        report["commands"].append(command)
        with (evidence / log_name).open("w") as log:
            return subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=90).returncode

    def isolated(binary, root_name, *arguments):
        return ["timeout", "60", "unshare", "--user", "--map-root-user", "--mount", "--pid", "--net", "--ipc", "--uts",
                "--fork", "bash", str(ROOT / "scripts/scc_namespace.sh"), str(run / root_name), str(work),
                str(ROOT / ".tools/scc-smoke"), f"/work/{binary}", "--test-threads=1", "--nocapture", *arguments]

    try:
        compile_command = [str(RUSTC), "--edition=2024", "--test", str(work / "probe.rs"), "-o", str(work / "probe")]
        report["compile_exit"] = execute(compile_command, "compile.log")
        if report["compile_exit"] != 0:
            raise ValueError("Compilation failed")
        report["test_exit"] = execute(isolated("probe", "root"), "execution.log")
        if report["test_exit"] != 0:
            raise ValueError("Contract checks failed")
        negative = harness.replace('&["read", "write:abXYef"]', '&["read", "write:XY"]')
        if negative == harness:
            raise ValueError("Negative control did not modify expectation")
        (work / "negative.rs").write_text(negative)
        (evidence / "negative.rs").write_text(negative)
        command = [str(RUSTC), "--edition=2024", "--test", str(work / "negative.rs"), "-o", str(work / "negative")]
        if execute(command, "negative-compile.log") != 0:
            raise ValueError("Negative control compilation failed")
        exit_code = execute(isolated("negative", "negative-root", "pc01_starry_patches_old_content", "--exact"), "negative.log")
        log = (evidence / "negative.log").read_text()
        if exit_code != 101 or "assertion `left == right` failed" not in log or "1 failed" not in log:
            raise ValueError("Negative control did not reject incorrect callback content")
        report["negative_control"] = "incorrect_equivalence_expectation_rejected"
        report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
    finally:
        (evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "evidence": str(evidence), "error": report.get("error")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

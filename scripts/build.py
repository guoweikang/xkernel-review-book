import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".build" / "src"
RESEARCH = ROOT / "research"


def main():
    local_binary = ROOT / ".tools" / "mdbook"
    binary = str(local_binary) if local_binary.exists() else shutil.which("mdbook")
    if not binary:
        raise SystemExit("Install mdBook 0.5.4; see README.md")
    version = subprocess.check_output([binary, "--version"], text=True).strip()
    if version != "mdbook v0.5.4":
        raise SystemExit(f"Expected mdbook v0.5.4, got {version}")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    shutil.copytree(ROOT / "chapters", STAGING)
    manifest = json.loads((RESEARCH / "evidence" / "manifest.json").read_text())
    evidence_urls = {
        (RESEARCH / "evidence" / record["path"]).resolve(): record["source_url"]
        for record in manifest["records"]
        if record["status"] == "downloaded"
    }
    research_files = sorted(
        source for source in RESEARCH.rglob("*.md")
        if not source.is_relative_to(RESEARCH / "evidence" / "originals")
    )
    for source in research_files:
        destination = STAGING / "research" / source.relative_to(RESEARCH)
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_text()

        def replace_link(match):
            target = match.group(1)
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            resolved = (source.parent / parsed.path).resolve()
            depth = len(destination.relative_to(STAGING).parts) - 1
            if not resolved.is_relative_to(RESEARCH.resolve()):
                return "](" + "../" * depth + "source-boundary.md)"
            if resolved in evidence_urls:
                return "](" + evidence_urls[resolved] + ")"
            if resolved == (RESEARCH / "evidence" / "manifest.json").resolve():
                return "](" + "../" * depth + "evidence-index.md)"
            if parsed.path.endswith("README.md"):
                return "](" + target.replace("README.md", "index.md") + ")"
            return match.group(0)

        content = re.sub(r"\]\(([^)]+)\)", replace_link, content)
        destination.write_text(content)
    summary_path = STAGING / "SUMMARY.md"
    summary = summary_path.read_text()
    listed = set(re.findall(r"\]\(([^)]+)\)", summary))
    for source in research_files:
        relative = "research/" + source.relative_to(RESEARCH).as_posix()
        if relative in listed:
            continue
        title_match = re.search(r"^# (.+)$", source.read_text(), re.MULTILINE)
        title = title_match.group(1) if title_match else source.stem
        summary += f"- [{title}]({relative})\n"
    summary_path.write_text(summary)
    evidence = [
        "# 证据索引", "",
        "原始全文仅保存在本地，不进入网页或 Git。以下链接指向一手来源。",
        "下载不等于精读；校验和不构成法律时间戳。失败项不隐藏。", "",
        "| 编号 | 来源 | 获取状态 | 字节数 | SHA-256 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in manifest["records"]:
        label = record.get("path", "未取回").split("/")[-1]
        status = record["status"]
        if status == "failed":
            status += ": " + record.get("error", "unknown").replace("|", "\\|")
        evidence.append(
            f"| {record['source_id']} | [{label}]({record['source_url']}) "
            f"| {status} | {record.get('bytes', '—')} "
            f"| `{record.get('sha256', '—')}` |"
        )
    (STAGING / "evidence-index.md").write_text("\n".join(evidence) + "\n")
    subprocess.run([binary, "build", str(ROOT)], check=True)
    print(f"Built {len(research_files)} research documents plus teaching chapters into {ROOT / 'dist'}")


if __name__ == "__main__":
    main()

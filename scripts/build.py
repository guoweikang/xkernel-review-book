import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".build" / "src"
RESEARCH = ROOT / "research"


def validate_catalog(actual, catalog):
    groups = catalog["groups"]
    identifiers = [group["id"] for group in groups]
    if len(identifiers) != len(set(identifiers)) or any(
        not re.fullmatch(r"[a-z][a-z0-9-]*", identifier) for identifier in identifiers
    ):
        raise SystemExit("Invalid or duplicate research topic identifiers")
    registered = [name for group in groups for name in group["documents"]]
    if len(registered) != len(set(registered)):
        raise SystemExit("Duplicate primary assignment in research/catalog.json")
    if set(registered) != actual:
        raise SystemExit(f"Research catalog mismatch: unassigned={sorted(actual - set(registered))}; missing={sorted(set(registered) - actual)}")


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
        and not source.is_relative_to(RESEARCH / "evidence" / "runs")
    )
    catalog = json.loads((RESEARCH / "catalog.json").read_text())
    actual = {source.relative_to(RESEARCH).as_posix() for source in research_files}
    validate_catalog(actual, catalog)
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
    navigation = []
    for group in catalog["groups"]:
        overview = STAGING / "research-topics" / (group["id"] + ".md")
        if not overview.exists():
            raise SystemExit(f"Missing research synthesis: {overview}")
        navigation.append(f'- [{group["title"]}](research-topics/{group["id"]}.md)')
        archive_path = f'research-topics/{group["id"]}-records.md'
        navigation.append(f'  - [材料与实验记录]({archive_path})')
        records = [f'# {group["title"]}：材料与实验记录', '',
                   f'[专题综合]({group["id"]}.md)', '',
                   '以下保留原始记录的标题和时点；历史计划不代表当前完成状态。', '']
        for name in group["documents"]:
            source = RESEARCH / name
            title_match = re.search(r"^# (.+)$", source.read_text(), re.MULTILINE)
            title = title_match.group(1) if title_match else source.stem
            navigation.append(f'    - [{title}](research/{name})')
            link = name.removesuffix("README.md") + "index.md" if name.endswith("README.md") else name
            records.append(f'- [{title}](../research/{link})')
        (STAGING / archive_path).write_text("\n".join(records) + "\n")
    marker = "<!-- RESEARCH_CATALOG -->"
    if summary.count(marker) != 1:
        raise SystemExit("SUMMARY must contain exactly one research catalog marker")
    summary = summary.replace(marker, "\n".join(navigation))
    summary_path.write_text(summary)
    for source in (RESEARCH / "publications").rglob("*"):
        if source.is_file() and source.suffix in {".pdf", ".docx", ".pptx"}:
            destination = STAGING / "research" / source.relative_to(RESEARCH)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
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

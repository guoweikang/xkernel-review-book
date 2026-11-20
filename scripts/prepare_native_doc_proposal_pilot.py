#!/usr/bin/env python3
"""Freeze existing snippets and native-doc arms without rankings or old judgments."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="2026-11-17-native-doc-proposal-01")
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in (".", ".."):
        parser.error("run must be a single directory name")
    protocol_path = ROOT / "research/protocols/native-doc-proposal-pilot-v1.json"
    protocol = json.loads(protocol_path.read_text())
    parent = ROOT / "research/evidence/runs" / protocol["parent_run"] / "reviewer"
    cases = json.loads((parent / "cases.json").read_text())
    run = ROOT / "research/evidence/runs" / args.run
    run.mkdir(exist_ok=False)
    shutil.copyfile(protocol_path, run / "protocol.json")
    shutil.copyfile(Path(__file__), run / "preparer.py")
    selected, used_paths, audit = [], set(), []
    for case in sorted(cases, key=lambda row: row["case_id"]):
        members = case["members"]
        paths = {member["path"] for member in members}
        docs = [(parent / case["case_id"] / f"{side}-doc.txt").read_text() for side in ("left", "right")]
        excluded = any("ut-tests" in member["path"] or member["path"].endswith("/path.rs")
                       or member["name"] in ("getattr", "inode_init")
                       or "unlink" in member["name"] or "rmdir" in member["name"] for member in members)
        reason = "selected"
        if excluded:
            reason = "excluded-scope"
        elif not any(doc.strip() for doc in docs):
            reason = "no-native-method-doc"
        elif paths & used_paths:
            reason = "source-path-overlap"
        elif len(selected) == 2:
            reason = "after-fixed-quota"
        audit.append({"case_id": case["case_id"], "reason": reason})
        if reason == "selected":
            selected.append(case)
            used_paths.update(paths)
    assert len(selected) == 2
    prompts = []
    for case in selected:
        body = []
        doc_body = []
        for side, member in zip(("left", "right"), case["members"]):
            snippet = (parent / case["case_id"] / f"{side}-snippet.rs").read_bytes()
            assert digest(snippet) == member["sha256"]
            assert not any(marker in snippet for marker in (b"//", b"/*", b"#[doc", b"#![doc"))
            source = (parent / case["case_id"] / f"{side}-source.rs").read_bytes()
            assert digest(source) == member["source_sha256"]
            body.append(f"{side}: {member['path']}:{member['start_line']}\n```rust\n{snippet.decode()}\n```\n")
            doc = (parent / case["case_id"] / f"{side}-doc.txt").read_text()
            doc_body.append(f"{side} native documentation:\n{doc}\n")
        base = "你是Rust代码研究提案助手。这是一个独立文本任务，不要使用任何工具，不读取文件或其他会话，只使用本消息材料。不要修改代码。不能从函数名推定未展示实现的语义。允许证据不足而不提出抽取。请用不超过900汉字（代码标识符除外）给出一次回答，分列：共享机制或弃权理由、必须保留的差异、已有委托、最小接口草案、约束及其来源(code/doc/unknown)、一条可反驳提案的验证义务、缺失上下文。文档只能作为声明，不能自动当作实现事实。不要报告置信度分数或宣称已经测试。\n\n" + "\n".join(body)
        for arm in protocol["arms"]:
            prompt = base + ("\n" + "\n".join(doc_body) if arm == "code_native_doc" else "")
            name = f"{case['case_id']}-{arm}.txt"
            (run / name).write_text(prompt)
            prompts.append({"case_id": case["case_id"], "arm": arm, "path": name,
                            "sha256": digest(prompt.encode()), "common_code_sha256": digest("\n".join(body).encode())})
    (run / "selection.json").write_text(json.dumps({"selected": selected, "audit": audit}, indent=2) + "\n")
    (run / "freeze.json").write_text(json.dumps({"protocol_sha256": digest(protocol_path.read_bytes()),
                                                "prompts": prompts}, indent=2) + "\n")
    print(json.dumps({"selected": [case["case_id"] for case in selected], "prompts": len(prompts)}))


if __name__ == "__main__":
    main()

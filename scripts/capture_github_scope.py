import argparse
import datetime
import hashlib
import json
import re
import urllib.request
from pathlib import Path


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "rust-review-research"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description="Capture a pinned repository tree and selected source blobs without executing them")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo) or not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("Expected owner/repository and a full commit SHA")
    if args.output.exists():
        parser.error("Output already exists")
    args.output.mkdir(parents=True)
    manifest = {"repository": args.repo, "revision": args.revision,
                "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": "incomplete", "files": []}
    try:
        api = f"https://api.github.com/repos/{args.repo}"
        commit_raw = download(f"{api}/git/commits/{args.revision}")
        (args.output / "commit.json").write_bytes(commit_raw)
        commit = json.loads(commit_raw)
        if commit["sha"] != args.revision:
            raise ValueError("Commit mismatch")
        tree_raw = download(f"{api}/git/trees/{commit['tree']['sha']}?recursive=1")
        (args.output / "tree.json").write_bytes(tree_raw)
        tree = json.loads(tree_raw)
        if tree.get("truncated") or tree["sha"] != commit["tree"]["sha"]:
            raise ValueError("Incomplete or mismatched tree")
        entries = {entry["path"]: entry for entry in tree["tree"]}
        manifest["gitlinks"] = [entry for entry in tree["tree"] if entry["type"] == "commit"]
        manifest["rust_source_files"] = sum(entry["type"] == "blob" and path.endswith(".rs") for path, entry in entries.items())
        for path in args.file:
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("Unsafe file path")
            entry = entries[path]
            if entry["type"] != "blob":
                raise ValueError("Requested path is not a blob")
            url = f"https://raw.githubusercontent.com/{args.repo}/{args.revision}/{path}"
            content = download(url)
            blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            if blob != entry["sha"]:
                raise ValueError("Blob mismatch")
            target = args.output / "sources" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            manifest["files"].append({"path": path, "url": url, "git_blob": blob,
                                      "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
        manifest["status"] = "captured"
    except Exception as error:
        manifest["error"] = str(error)
        raise
    finally:
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (args.output / "capture.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: manifest[key] for key in ("repository", "revision", "status", "rust_source_files", "gitlinks")}, indent=2))


if __name__ == "__main__":
    main()

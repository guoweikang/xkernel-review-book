import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"a", "img", "script", "link", "iframe"}:
            return
        self.targets.extend(value for name, value in attrs if name in {"href", "src"} and value)


def main():
    if not (DIST / "index.html").exists():
        raise SystemExit("Build the book first")
    failures = []
    html_files = list(DIST.rglob("*.html"))
    for page in html_files:
        parser = Links()
        parser.feed(page.read_text())
        for target in parser.targets:
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = unquote(parsed.path)
            candidate = DIST / path.lstrip("/") if path.startswith("/") else page.parent / path
            if not candidate.resolve().is_relative_to(DIST.resolve()) or not candidate.exists():
                failures.append(f"Broken link: {page.relative_to(DIST)} -> {target}")
    forbidden = [path for path in DIST.rglob("*") if path.is_file() and (
        path.suffix in {".pdf", ".rs", ".py", ".toml"} or "originals" in path.parts or ".git" in path.parts
    )]
    failures.extend(f"Unexpected private/source artifact in site: {path}" for path in forbidden)
    manifest = json.loads((ROOT / "research/evidence/manifest.json").read_text())
    verified = 0
    absent = 0
    for record in manifest["records"]:
        if record["status"] != "downloaded":
            continue
        path = ROOT / "research/evidence" / record["path"]
        if not path.exists():
            absent += 1
            continue
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            failures.append(f"Archive checksum mismatch: {record['path']}")
        verified += 1
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"PASS: {len(html_files)} HTML pages; local links; artifact isolation; {verified} archive checksums")
    if absent:
        print(f"NOTE: {absent} local-only originals absent; reference-only checkout is supported")


if __name__ == "__main__":
    main()

"""
Validate that relative markdown links in README.md and docs/**/*.md resolve to files in the repo.

This is intentionally lightweight (no third-party deps) so it can be run anywhere:

    python tools/validate_markdown_links.py

Notes:
- Only checks *relative* markdown links: [text](path/to/file.md)
- Ignores:
  - external URLs (contains ://)
  - mailto:
  - fragment-only links (#anchor)
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def iter_md_files() -> list[Path]:
    files: list[Path] = []
    readme = ROOT / "README.md"
    if readme.exists():
        files.append(readme)
    docs_dir = ROOT / "docs"
    if docs_dir.exists():
        files.extend(docs_dir.rglob("*.md"))
    return files


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def is_relative_link(target: str) -> bool:
    t = target.strip()
    if not t:
        return False
    if t.startswith("#"):
        return False
    if "://" in t:
        return False
    if t.startswith("mailto:"):
        return False
    return True


def main() -> int:
    errors: list[tuple[Path, str, str]] = []

    for md in iter_md_files():
        text = md.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            target = m.group(2).strip()

            # Strip optional title: (path "title")
            if " " in target and (target.endswith('"') or target.endswith("'")):
                target = target.split(" ", 1)[0]

            if not is_relative_link(target):
                continue

            target_path = target.split("#", 1)[0]
            if not target_path:
                continue

            resolved = (md.parent / target_path).resolve()

            # Allow outside-repo only if it exists on disk (rare but possible).
            try:
                resolved.relative_to(ROOT)
            except Exception:
                if not resolved.exists():
                    errors.append((md, target, "points outside repo and does not exist"))
                continue

            if not resolved.exists():
                errors.append((md, target, "target does not exist"))

    if errors:
        print("Broken relative links found:")
        for md, target, reason in errors:
            print(f"- {md.relative_to(ROOT)} -> {target} ({reason})")
        return 1

    print("OK: all relative markdown links resolve to existing files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


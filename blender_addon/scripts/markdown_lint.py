"""Lightweight Markdown linter for a subset of rules used in this repo.

Implemented rules:
    MD029 (ol-prefix): Ordered list item prefix should increment by 1 within a block (but uniform '1.' style is allowed).
  MD031 (blanks-around-fences): Fenced code blocks must be surrounded by blank lines.
  MD032 (blanks-around-lists): Lists must be surrounded by blank lines.

Exit code: 0 if no issues, 1 otherwise.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

MARKDOWN_EXTS = {".md", ".markdown", ".mdown"}

FENCE_RE = re.compile(r"^```")
OL_ITEM_RE = re.compile(r"^(\s*)(\d+)\.\s+")
UL_ITEM_RE = re.compile(r"^(\s*)[-*+]\s+")


SKIP_DIR_NAMES = {".venv", "venv", ".git", "dist", "__pycache__"}


def iter_markdown_files(root: Path) -> List[Path]:
    files: List[Path] = []
    # Manual walk to allow directory exclusion efficiently
    for path in root.rglob("*.md"):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if parts & SKIP_DIR_NAMES:
            continue
        files.append(path)
    return files


def lint_file(path: Path) -> List[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    issues: List[str] = []

    # Track ordered list blocks
    in_ol = False
    expected_num = None
    # Tracking variables (some removed to satisfy linter if unused)
    in_fence = False

    def is_list_line(idx: int) -> bool:
        line = lines[idx]
        return bool(OL_ITEM_RE.match(line) or UL_ITEM_RE.match(line))

    for i, raw in enumerate(lines):
        line_no = i + 1
        stripped = raw.rstrip()

        # Fence detection MD031
        if FENCE_RE.match(stripped):
            if not in_fence:
                # opening fence requires blank line before unless BOF
                if i > 0 and lines[i - 1].strip() != "":
                    issues.append(
                        f"{path}:{line_no}: MD031 opening fence not preceded by blank line"
                    )
                in_fence = True
            else:
                # closing fence requires blank line after unless EOF
                if i + 1 < len(lines) and lines[i + 1].strip() != "":
                    issues.append(
                        f"{path}:{line_no}: MD031 closing fence not followed by blank line"
                    )
                in_fence = False
            continue

        if in_fence:
            continue  # ignore list / other rules inside code blocks

        m_ol = OL_ITEM_RE.match(stripped)
        if m_ol:
            num = int(m_ol.group(2))
            if not in_ol:
                in_ol = True
                expected_num = num
                # MD032: blank before list (unless BOF)
                if i > 0 and lines[i - 1].strip() != "":
                    issues.append(f"{path}:{line_no}: MD032 list not preceded by blank line")
            else:
                if expected_num is not None:
                    # Allow uniform '1.' style: if current and all previous items are '1', don't escalate expected number.
                    if not (expected_num == 1 and num == 1):
                        expected_num += 1
                        if num != expected_num:
                            issues.append(
                                f"{path}:{line_no}: MD029 ordered list item expected {expected_num} got {num}"
                            )
            continue

        # If we reach here and were in an ordered list, we may be exiting it
        if in_ol and stripped == "":
            # Blank line terminates ordered list cleanly
            in_ol = False
            expected_num = None
            # reset state after blank line
            continue
        elif in_ol and stripped != "" and not is_list_line(i):
            # list terminated without blank line after
            issues.append(f"{path}:{line_no}: MD032 list not followed by blank line")
            in_ol = False
            expected_num = None
            # reset state after non-list content without blank line
        elif in_ol and stripped == "":
            # blank line resets state
            in_ol = False
            expected_num = None
            # state cleared

    # finalize if file ends during list without trailing blank line (acceptable by many linters, but enforce)
    if in_ol:
        issues.append(f"{path}:{len(lines)}: MD032 list not followed by blank line at EOF")

    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # project root (two levels up from scripts/)
    md_files = iter_markdown_files(root)
    all_issues: List[str] = []
    for f in md_files:
        all_issues.extend(lint_file(f))

    if all_issues:
        print("Markdown lint issues found:")
        for issue in all_issues:
            print(issue)
        return 1
    print("Markdown lint: OK (no issues detected)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

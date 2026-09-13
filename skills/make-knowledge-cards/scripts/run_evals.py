#!/usr/bin/env python3
"""Regression check: validate every worked example in references/examples.md.

The examples file is the single source of truth for expected output, so this script
extracts each fenced ```markdown block that contains cards and runs the same checks as
check_cards.py over it. Run it after any change to SKILL.md or the references.

Usage:
    python scripts/run_evals.py [--examples PATH]

Exit code 0 when all cases pass, 1 otherwise. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_cards import report, validate  # noqa: E402

DEFAULT_EXAMPLES = Path(__file__).resolve().parent.parent / "references" / "examples.md"
CASE_RE = re.compile(r"^##\s+Case\s+(?P<num>\d+)\s*[-–—]\s*(?P<title>.+?)\s*$", re.M)
OPEN_RE = re.compile(r"^(?P<fence>`{3,})markdown\s*$", re.M)


def extract_cases(text: str) -> list[dict]:
    cases: list[dict] = []
    markers: list[tuple[int, str]] = [(m.start(), f"Case {m.group('num')} - {m.group('title')}") for m in CASE_RE.finditer(text)]
    markers.append((len(text), ""))

    for index, (start, name) in enumerate(markers[:-1]):
        segment = text[start: markers[index + 1][0]]
        for block in _markdown_blocks(segment):
            if "### 卡片" in block or "### Card" in block:
                cases.append({"name": name, "text": block})
                break
    return cases


def _markdown_blocks(segment: str) -> list[str]:
    """Extract fenced markdown blocks, honouring fences longer than three backticks."""
    blocks: list[str] = []
    for match in OPEN_RE.finditer(segment):
        fence = match.group("fence")
        closer = re.compile(r"^" + fence + r"\s*$", re.M)
        close = closer.search(segment, match.end())
        if close:
            blocks.append(segment[match.end(): close.start()])
    return blocks


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate all worked examples in examples.md.")
    parser.add_argument("--examples", default=str(DEFAULT_EXAMPLES))
    args = parser.parse_args(argv)

    path = Path(args.examples)
    if not path.is_file():
        print(f"FAIL  文档  找不到样例文件：{path}")
        return 1

    cases = extract_cases(path.read_text(encoding="utf-8-sig"))
    if not cases:
        print(f"FAIL  文档  未在 {path} 中解析到任何样例（需以 '## Case N - ' 分隔并含 ```markdown 代码块）")
        return 1

    print(f"examples: {path.name} | cases: {len(cases)}")
    failed = 0
    for case in cases:
        print(f"\n--- {case['name']} ---")
        result = validate(case["text"])
        report(result)
        if not result["passed"]:
            failed += 1

    print(f"\nRESULT: {'PASS' if failed == 0 else 'FAIL'} | cases: {len(cases)} | failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

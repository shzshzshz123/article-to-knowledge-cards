#!/usr/bin/env python3
"""Validate knowledge cards against the output contract of make-knowledge-cards.

Usage:
    python scripts/check_cards.py cards.md
    python scripts/check_cards.py --stdin
    python scripts/check_cards.py --min-noted 5 --max-silent 8 cards.md

Exit code 0 when no FAIL is reported, 1 otherwise. Standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

MIN_NOTED = 5
MAX_SILENT = 8
HARD_MAX = 12
MAX_CORE_SENTENCES = 1
WARN_EXPLANATION_SENTENCES = 6
WARN_TITLE_CHARS_ZH = 30
WARN_TITLE_CHARS_EN = 70
WARN_TITLE_SIMILARITY = 0.85

NOTE_RE = re.compile(
    r"不足以支撑|信息不足|insufficient|原文较长|内容较长|信息点密集|信息密度|"
    r"longer source|dense source|共\s*\d+\s*张|\d+\s*cards?"
)

BANNED_TITLE_WORDS = [
    "简介",
    "概述",
    "其他",
    "补充说明",
    "要点一",
    "要点二",
    "要点三",
    "about",
    "misc",
    "introduction",
    "overview",
    "other",
]

ARTICLE_HEADING_RE = re.compile(r"^##\s+(?P<title>\S.*?)\s*$", re.M)
GROUP_RE = re.compile(r"^##\s+(?P<title>.*?(?:知识卡片|Knowledge Cards).*?)\s*$", re.M)
CARD_RE = re.compile(
    r"^###\s+(?:卡片|Card)\s*(?P<num>\d+)\s*[:：]\s*(?P<title>.+?)\s*$", re.M
)
FIELD_RE = re.compile(r"^[-*]\s*\*\*(?P<label>[^*]+?)\*\*\s*[:：]\s*(?P<value>.*)$")

FIELD_KINDS = {
    "core": {"核心知识", "core knowledge"},
    "explanation": {"简明解释", "explanation"},
    "example": {"例子", "example"},
    "selftest": {"自测问题", "self-test", "self test", "self-test question"},
    "source": {"原文依据", "原文出处", "source", "source reference"},
}
COMBO_LABELS = {"例子 / 自测问题", "example / self-test", "example / self-test question"}

SENTENCE_END_RE = re.compile(r"[。！？!?]|\.(?=\s|$)")


def label_key(label: str) -> str:
    return re.sub(r"\s*/\s*", " / ", label.strip().lower())


def kind_of(label: str) -> str | None:
    key = label_key(label)
    for kind, names in FIELD_KINDS.items():
        if key in names:
            return kind
    return None


def is_combo_label(label: str) -> bool:
    return label_key(label) in COMBO_LABELS


def count_sentences(text: str) -> int:
    return len(SENTENCE_END_RE.findall(text))


def script_of(text: str) -> str | None:
    """Classify a passage, tolerating Chinese prose that quotes Latin identifiers.

    Chinese carries far more meaning per character, so a passage with a handful of
    ideographs and many Latin letters (e.g. a sentence about Cache-Control) is still Chinese.
    """
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if cjk >= 4 and cjk * 3 >= latin:
        return "zh"
    if latin > cjk:
        return "en"
    if cjk:
        return "zh"
    return None


def norm_title(title: str) -> str:
    return re.sub(r"[\s\W_]+", "", title).lower()


def parse_cards(text: str) -> list[dict]:
    cards = []
    matches = list(CARD_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        cards.append(_parse_block(int(match.group("num")), match.group("title"), text[match.end():end]))
    return cards


def _parse_block(num: int, title: str, block: str) -> dict:
    fields: dict[str, str] = {}
    labels: dict[str, str] = {}
    seen: dict[str, int] = {}
    unknown: list[str] = []
    current: str | None = None

    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("###"):
            continue
        match = FIELD_RE.match(line)
        if match:
            label = match.group("label").strip()
            value = match.group("value").strip()
            kind = kind_of(label)
            if kind is None:
                unknown.append(label)
                current = None
                continue
            seen[kind] = seen.get(kind, 0) + 1
            fields[kind] = f"{fields[kind]} {value}".strip() if kind in fields else value
            labels.setdefault(kind, label)
            current = kind
            continue
        if current:
            fields[current] = f"{fields[current]} {line}".strip()

    return {
        "num": num,
        "title": title,
        "fields": fields,
        "labels": labels,
        "seen": seen,
        "unknown": unknown,
    }


def validate(
    text: str,
    min_noted: int = MIN_NOTED,
    max_silent: int = MAX_SILENT,
    _grouped: bool = False,
) -> dict:
    items: list[dict] = []

    def add(level: str, where: str, message: str) -> None:
        items.append({"level": level, "where": where, "message": message})

    groups = list(GROUP_RE.finditer(text))
    if len(groups) > 1 and not _grouped:
        total = 0
        script: str | None = None
        for index, group in enumerate(groups):
            end = groups[index + 1].start() if index + 1 < len(groups) else len(text)
            sub = validate(text[group.start():end], min_noted, max_silent, _grouped=True)
            total += sub["cards"]
            script = script or sub["script"]
            items.extend({**item, "where": f"组 {index + 1} · {item['where']}"} for item in sub["items"])
        return _summarize(items, total, script)

    heading = ARTICLE_HEADING_RE.search(text)
    if not heading:
        add("FAIL", "文档", "缺少文章标题行，应为 '## 知识卡片：<主题>' 或 '## Knowledge Cards: <topic>'")

    cards = parse_cards(text)
    if not cards:
        add("FAIL", "文档", "未解析到任何卡片，卡片标题应为 '### 卡片 1：<标题>' 或 '### Card 1: <title>'")
        return _summarize(items, len(cards), None)

    count = len(cards)
    if count > HARD_MAX:
        add("FAIL", "文档", f"卡片数量 {count} 超过硬上限 {HARD_MAX}，请合并同类知识点")
    needs_note = count < min_noted or count > max_silent
    if needs_note:
        blockquote = _note_after_heading(text, heading)
        if not blockquote:
            add(
                "FAIL",
                "文档",
                f"卡片数量为 {count}，必须在文章标题下紧跟一行 '> ...' 说明原因（减量或长文）",
            )
        elif not NOTE_RE.search(blockquote):
            add("FAIL", "文档", f"说明行未说明原因，当前为：{blockquote[:60]}")
        else:
            add("INFO", "文档", f"张数 {count} 触发说明规则，已附说明行：{blockquote[:40]}")

    title_scripts: list[str | None] = []
    for card in cards:
        where = f"卡片 {card['num']}"
        _check_title(card, add, where)
        _check_core(card, add, where)
        _check_explanation(card, add, where)
        _check_practice(card, add, where)
        for label in card["unknown"]:
            add("INFO", where, f"未识别的字段 '{label}'，已忽略校验（允许的自定义字段：原文依据 / source）")
        title_scripts.append(script_of(f"{card['title']} {card['fields'].get('core', '')}"))

    _check_duplicate_titles(cards, add)
    _check_label_language(cards, add)

    doc_script = next((s for s in title_scripts if s), None)
    return _summarize(items, len(cards), doc_script)


def _note_after_heading(text: str, heading) -> str | None:
    tail = text[heading.end():]
    stop = CARD_RE.search(tail)
    segment = tail[: stop.start()] if stop else tail
    for line in segment.splitlines():
        line = line.strip()
        if line.startswith(">"):
            return line.lstrip("> ").strip()
    return None


def _check_title(card: dict, add, where: str) -> None:
    title = card["title"].strip()
    if not title:
        add("FAIL", where, "标题为空")
        return
    lower = title.lower()
    for word in BANNED_TITLE_WORDS:
        if word in lower:
            add("FAIL", where, f"标题含被禁用的泛化词 '{word}'：{title}")
    limit = WARN_TITLE_CHARS_EN if script_of(title) == "en" else WARN_TITLE_CHARS_ZH
    if len(title) > limit:
        add("WARN", where, f"标题 {len(title)} 字符，偏长，建议压到 {limit} 以内")


def _check_core(card: dict, add, where: str) -> None:
    core = card["fields"].get("core")
    if not core:
        add("FAIL", where, "缺少「核心知识」字段")
        return
    if card["seen"].get("core", 0) > 1:
        add("FAIL", where, "「核心知识」字段出现多次，应恰好一次")
    sentences = count_sentences(core)
    if sentences > MAX_CORE_SENTENCES:
        add("FAIL", where, f"核心知识含 {sentences} 个句子，应恰好 1 个：{core[:50]}")
    for connector in ("并且", "以及", "；"):
        if connector in core:
            add("WARN", where, f"核心知识可能包含两个主张（出现 '{connector}'），请确认是否需要拆卡")
    if core.count("，") + core.count(",") >= 3:
        add("WARN", where, f"核心知识有 {core.count('，') + core.count(',')} 个逗号，可能包含多个主张，请确认是否需要拆卡")


def _check_explanation(card: dict, add, where: str) -> None:
    explanation = card["fields"].get("explanation")
    if not explanation:
        add("FAIL", where, "缺少「简明解释」字段")
        return
    if card["seen"].get("explanation", 0) > 1:
        add("FAIL", where, "「简明解释」字段出现多次，应恰好一次")
    sentences = count_sentences(explanation)
    if sentences > WARN_EXPLANATION_SENTENCES:
        add("WARN", where, f"简明解释 {sentences} 句，超出建议的 2-4 句")


def _check_practice(card: dict, add, where: str) -> None:
    has_example = "example" in card["fields"]
    has_selftest = "selftest" in card["fields"]
    if has_example and has_selftest:
        add("FAIL", where, "「例子」与「自测问题」不可同时出现，第 4 字段只能二选一")
    if not has_example and not has_selftest:
        add("FAIL", where, "缺少第 4 字段：必须提供「例子」或「自测问题」之一")
        return
    if has_example:
        label = card["labels"].get("example", "")
        value = card["fields"]["example"]
    else:
        label = card["labels"].get("selftest", "")
        value = card["fields"]["selftest"]
    if is_combo_label(label):
        kind = "自测问题" if re.search(r"[？?]", value) else "例子"
        add("FAIL", where, f"字段标签为组合式 '{label}'，须改用具体标签 '{kind}'")


def _check_duplicate_titles(cards: list[dict], add) -> None:
    normalized = [norm_title(c["title"]) for c in cards]
    for i, left in enumerate(normalized):
        for j in range(i + 1, len(normalized)):
            right = normalized[j]
            if not left or not right:
                continue
            if left == right:
                add("FAIL", f"卡片 {cards[i]['num']} / {cards[j]['num']}", f"标题重复：{cards[i]['title']}")
            else:
                ratio = difflib.SequenceMatcher(None, left, right).ratio()
                if ratio >= WARN_TITLE_SIMILARITY:
                    add(
                        "WARN",
                        f"卡片 {cards[i]['num']} / {cards[j]['num']}",
                        f"标题高度相似（{ratio:.2f}），确认是不同知识点：{cards[i]['title']} / {cards[j]['title']}",
                    )


def _check_label_language(cards: list[dict], add) -> None:
    for card in cards:
        body = " ".join(
            [card["title"], *card["fields"].values()]
        )
        body_script = script_of(body)
        if not body_script:
            continue
        label_text = " ".join(card["labels"].values())
        if not label_text:
            continue
        if script_of(label_text) == "zh" and body_script == "en":
            add("FAIL", f"卡片 {card['num']}", "正文为英文但字段标签为中文，应整体跟随输出语言")
        elif script_of(label_text) == "en" and body_script == "zh":
            add("FAIL", f"卡片 {card['num']}", "正文为中文但字段标签为英文，应整体跟随输出语言")


def _summarize(items: list[dict], card_count: int, doc_script: str | None) -> dict:
    fails = [i for i in items if i["level"] == "FAIL"]
    warns = [i for i in items if i["level"] == "WARN"]
    return {"cards": card_count, "script": doc_script, "items": items,
            "fails": len(fails), "warns": len(warns), "passed": not fails}


def report(result: dict, stream=sys.stdout) -> None:
    labels = {"FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO"}
    for item in result["items"]:
        print(f"{labels[item['level']]}  {item['where']}  {item['message']}", file=stream)
    script = result["script"] or "-"
    status = "PASS" if result["passed"] else "FAIL"
    print(
        f"RESULT: {status} | cards: {result['cards']} | language: {script} | "
        f"fail: {result['fails']} | warn: {result['warns']}",
        file=stream,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate knowledge cards produced by make-knowledge-cards.")
    parser.add_argument("path", nargs="?", help="path to a Markdown file containing cards")
    parser.add_argument("--stdin", action="store_true", help="read the cards from standard input")
    parser.add_argument("--min-noted", type=int, default=MIN_NOTED)
    parser.add_argument("--max-silent", type=int, default=MAX_SILENT)
    args = parser.parse_args(argv)

    if args.stdin or not args.path:
        text = sys.stdin.read()
    else:
        file_path = Path(args.path)
        if not file_path.is_file():
            print(f"FAIL  文档  找不到文件：{file_path}")
            return 1
        text = file_path.read_text(encoding="utf-8-sig")

    result = validate(text, min_noted=args.min_noted, max_silent=args.max_silent)
    report(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

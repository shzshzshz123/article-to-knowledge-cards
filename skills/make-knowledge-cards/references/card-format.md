# Card Format Reference

Field-level detail for a single card, plus the edge cases that are easy to get wrong.
The normative rules and the output templates live in `SKILL.md`; this file only adds the
operational detail needed to apply them.

## Title

Write a specific noun phrase that names the point, not the paragraph.

| Good | Poor | Why |
| --- | --- | --- |
| 睡眠通过海马体重放完成记忆巩固 | 记忆 | Too broad, could cover any memory fact. |
| 番茄钟不可分割 | 补充说明 | Names no knowledge point. |
| A branch is only a pointer | 分支 | Too vague to recall anything. |
| 最低系统版本提升至 iOS 15 | 其他变更 | Unsearchable placeholder. |

Banned title words: `简介`, `概述`, `其他`, `补充`, `要点一/二/三`, `About`, `Misc`.

Additional checks:

- Keep a Chinese title within about 30 characters and an English title within about 70,
  or the card becomes a summary sentence instead of a handle.
- The title must be greppable: someone reading only the titles of a card set should be
  able to reconstruct the article's outline.

## Core knowledge

One sentence, one claim. It must be a statement, not a topic label.

- Good: `睡眠以约 90 分钟为一个周期。`
- Poor: `关于睡眠周期` (a label, not knowledge)
- Poor: `睡眠以约 90 分钟为一个周期，且分为四到五个阶段，其中深睡最重要。`
  (two claims - split into separate cards)

The checkable form of this rule: the sentence contains exactly one sentence-ending mark.
Chinese connectors `并且`, `以及`, `同时`, `；` and English `and`, `while` usually mean two
claims are hiding in one sentence.

## Explanation

Explain, do not restate. The core knowledge says *what*; the explanation says *why*,
*how*, or *so what*. Stay inside the source: if the source does not explain a mechanism,
do not supply one from outside knowledge. Two to four sentences; longer means the card is
carrying more than one knowledge point.

## Example or self-test

`SKILL.md` defines the priority order. This section defines what counts as acceptable.

**A usable source example** is a concrete case the source actually states, such as a named
scenario, a worked calculation, a real command, or a before/after comparison. When reusing
it:

- Keep the original numbers, names, and units. Do not round, simplify, or rename.
- If it is a code block, a table, a formula, or a command, keep it verbatim inside a fenced
  block or inline code. Do not translate code, identifiers, flags, or file paths.
- Shorten only by trimming surrounding prose, never by paraphrasing the example itself.
- Attribute it when the source does: `> 原文依据：<原文片段>`.

**A self-test question** must be answerable from the card's own fields, so the reader can
check the answer without going back to the source. Avoid questions that only ask for
recall of the title, and avoid questions whose answer is not on the card.

Never invent example data (numbers, scenarios, product names) that the source does not
contain. If nothing usable exists, ask a self-test question instead.

## Optional source field

Add a fifth field only when the user asks for verifiable extraction (`?with-source`,
"标注原文出处", "include sources"):

```markdown
- **原文依据**：白天学到的信息最初以不稳定的形式暂存在海马体……
```

Rules: quote at most about 40 characters, copy the exact wording, and never use this field
to smuggle in facts the quotation does not support. The checker accepts `原文依据` and
`Source` as known extra fields and ignores any other custom field name.

## Complete good vs. poor card

Good:

```markdown
### 卡片 3：睡眠由约 90 分钟一个的周期构成
- **核心知识**：睡眠以约 90 分钟为一个周期，每个周期包含 NREM 与 REM 两种睡眠。
- **简明解释**：睡眠不是均匀的整体，而是在非快速眼动睡眠（NREM）和快速眼动睡眠
  （REM）之间循环，单个周期约 90 分钟。理解周期是理解两类睡眠分工的前提。
- **自测问题**：一个睡眠周期大约多长？周期内包含哪两类睡眠？
```

Poor - and why:

```markdown
### 卡片 3：睡眠周期
- **核心知识**：睡眠很重要，包含多个阶段，对记忆有好处，还可以恢复体力。
- **简明解释**：睡眠分为多个阶段，每个阶段都有作用。
- **例子**：小明每天睡 8 小时，考试成绩提升了 20 分。
```

Problems: the title is a topic label; the core knowledge packs four claims into one
sentence; the explanation adds nothing; the example is invented data that the source
never mentioned.

## Special cases

### Enumerations in the source

When the source lists several parallel rules (e.g. "使用时有三个原则"):

- Give each rule its own card **only when** the rule is independently meaningful and
  would be useful on its own.
- Otherwise keep them in one card whose core knowledge states that the rules exist as a
  set, and whose explanation lists them.

Do not create one card per sentence just to reach the target count.

### More points than the ceiling

Past 12 points, merge in this order before dropping anything:

1. Two facets of the same mechanism (e.g. "what HEAD is" and "what HEAD does").
2. A general rule and its single illustrative detail.
3. A definition and the conclusion that immediately follows from it.

Drop a point entirely only when it is a restatement or a detail with no standalone value.
Never drop a point that carries the article's central claim.

### Fewer points than expected

A short card set is correct when the source is genuinely thin. It is a mistake when the
extraction was lazy: re-read the source and check for definitions, caveats, and "why"
statements that were skipped before concluding that only 2 points exist.

### Source is a list, changelog, or FAQ

Treat each independently useful entry as a candidate point. Skip entries that are pure
bookkeeping (version bumps with no user impact, typo fixes, links). Entries sharing one
cause belong in one card: three bug fixes with the same root cause are one knowledge
point, not three.

### Source contains code, tables, or formulas

They are primary source material, not decoration:

- Keep short blocks verbatim in the example field.
- If a block is too long for a card, quote the decisive lines and say what the rest does,
  rather than rewriting the logic in prose.
- A table that enumerates parallel facts usually becomes one card whose explanation
  reproduces the key rows, not one card per row.

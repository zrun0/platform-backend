# Architecture Decision Records

记录本项目的重要架构决策:为什么选、备选是什么、后果如何。每篇 ADR 是决策时点的快照,不随代码演进更新(append-only);被取代时只改 Status 标注,正文不动。

## 目录

- [0001 - uv workspace monorepo + PEP 420 `zrun.*` namespace](./0001-uv-workspace-monorepo-with-pep420-namespace.md)(现行)
- [0002 - API contracts as separate packages](./0002-api-contracts-as-separate-packages.md)(现行)
- [0003 - Centralized version constraints at the workspace root](./0003-centralized-version-constraints-at-workspace-root.md)(现行)
- [0004 - Self-built MockRouter replacing respx](./0004-mock-router-replacing-respx.md)(现行)
- [0005 - Migrate HTTP stack from httpx to httpx2](./0005-migrate-http-stack-from-httpx-to-httpx2.md)(现行)

## 写作规范

- **单篇 ~100 行以内**:决策 + 理由 + 后果。配置和代码的现行形态写在 living docs(`CONTEXT.md`、`docs/*.md`、根 `README.md`)或代码注释里,ADR 只链接过去,不内嵌快照(快照会腐烂)
- **Status 必须带状态与取代关系**:**Accepted** / **Superseded by [NNNN](./NNNN-实际文件名.md)**(日期);取代旧决策时同时在旧 ADR 的 Status 回链
- **备选方案要写清为什么不选**:**Alternatives Considered** 是 ADR 的核心价值,不是装饰
- **命名**:`NNNN-<slug>.md`,编号从 0001 连续递增,不复用已删除编号;**标题(# heading、目录与互链文本)用英文**,正文中文+English terms
- **Related Decisions 互链必须用实际文件名**(互链是 ADR 被发现的主要路径)

## 模板

```md
# NNNN - <决策标题>

## Status

**Accepted**(若取代旧决策:注明取代关系与日期)

## Context

面临什么问题/约束,为什么需要做这个决策。

## Decision

选了什么。
Why:逐条理由。
Alternatives Considered:每个备选 ✅ 优势 / ❌ 劣势,说清为什么不选。

## Consequences

**Positive / Negative / Mitigation。**
Mitigation 指向 living docs(`CONTEXT.md`、`docs/*.md`),不复制内容。

## Implementation Notes

落地要点(可选;不放大段配置快照)。

## Related Decisions

- [NNNN - 标题](./NNNN-实际文件名.md)
```

## 范本

[0002 - API contracts as separate packages](./0002-api-contracts-as-separate-packages.md):Alternatives Considered 的 ✅/❌ 写法、Mitigation 指向 living docs(`CONTEXT.md` 词条)的示范。

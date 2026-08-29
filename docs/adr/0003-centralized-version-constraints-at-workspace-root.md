# 0003 - Centralized version constraints at the workspace root

## Status

**Accepted**(2026-08-28,项目初始化)

## Context

workspace 的八个发行包共用一个 lockfile 和一个虚拟环境,每个第三方库只能存在一个版本。若各成员自行 pin 版本,要么在不同发行包间解析出不同版本,要么与 lockfile 冲突。

## Decision

第三方依赖的版本约束只写在根 `pyproject.toml` 的 `[tool.uv] constraint-dependencies`(如 `fastapi>=0.115`);workspace 成员在 `dependencies` 里只写裸名。

Why:

- 单 venv 下"每库一版"是物理事实,集中约束让解析结果与事实一致
- 升级是单文件改动,`uv.lock` diff 直接展示对全部 consumer 的波及范围(blast radius)
- 成员声明意图(import 什么),根声明策略(跑哪个版本),职责分离

新增或升级依赖的现行操作流程由 living doc 承载:[Dependency Management](../dependencies.md)。

Alternatives Considered:

- **各成员自行 pin 版本**:✅ 包可独立迁移出去 / ❌ 单 venv 下必然冲突或解析分裂;本仓库无独立发布诉求,优势不成立

## Consequences

**Positive:**

- 升级单文件化,blast radius 全景可见
- 依赖子集保持诚实:成员缺依赖在 type-check 阶段暴露

**Negative:**

- 约定对工具不可见:uv 完全接受成员包里冒出的 `fastapi>=0.100`,没有机械防线

**Mitigation:**

- 由 PR review 把关:拒绝成员 `dependencies` 里的版本号;规则与流程见 [Dependency Management](../dependencies.md)

## Related Decisions

- [0001 - uv workspace monorepo + PEP 420 `zrun.*` namespace](./0001-uv-workspace-monorepo-with-pep420-namespace.md)

# 0001 - uv workspace monorepo + PEP 420 `zrun.*` namespace

## Status

**Accepted**(2026-08-28,项目初始化)

## Context

平台由多个可独立部署的服务(BFF、UC、Flow)加跨服务共享代码(core、auth、各 API 契约)组成。需要一种仓库与打包模型:服务独立演进和部署、共享代码不发布到外部 index、一个 lockfile 和一个虚拟环境让跨包重构与全量 `just test` / `just check` 在单仓库内完成。

## Decision

采用 uv workspace monorepo,两层布局:可部署服务在 `apps/`(bff、uc、flow),共享库在 `packages/`(core、auth、契约包)。所有 import 代码位于 `zrun.*` PEP 420 隐式命名空间(implicit namespace)下——命名空间根没有 `__init__.py`——每个发行包通过 `tool.uv.build-backend.module-name` 映射到一个模块(如 `zrun-uc-api` → `zrun.uc_api`)。

Why:

- 服务独立部署,共享代码经 `workspace = true` source 直连,无需私有 index 发布
- 单 lockfile/venv:跨包重构单 PR 完成,工具链(测试、类型检查)天然全树覆盖
- PEP 420 让任意发行包持有 `zrun.*` 下任意模块,无需命名空间属主包

Alternatives Considered:

- **Single package(单一包)**:✅ 工具链最简 / ❌ 部署单元无法声明各自的依赖子集
- **Multi-repo + private index(多仓库+私有索引)**:✅ 完全隔离 / ❌ 发布摩擦 + 跨仓库 PR;对内部平台不值得

## Consequences

**Positive:**

- 跨包重构单 PR;`just sync` / `just test` / `just check` 覆盖整棵树
- 每个 app 只声明自己 import 的依赖(BFF 拉 `zrun-uc-api` 而非 UC app),意外耦合在 type-check 阶段暴露

**Negative:**

- PEP 420 是承重结构:新包 `module-name` 注册错误,import 会以隐蔽方式坏掉
- 新增服务要同时落 `apps/<name>/` 目录与完整 pyproject(`module-name` 注册等),布局与打包约定成为负担(`just dev <name>` 为泛型插值,无需改 justfile)

**Mitigation:**

- 目录职责与包命名约定见 living docs:[README.md](../../README.md) 的 Structure 一节、[CONTEXT.md](../../CONTEXT.md) 的 Service 词条
- `zrun-test-utils` 例外:发行顶层模块 `zrun_test_utils`(不在 `zrun.*` 下),测试脚手架刻意置于运行时命名空间之外

## Related Decisions

- [0002 - API contracts as separate packages](./0002-api-contracts-as-separate-packages.md)
- [0003 - Centralized version constraints at the workspace root](./0003-centralized-version-constraints-at-workspace-root.md)

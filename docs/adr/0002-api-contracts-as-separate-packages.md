# 0002 - API contracts as separate packages

## Status

**Accepted**(2026-08-28,项目初始化)

## Context

BFF 通过 HTTP 调用下游服务(UC、Flow)。请求/响应模型与调用代码的归属有三种可能:provider 服务包内、各 consumer 内、独立契约包。同时希望测试替身(fake)无需继承具体 client 类即可替换下游依赖。

## Decision

每个暴露 HTTP API 的服务配一个同级契约包 `packages/<service>-api/`(发行名 `zrun-<service>-api`,模块名 `zrun.<service>_api`),恰好包含三件事:

- `models.py` — Pydantic wire models,线上契约
- `protocol.py` — `typing.Protocol`,client 以结构化子类型(structural subtyping)满足它
- `client.py` — `BaseServiceClient` 子类,Feign 风格端点装饰器

契约包只依赖 `zrun-core`,绝不依赖 provider 的 app 包;consumer(BFF)依赖契约包而非服务包。

Why:

- consumer 依赖保持轻薄:不拖入 provider 的服务端依赖(uvicorn、settings)
- provider 路由与 consumer client 共享同一份 wire 定义,契约变更让双方在同一 PR 内编译期报错
- `Protocol` 结构化满足让测试 fake 直接实现接口,不导入 HTTP 机制

Alternatives Considered:

- **契约放在 provider app 内**:✅ 无独立包开销 / ❌ consumer 被拖入 provider 的服务端依赖
- **契约放在各 consumer 内**:✅ consumer 自治 / ❌ 模型重复定义,逐渐漂移(drift)

## Consequences

**Positive:**

- wire 契约单点定义,变更即全仓编译期可见
- fake 廉价:结构化实现协议即可,测试无需起 HTTP

**Negative:**

- 一次契约变更要以 lockstep 触碰契约、provider、consumer 三个包
- 模式依赖约定重复:每个新服务必须复刻三件套,不能即兴发挥布局

**Mitigation:**

- 三件套约定由 [CONTEXT.md](../../CONTEXT.md) 的 Contract Package 词条承载;新服务照词条落地
- 契约包不得长出业务逻辑:超出三件套的代码属于 `zrun-core` 或 provider(review 把关)

## Related Decisions

- [0001 - uv workspace monorepo + PEP 420 `zrun.*` namespace](./0001-uv-workspace-monorepo-with-pep420-namespace.md)

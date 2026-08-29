# 0004 - Self-built MockRouter replacing respx

## Status

**Accepted**(2026-08-29)

## Context

代码库从 httpx 迁移到 httpx2(starlette testclient 已 deprecate httpx)。respx 只 patch 旧 `httpx` 模块,无法拦截 httpx2 client;PyPI 上无 respx2 或同等 mock 库(2026-08-29 核实)。而测试体系重度依赖 transport 层 mock:契约包 client 测试与 BFF endpoint 集成测试都靠它拦截下游 HTTP、回放 canned response、断言请求内容。

## Decision

在 `zrun-test-utils` 内自建 `MockRouter`——一个 `httpx2.AsyncBaseTransport` 子类,提供 respx 兼容 API 子集(`router.get/post(url)`、`route.return_value`、`route.called`、`route.calls.last.request`),经 `BaseServiceClient` 新增的 `transport=` 注入 seam 接入 client。未注册的请求抛 `AssertionError`。

Why:

- mock 能力是测试刚需,没有可用的第三方选项,自建是唯一出路
- `AsyncBaseTransport` 是 httpx2 的官方扩展点,不 monkey-patch 任何内部结构,升级 httpx2 不易碎
- respx 兼容子集让 4 个测试文件的迁移 diff 最小,测试语义不变
- 核心实现 ~100 行,无 pattern matching 等高级特性,维护面可控

Alternatives Considered:

- **保留 respx + httpx 不迁移**:✅ 零自建 / ❌ 与 httpx2 迁移互斥,deprecation warning 常驻,运行时与测试双 HTTP 栈
- **等 respx 官方支持 httpx2**:✅ 无自建 / ❌ 时间不可控,阻塞 httpx2 迁移
- **按 ADR 0002 的 Protocol fake 绕过 HTTP 层**:✅ 彻底去掉 HTTP mock / ❌ BFF 集成测试恰恰要验证真实 client 栈——重试、错误映射、header 传播

## Consequences

**Positive:**

- 测试基建与运行时同栈(httpx2),不存在 mock 库与客户端版本漂移
- 未注册请求 fail loudly(AssertionError);respx 默认 passthrough 会放意外请求去打真实网络
- `transport=` seam 同时提升 `BaseServiceClient` 的可测性

**Negative:**

- 自维护 mock 库:respx 的 pattern matching、side_effect、调用统计等能力没有,需要时须自行扩展
- respx 兼容只是子集,写测试时不能照搬 respx 全部 API

**Mitigation:**

- 用法、范例与设计说明由 living doc 承载:[packages/test-utils/README.md](../../packages/test-utils/README.md) 的 Mocking 一节

## Implementation Notes

- `MockRouter` 驻留 `zrun-test_utils.mock_router`,经包根 `__init__` 导出
- 各 tests 目录的 `conftest.py` 提供 `mock_router` fixture,client fixture 以 `transport=mock_router` 注入
- URL 匹配规则:scheme://host/path 精确匹配,忽略 query string(同 respx 默认)

## Related Decisions

- [0001 - uv workspace monorepo + PEP 420 `zrun.*` namespace](./0001-uv-workspace-monorepo-with-pep420-namespace.md)
- [0002 - API contracts as separate packages](./0002-api-contracts-as-separate-packages.md)
- [0003 - Centralized version constraints at the workspace root](./0003-centralized-version-constraints-at-workspace-root.md)
